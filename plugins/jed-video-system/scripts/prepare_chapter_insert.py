"""Prepare an inserted chapter preview for review; never modifies editor drafts."""
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
from jed_chapters.insertion import insert_chapters
from jed_chapters.insertion_audio import audio_filter


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--props', required=True)
    parser.add_argument('--cards', required=True)
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
            raise ValueError('Use a distinct simple job-id')
        props_path, cards_path, config_path = map(local, (args.props, args.cards, args.local_config))
        props = insert_chapters(read(props_path), read(cards_path))
        config = read(config_path)
        motion = root / 'motion-lab'
        public = (motion / 'public').resolve()
        def asset(value):
            path = (public / value).resolve()
            if not path.is_relative_to(public) or not path.is_file():
                raise ValueError('Media must exist inside the local Remotion public directory')
            return path
        source = asset(props['sourceSrc'])
        sounds = [asset(sound['audioSrc']) for sound in props['soundEffects']]
        art = [asset(card['artSrc']) for card in props['chapterTransitions']]
        node, ffmpeg, ffprobe = map(shutil.which, ('node', 'ffmpeg', 'ffprobe'))
        browser = local(config['remotion']['browserExecutable'])
        cli = motion / 'node_modules/@remotion/cli/remotion-cli.js'
        if not all((node, ffmpeg, ffprobe)) or read(cli.with_name('package.json'))['version'] != '4.0.530':
            raise ValueError('Requires existing Remotion 4.0.530 and local FFmpeg tools')
        def probe(path):
            return json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], encoding='utf-8'))
        streams = probe(source)['streams']
        video = next(stream for stream in streams if stream['codec_type'] == 'video')
        if video['width'] != 1920 or video['height'] != 1080 or video['avg_frame_rate'] != '30/1' or float(video['duration']) + 1 / 30 < props['sourceDurationInFrames'] / 30 or not any(stream['codec_type'] == 'audio' for stream in streams):
            raise ValueError('Source must cover the complete 1080p/30fps pilot with original audio')
        for path, sound in zip(sounds, props['soundEffects']):
            if not any(stream['codec_type'] == 'audio' for stream in probe(path)['streams']) or abs(float(probe(path)['format']['duration']) - sound['durationInFrames'] / 30) > .002:
                raise ValueError('Prepared sound duration must match its exact event window')
        bound = [props_path, cards_path, config_path, source, *sounds, *art,
                 *sorted((public / 'fonts').glob('jed-sans-*.ttf')), browser, cli,
                 Path(node), Path(ffmpeg), Path(ffprobe), Path(__file__),
                 *sorted((motion / 'src').rglob('*.*')), motion / 'package-lock.json', motion / 'remotion.config.ts',
                 root / 'plugins/jed-video-system/src/jed_chapters/insertion.py',
                 root / 'plugins/jed-video-system/src/jed_chapters/insertion_audio.py',
                 root / 'plugins/jed-video-system/src/jed_chapters/delivery.py']
        hashes = {str(path.resolve()): sha(path) for path in bound}
        job = root / 'work/chapter-insert' / args.job_id
        result = {'schemaVersion': 'jed-chapter-insert/1', 'jobId': args.job_id,
            'status': 'planned', 'inputHashes': hashes, 'outputRoot': str(job),
            'sourceDurationInFrames': props['sourceDurationInFrames'], 'durationInFrames': props['durationInFrames'],
            'audioAndPacingApproved': False, 'draftCreated': False, 'published': False}
        result['fingerprint'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        if not args.execute:
            print(json.dumps(result, ensure_ascii=False))
            return 0
        receipt = job / 'receipt.json'
        if job.exists():
            old = read(receipt)
            if old.get('fingerprint') != result['fingerprint'] or old.get('status') != 'succeeded' or any(sha(path) != digest for path, digest in old['outputHashes'].items()):
                raise ValueError('Existing job changed or failed; inspect logs and use a new job-id')
            print(json.dumps({**old, 'reused': True}, ensure_ascii=False))
            return 0
        job.mkdir(parents=True, exist_ok=False)
        result['status'] = 'running'
        write(receipt, result)
        def unchanged():
            if any(sha(path) != digest for path, digest in hashes.items()):
                raise ValueError('Bound input changed during preview preparation')
        def run(step, argv, cwd=root):
            unchanged()
            process = subprocess.run([str(arg) for arg in argv], cwd=cwd, capture_output=True, encoding='utf-8', errors='replace', timeout=900, shell=False)
            (job / f'{step}.stdout.log').write_text(process.stdout, encoding='utf-8')
            (job / f'{step}.stderr.log').write_text(process.stderr, encoding='utf-8')
            if process.returncode:
                raise ValueError(f'{step} failed; see retained job logs')
            unchanged()
        compiled = job / 'props.json'
        write(compiled, props)
        raw, preview = job / 'preview-remotion.mp4', job / 'preview.mp4'
        run('render', [node, cli, 'render', 'ChapterInsertPreview', raw, '--props', compiled,
            '--browser-executable', browser, '--concurrency=4', '--codec=h264', '--crf=18', '--log=error'], motion)
        # Discard Remotion's encoded audio; rebuild once from original samples and gap mapping.
        inputs = [ffmpeg, '-nostdin', '-v', 'error', '-n', '-i', raw, '-i', source]
        for sound in sounds:
            inputs.extend(['-i', sound])
        run('mapped-audio', [*inputs, '-filter_complex', audio_filter(props), '-map', '0:v:0', '-map', '[outa]',
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-t', str(props['durationInFrames'] / 30), '-movflags', '+faststart', preview])
        first = props['insertions'][0]
        start = max(0, first['outputStartFrame'] - 60)
        frames = min(props['durationInFrames'] - start, 60 + first['durationInFrames'] + 180)
        sample = job / 'sample.mp4'
        run('sample', [ffmpeg, '-nostdin', '-v', 'error', '-n', '-i', preview, '-ss', str(start / 30), '-t', str(frames / 30),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', sample])
        info = probe(preview)
        stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
        if int(stream['nb_frames']) != props['durationInFrames'] or abs(float(info['format']['duration']) - props['durationInFrames'] / 30) > .02:
            raise ValueError('Rendered preview does not match the inserted timeline')
        write(job / 'probe.json', info)
        result.update(status='succeeded', preview=str(preview), sample=str(sample), sampleStartFrame=start, sampleDurationInFrames=frames)
        result['outputHashes'] = {str(path.resolve()): sha(path) for path in job.iterdir() if path.is_file() and path != receipt and path.suffix != '.log'}
        write(receipt, result)
        print(json.dumps({key: result[key] for key in ('status', 'preview', 'sample', 'durationInFrames', 'audioAndPacingApproved', 'draftCreated')}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        if receipt is not None and result is not None and result.get('status') == 'running':
            result.update(status='failed', error=str(exc))
            write(receipt, result)
        print(f'Chapter insertion blocked: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
