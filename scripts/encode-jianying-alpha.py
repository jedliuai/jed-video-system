"""Encode fresh Remotion PNG frames for a premultiplied-alpha editor.

The explicit unknown tag prevents FFmpeg 8's automatic alpha conversion from
undoing the multiplication before ProRes encoding. Never apply to an old MOV.
The destination editor's actual playback must still be checked.
"""
import argparse
from pathlib import Path
import subprocess


def encode(frames, output, fps=30):
    directory, destination = Path(frames).resolve(), Path(output).resolve()
    if type(fps) is not int or fps <= 0:
        raise ValueError('fps must be a positive integer')
    sequence = sorted(directory.glob('element-*.png'))
    digits = len(sequence[0].stem.removeprefix('element-')) if sequence else 3
    if not sequence or digits < 3 or [p.name for p in sequence] != [f'element-{n:0{digits}d}.png' for n in range(len(sequence))]:
        raise ValueError('Expected a complete zero-based Remotion PNG sequence')
    if destination.exists():
        raise ValueError('Use a new output path; existing alpha media is never overwritten')
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-framerate', str(fps),
        '-i', str(directory / f'element-%0{digits}d.png'), '-vf',
        'format=gbrap16le,premultiply=inplace=1:planes=7,setparams=alpha_mode=unknown,format=yuva444p10le',
        '-c:v', 'prores_ks', '-profile:v', '4', '-alpha_bits', '16', '-an', str(destination)],
        check=True)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frames', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--fps', type=int, default=30)
    args = parser.parse_args()
    print(encode(args.frames, args.output, args.fps))
