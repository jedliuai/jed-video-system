"""Compile chapter candidates, preserving the existing footage and audio clock."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jed_chapters import compile_chapters


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--structure', required=True)
    parser.add_argument('--props', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    try:
        structure = json.loads(Path(args.structure).read_text(encoding='utf-8-sig'))
        props_path = Path(args.props).resolve()
        props = json.loads(props_path.read_text(encoding='utf-8-sig'))
        public = (root / 'motion-lab/public').resolve()
        source = (public / structure['source']['publicFile']).resolve()
        art = (public / structure['style']['referenceAsset']).resolve()
        if not source.is_relative_to(public) or not art.is_relative_to(public):
            raise ValueError('Chapter media must stay inside the bound public directory')
        if digest(art) != structure['style']['referenceSha256']:
            raise ValueError('Reference art changed; reconsider the style candidate')
        output = Path(args.output).resolve()
        if output == props_path or output == Path(args.structure).resolve() or output.is_relative_to(public):
            raise ValueError('Write chapter candidates separately from source inputs')
        result = compile_chapters(structure, props, digest(props_path), digest(source))
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix('.tmp')
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(output)
        print(f'Chapter candidate: {output}; humanApproved=false')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Chapter compilation blocked: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
