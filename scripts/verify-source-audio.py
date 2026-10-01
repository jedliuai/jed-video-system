"""Verify that a clean media excerpt shares the ASR source's audio clock."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from scipy.signal import correlate, correlation_lags


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audio(path):
    data = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-t', '40.8',
                           '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    return np.frombuffer(data, dtype='<f4').astype(np.float64)


def compare_audio_clocks(reference_path, candidate_path):
    reference, candidate = audio(reference_path), audio(candidate_path)
    # Check three distant windows; a single start match cannot rule out later drift.
    checks = []
    for start, end in ((0.5, 9.5), (14, 23), (30, 39)):
        a = reference[round(start * 16000):round(end * 16000)]
        b = candidate[round(start * 16000):round(end * 16000)]
        if min(len(a), len(b)) < 1000:
            raise ValueError('Audio does not cover every review window')
        a, b = a - a.mean(), b - b.mean()
        scores = correlate(a, b, mode='full', method='fft')
        lags = correlation_lags(len(a), len(b), mode='full')
        allowed = abs(lags) <= 4000
        index = np.flatnonzero(allowed)[np.argmax(scores[allowed])]
        lag = int(lags[index])
        # Positive lag means reference sound occurs later than candidate sound.
        aa, bb = (a[lag:], b[:len(a)-lag]) if lag >= 0 else (a[:len(b)+lag], b[-lag:])
        count = min(len(aa), len(bb))
        similarity = float(np.dot(aa[:count], bb[:count]) /
                           (np.linalg.norm(aa[:count]) * np.linalg.norm(bb[:count])))
        checks.append({'windowSeconds': [start, end], 'lagSeconds': lag / 16000,
                       'normalizedCorrelation': similarity})
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    checks = compare_audio_clocks(args.reference, args.candidate)
    passed = all(c['normalizedCorrelation'] >= 0.9 and abs(c['lagSeconds']) <= 1/30 for c in checks)
    result = {'schemaVersion': '0.1.0', 'status': 'passed' if passed else 'needs_review',
              'reference': {'path': str(Path(args.reference).resolve()), 'sha256': digest(args.reference)},
              'candidate': {'path': str(Path(args.candidate).resolve()), 'sha256': digest(args.candidate)},
              'checks': checks, 'toleranceSeconds': 1/30,
              'note': 'Audio correlation checks shared timing; it does not certify every ASR word or Jianying playback.'}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'checks': checks}))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
