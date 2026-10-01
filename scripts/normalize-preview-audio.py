"""Correct a measured constant audio offset in this pilot's single continuous clip."""
import argparse
import json
from pathlib import Path
import runpy
from statistics import median
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--props', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    props = json.loads(Path(args.props).read_text(encoding='utf-8-sig'))
    if len(props['clips']) != 1 or props['clips'][0]['sourceStartFrame'] != 0:
        raise ValueError('Audio binding for edited clips is outside this continuous-source pilot')
    if Path(args.input).resolve() == Path(args.output).resolve():
        raise ValueError('Keep the uncorrected render as an independent input')
    helpers = runpy.run_path(str(Path(__file__).with_name('verify-source-audio.py')))
    compare = helpers['compare_audio_clocks']
    before = compare(args.reference, args.input)
    lags = [check['lagSeconds'] for check in before]
    if any(check['normalizedCorrelation'] < .9 for check in before) or max(lags) - min(lags) > .005:
        raise ValueError('Audio mismatch or changing drift requires review, not a constant-offset correction')
    advance = -median(lags)
    if abs(advance) > .15:
        raise ValueError('Unexpectedly large latency requires review')
    duration = props['durationInFrames'] / props['fps']
    timing_filter = (f'atrim=start={advance:.9f},asetpts=PTS-STARTPTS' if advance > 0 else
                     f'adelay={-advance * 1000:.6f}:all=1,asetpts=PTS-STARTPTS')
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', args.input,
               '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'copy', '-af',
               f'{timing_filter},apad,atrim=duration={duration:.9f}', '-c:a', 'aac',
               '-b:a', '160k', '-t', f'{duration:.9f}', '-movflags', '+faststart', args.output]
    subprocess.run(command, check=True)
    after = compare(args.reference, args.output)
    passed = all(check['normalizedCorrelation'] >= .9 and abs(check['lagSeconds']) <= 1 / props['fps'] for check in after)
    report = {'schemaVersion': '0.1.0', 'status': 'passed' if passed else 'needs_review',
              'input': args.input, 'output': args.output, 'reference': args.reference,
              'audioAdvancedSeconds': advance, 'durationSeconds': duration,
              'videoReencoded': False, 'before': before, 'after': after}
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'audioAdvancedSeconds': advance, 'after': after}))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
