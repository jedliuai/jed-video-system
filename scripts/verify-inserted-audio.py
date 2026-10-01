"""Check inserted preview speech against mapped source and gap against sound only.

Run with the existing Video Use Python (NumPy/SciPy). This is timing evidence,
not a claim that a person listened or accepted the transition.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from scipy.signal import correlate, correlation_lags

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/jed-video-system/src'))
from jed_chapters.insertion import validate_inserted_timeline


RATE = 16000


def audio(path):
    process = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', str(RATE), '-f', 'f32le', '-'], capture_output=True, check=True)
    return np.frombuffer(process.stdout, dtype='<f4').astype(np.float64)


def compare(a, b):
    if len(a) != len(b) or len(a) < 1000 or np.linalg.norm(a) < 1e-6:
        raise ValueError('Need complete audible verification windows')
    scores = correlate(a, b, mode='full', method='fft')
    lags = correlation_lags(len(a), len(b), mode='full')
    allowed = np.flatnonzero(abs(lags) <= round(RATE / 30))
    lag = int(lags[allowed[np.argmax(scores[allowed])]])
    aa, bb = (a[lag:], b[:len(a)-lag]) if lag >= 0 else (a[:len(b)+lag], b[-lag:])
    similarity = float(np.dot(aa, bb) / (np.linalg.norm(aa) * np.linalg.norm(bb)))
    return {'lagSeconds': lag / RATE, 'normalizedCorrelation': similarity}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--props', required=True)
    parser.add_argument('--public-root', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    props = json.loads(Path(args.props).read_text(encoding='utf-8-sig'))
    validate_inserted_timeline(props)
    public = Path(args.public_root).resolve()
    source_path = public / props['sourceSrc']
    reference, candidate = audio(source_path), audio(args.candidate)
    fps = props['fps']
    def samples(frame):
        return round(frame * RATE / fps)
    checks = []
    for clip in props['clips']:
        # Interior windows avoid encoded cut edges; start/middle/end detect drift.
        duration = clip['durationInFrames']
        if duration < 12:
            raise ValueError('Source interval too short for interior audio QA')
        width = min(90, duration - 6)
        offsets = sorted({3, max(3, (duration - width) // 2), duration - width - 3})
        for offset in offsets:
            start_source = samples(clip['sourceStartFrame'] + offset)
            start_output = samples(clip['outputStartFrame'] + offset)
            length = samples(width)
            checks.append({'kind': 'mapped_speech', 'sourceStartFrame': clip['sourceStartFrame'] + offset,
                'outputStartFrame': clip['outputStartFrame'] + offset,
                **compare(reference[start_source:start_source+length], candidate[start_output:start_output+length])})
    for gap in props['insertions']:
        sound = next(sound for sound in props['soundEffects'] if sound['chapterId'] == gap['id'])
        expected = np.zeros(samples(gap['durationInFrames']))
        sound_audio = audio(public / sound['audioSrc'])[:samples(sound['durationInFrames'])]
        offset = samples(sound['outputStartFrame'] - gap['outputStartFrame'])
        expected[offset:offset + len(sound_audio)] = sound_audio
        start = samples(gap['outputStartFrame'])
        actual = candidate[start:start + len(expected)]
        checks.append({'kind': 'chapter_sound_only', 'chapterId': gap['id'], **compare(expected, actual)})
    passed = all(check['normalizedCorrelation'] >= .98 and abs(check['lagSeconds']) <= 1/fps for check in checks)
    report = {'status': 'passed' if passed else 'needs_review', 'checks': checks,
        'sourceSHA256': digest(source_path), 'candidateSHA256': digest(args.candidate),
        'propsSHA256': digest(args.props), 'subjectiveListeningApproved': False,
        'note': 'Interior speech windows and sound-only gaps checked; not exhaustive phoneme or editor-playback verification.'}
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
