"""Bound pilot delivery: accepted chapter recipe -> full preview -> isolated draft.

Official plugins stay external. This uses the existing local CLI and Bridge;
never publishes a draft or fabricates whole-video approval.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jed_chapters.delivery import accepted_recipe, asset_props, sha


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, data):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--props', required=True)
    parser.add_argument('--review-state', required=True)
    parser.add_argument('--candidate-id', required=True)
    parser.add_argument('--local-config', default='config/local.json')
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    def local(value):
        path = Path(value)
        return (path if path.is_absolute() else root / path).resolve()
    receipt, result = None, None
    try:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', args.job_id):
            raise ValueError('job-id must be a simple bounded name')
        if not re.fullmatch(r'jed-probe-[A-Za-z0-9_-]{1,72}', 'jed-probe-chapters-' + args.job_id):
            raise ValueError('job-id is too long for the existing draft name contract')
        props_path = local(args.props)
        props = read(props_path)
        review_path = local(args.review_state)
        acceptance = accepted_recipe(read(review_path), args.candidate_id, props_path, props)
        if props.get('fps') != 30 or props.get('sourceSrc') != 'live-source.mp4':
            raise ValueError('This delivery binds only the existing 30fps live pilot')
        config_path = local(args.local_config)
        config = read(config_path)
        motion = root / 'motion-lab'
        node = shutil.which('node')
        cli = motion / 'node_modules/@remotion/cli/remotion-cli.js'
        browser = local(config['remotion']['browserExecutable'])
        if not node or read(cli.with_name('package.json')).get('version') != '4.0.530' or not browser.is_file():
            raise ValueError('Bound existing Remotion 4.0.530 runtime is required')
        source = motion / 'public/live-source.mp4'
        overlay = root / 'work/renders/talking-head-overlay.mov'
        font = motion / 'public/fonts/jed-sans-regular.ttf'
        bound = [source, overlay, font, props_path, review_path, config_path, browser, cli,
                 local(config['videoUse']['python']), local(config['jianying']['python']),
                 local(config['jianying']['bridgeConfig']), root / 'workers/draft-adapter/worker.py',
                 root / 'scripts/normalize-preview-audio.py', root / 'scripts/verify-source-audio.py',
                 Path(__file__), root / 'plugins/jed-video-system/src/jed_chapters/delivery.py',
                 *sorted((motion / 'src').rglob('*.*')), motion / 'package-lock.json', motion / 'remotion.config.ts']
        hashes = {str(path.resolve()): sha(path) for path in bound}
        hashes.update(acceptance['verifiedDependencies'])
        job = root / 'work/chapter-delivery' / args.job_id
        result = {'schemaVersion': 'jed-chapter-delivery/1', 'jobId': args.job_id,
            'status': 'planned', 'acceptance': acceptance, 'inputHashes': hashes,
            'outputRoot': str(job), 'published': False, 'externalEditorVerified': False}
        fingerprint = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        result['fingerprint'] = fingerprint
        if not args.execute:
            print(json.dumps(result, ensure_ascii=False))
            return 0
        receipt = job / 'receipt.json'
        if job.exists():
            old = read(receipt)
            if old.get('fingerprint') != fingerprint or old.get('status') != 'succeeded':
                raise ValueError('Existing job changed or did not succeed; inspect it, then use a distinct job-id')
            if any(sha(path) != digest for path, digest in old['outputHashes'].items()):
                raise ValueError('Existing delivery output changed')
            print(json.dumps({**old, 'reused': True}, ensure_ascii=False))
            return 0
        job.mkdir(parents=True, exist_ok=False)
        result['status'] = 'running'
        write(receipt, result)
        def unchanged():
            if any(sha(path) != digest for path, digest in hashes.items()):
                raise ValueError('Bound input changed during delivery')
        def run(step, argv, cwd=root):
            unchanged()
            process = subprocess.run([str(arg) for arg in argv], cwd=cwd, capture_output=True,
                encoding='utf-8', errors='replace', timeout=900, shell=False)
            (job / f'{step}.stdout.log').write_text(process.stdout, encoding='utf-8')
            (job / f'{step}.stderr.log').write_text(process.stderr, encoding='utf-8')
            if process.returncode:
                raise ValueError(f'{step} failed ({process.returncode}); see retained job logs')
            unchanged()
            return process.stdout
        base_args = [node, cli]
        runtime_args = ['--browser-executable', browser, '--concurrency=4', '--log=error']
        full_raw = job / 'preview-remotion.mp4'
        run('full-preview', [*base_args, 'render', 'ChapterTransitionPreview', full_raw,
            '--props', props_path, '--codec=h264', '--crf=18', *runtime_args], motion)
        full = job / 'preview.mp4'
        run('audio-clock', [local(config['videoUse']['python']), root / 'scripts/normalize-preview-audio.py',
            '--reference', source, '--input', full_raw, '--output', full, '--props', props_path,
            '--report', job / 'audio-clock.json'])
        media = []
        for i, event in enumerate(props['chapterTransitions']):
            asset_input = job / f'chapter-{i}-props.json'
            write(asset_input, asset_props(props, event))
            asset = job / f'chapter-{i}.mov'
            run(f'chapter-{i}', [*base_args, 'render', 'ChapterTransitionAsset', asset,
                '--props', asset_input, '--image-format=png', '--pixel-format=yuva444p10le',
                '--codec=prores', '--prores-profile=4444', *runtime_args], motion)
            event_digest = hashlib.sha256(json.dumps(event, sort_keys=True, ensure_ascii=False,
                separators=(',', ':')).encode('utf-8')).hexdigest()
            media.append({'id': event['id'], 'path': str(asset), 'sha256': sha(asset), 'eventDigest': event_digest})
        overlay_frames = max(item['outputStartFrame'] + item['durationInFrames'] for item in props['overlays'])
        spec = {'schemaVersion': 'jed-draft-preview/1', 'name': 'jed-probe-chapters-' + args.job_id,
            'bridgeProject': config['jianying']['bridgeProject'], 'bridgeConfig': config['jianying']['bridgeConfig'],
            'outputRoot': str(job / 'draft-builds'), 'source': str(source), 'overlay': str(overlay),
            'font': str(font), 'renderProps': str(props_path), 'overlayDurationFrames': overlay_frames,
            'chapterMedia': media}
        spec_path = job / 'draft-input.json'
        write(spec_path, spec)
        draft_result = json.loads(run('draft', [local(config['jianying']['python']),
            root / 'workers/draft-adapter/worker.py', 'preview', '--input', spec_path]))
        if draft_result.get('published') is not False or draft_result['checks']['structure']['status'] != 'passed':
            raise ValueError('Isolated chapter draft did not pass structure checks')
        write(job / 'draft-result.json', draft_result)
        result.update(status='succeeded', preview=str(full), draftPath=draft_result['draftPath'],
            chapterMedia=media, draftChecks=draft_result['checks'])
        result['outputHashes'] = {str(path.resolve()): sha(path) for path in job.rglob('*')
            if path.is_file() and path != receipt and path.suffix != '.log'}
        write(receipt, result)
        print(json.dumps({key: result[key] for key in ('status', 'preview', 'draftPath', 'published', 'externalEditorVerified')}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        # Never rewrite a previous receipt if preflight/reuse failed.
        if receipt is not None and result is not None and result.get('status') == 'running':
            result.update(status='failed', error=str(exc))
            write(receipt, result)
        print(f'Chapter delivery blocked: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
