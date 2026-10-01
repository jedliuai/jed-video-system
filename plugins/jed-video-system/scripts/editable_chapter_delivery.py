"""Accepted insertion -> separate editable layers -> isolated new draft.

Default is a plan. --execute creates media and draft; --publish optionally uses
the existing Bridge's app-running checks, backup and index transaction.
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
from jed_chapters.delivery import sha
from jed_chapters.editable import accepted_insertion, overlay_source_frame


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, data):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--props', required=True)
    parser.add_argument('--review-state', required=True)
    parser.add_argument('--candidate-id', required=True)
    parser.add_argument('--local-config', default='config/local.json')
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    def local(value):
        path = Path(value)
        return (path if path.is_absolute() else root / path).resolve()
    receipt, result = None, None
    try:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,49}', args.job_id):
            raise ValueError('Use a distinct simple bounded job-id')
        props_path, review_path, config_path = map(local, (args.props, args.review_state, args.local_config))
        props = read(props_path)
        acceptance = accepted_insertion(read(review_path), args.candidate_id, props_path, props)
        if any(event.get('styleId') != 'jed-paper-blue' or event.get('styleRevision') != 'r1' for event in props['chapterTransitions']):
            raise ValueError('Native layout only supports the approved paper-blue r1 pilot')
        config = read(config_path)
        public = (root / 'motion-lab/public').resolve()
        def asset(raw):
            path = (public / raw).resolve()
            if not path.is_relative_to(public) or not path.is_file():
                raise ValueError('Local artwork and sounds must exist in the public directory')
            return path
        source = asset(props['sourceSrc'])
        images = [asset(event['artSrc']) for event in props['chapterTransitions']]
        sounds = [asset(event['audioSrc']) for event in props['soundEffects']]
        original_overlay = root / 'work/renders/talking-head-overlay.mov'
        regular, bold = public / 'fonts/jed-sans-regular.ttf', public / 'fonts/jed-sans-bold.ttf'
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise ValueError('Existing FFmpeg runtime required')
        bound = [props_path, review_path, config_path, source, original_overlay, regular, bold,
            *images, *sounds, Path(ffmpeg), Path(__file__), local(config['jianying']['python']),
            local(config['jianying']['bridgeConfig']),
            local(config['jianying']['bridgeProject']) / 'jianying_bridge/core.py',
            root / 'workers/draft-adapter/worker.py', root / 'workers/draft-adapter/inserted.py',
            root / 'workers/draft-adapter/publish_inserted.py',
            root / 'plugins/jed-video-system/src/jed_chapters/editable.py']
        hashes = {str(path.resolve()): sha(path) for path in bound}
        hashes.update(acceptance['verifiedDependencies'])
        job = root / 'work/editable-chapter-delivery' / args.job_id
        name = 'jed-probe-editable-' + args.job_id
        result = {'schemaVersion': 'jed-editable-chapter-delivery/1', 'jobId': args.job_id,
            'status': 'planned', 'inputHashes': hashes, 'acceptance': acceptance,
            'outputRoot': str(job), 'draftName': name, 'publishRequested': args.publish,
            'published': False, 'externalEditorVerified': False}
        result['fingerprint'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        if not args.execute:
            print(json.dumps(result, ensure_ascii=False))
            return 0
        receipt = job / 'receipt.json'
        if job.exists():
            old = read(receipt)
            if old.get('fingerprint') != result['fingerprint'] or old.get('status') != 'succeeded' or any(sha(path) != digest for path, digest in old['outputHashes'].items()):
                raise ValueError('Existing delivery changed or failed; inspect it and use a new job-id')
            print(json.dumps({**old, 'reused': True}, ensure_ascii=False))
            return 0
        job.mkdir(parents=True, exist_ok=False)
        result['status'] = 'running'
        write(receipt, result)
        def unchanged():
            if any(sha(path) != digest for path, digest in hashes.items()):
                raise ValueError('Bound input changed during editable delivery')
        def run(step, argv):
            unchanged()
            process = subprocess.run([str(arg) for arg in argv], cwd=root, capture_output=True, encoding='utf-8', errors='replace', timeout=900, shell=False)
            (job / f'{step}.stdout.log').write_text(process.stdout, encoding='utf-8')
            (job / f'{step}.stderr.log').write_text(process.stderr, encoding='utf-8')
            if process.returncode:
                raise ValueError(f'{step} failed; inspect retained logs')
            unchanged()
            return process.stdout
        voice = job / 'original-voice.wav'
        # AAC decoding can end a fraction of a frame before the video's endpoint.
        # Pad only that missing tail, keeping every original speech sample at 1x.
        samples = props['sourceDurationInFrames'] * 48000 // 30
        run('extract-original-voice', [ffmpeg, '-nostdin', '-v', 'error', '-n', '-i', source, '-vn',
            '-af', f'aresample=48000,apad,atrim=end_sample={samples}', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', voice])
        matte = job / 'chapter-warm-matte.png'
        run('chapter-matte', [ffmpeg, '-nostdin', '-v', 'error', '-n', '-f', 'lavfi', '-i', 'color=c=0xF7F5EF:s=1920x1080', '-frames:v', '1', matte])
        media = []
        for i, event in enumerate(props.get('overlays', [])):
            source_frame = overlay_source_frame(props, event)
            path = job / f'remotion-block-{i}.mov'
            run(f'overlay-{i}', [ffmpeg, '-nostdin', '-v', 'error', '-n', '-i', original_overlay,
                '-vf', f'trim=start_frame={source_frame}:end_frame={source_frame+event["durationInFrames"]},setpts=PTS-STARTPTS',
                '-an', '-c:v', 'prores_ks', '-profile:v', '4', '-pix_fmt', 'yuva444p10le', path])
            media.append({'id': event['id'], 'path': str(path), 'sha256': sha(path),
                'eventDigest': hashlib.sha256(json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()})
        def records(events, paths):
            return [{'id': event['id'], 'path': str(path), 'sha256': sha(path),
                'eventDigest': hashlib.sha256(json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()} for event, path in zip(events, paths)]
        spec = {'schemaVersion': 'jed-draft-inserted/1', 'name': name,
            'bridgeProject': config['jianying']['bridgeProject'], 'bridgeConfig': config['jianying']['bridgeConfig'],
            'outputRoot': str(job / 'draft-builds'), 'source': str(source), 'voice': str(voice), 'matte': str(matte),
            'font': str(regular), 'boldFont': str(bold), 'renderProps': str(props_path), 'overlayMedia': media,
            'chapterImages': records(props['chapterTransitions'], images), 'soundMedia': records(props['soundEffects'], sounds)}
        spec_path = job / 'draft-input.json'
        write(spec_path, spec)
        draft_result = json.loads(run('draft', [local(config['jianying']['python']), root / 'workers/draft-adapter/worker.py', 'inserted', '--input', spec_path]))
        if draft_result['checks']['layers']['status'] != 'passed':
            raise ValueError('Saved draft did not retain independent editable layers')
        if args.publish:
            # Existing Bridge owns app-running checks, backups and index transaction.
            unchanged()
            sys.path.insert(0, str(local(config['jianying']['bridgeProject'])))
            # Publication runs in the pinned Bridge Python, not this packaging interpreter.
            publish_spec = job / 'publish-input.json'
            write(publish_spec, {'bridgeProject': config['jianying']['bridgeProject'], 'bridgeConfig': config['jianying']['bridgeConfig'], 'draftResult': draft_result})
            published = json.loads(run('publish', [local(config['jianying']['python']), root / 'workers/draft-adapter/publish_inserted.py', '--input', publish_spec]))
            draft_result.update(published=True, draftPath=published['draft_path'], publication=published)
        write(job / 'draft-result.json', draft_result)
        result.update(status='succeeded', draftPath=draft_result['draftPath'], published=draft_result['published'],
            checks=draft_result['checks'], editability=draft_result['editability'])
        result['outputHashes'] = {str(path.resolve()): sha(path) for path in job.rglob('*') if path.is_file() and path != receipt and path.suffix != '.log'}
        write(receipt, result)
        print(json.dumps({key: result[key] for key in ('status', 'draftName', 'draftPath', 'published', 'editability', 'checks')}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        if receipt is not None and result is not None and result.get('status') == 'running':
            result.update(status='failed', error=str(exc))
            write(receipt, result)
        print(f'Editable chapter delivery blocked: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
