"""Plan/execute a fixed local action, preserving evidence and review boundaries."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jed_dispatch import dispatch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--capabilities', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        result = dispatch(Path(__file__).resolve().parents[3],
            json.loads(Path(args.request).read_text(encoding='utf-8-sig')),
            json.loads(Path(args.capabilities).read_text(encoding='utf-8-sig')),
            execute=args.execute)
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] in ('planned', 'succeeded') else 2
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Dispatch blocked: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
