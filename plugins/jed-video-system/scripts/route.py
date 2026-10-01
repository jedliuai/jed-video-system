"""Read-only backend routing and review requirements; no external mutations."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jed_routing import route_project


def main():
    parser = argparse.ArgumentParser(description='Plan external backends without executing.')
    parser.add_argument('--request', required=True)
    parser.add_argument('--capabilities', required=True)
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        request = json.loads(Path(args.request).read_text(encoding='utf-8-sig'))
        capabilities = json.loads(Path(args.capabilities).read_text(encoding='utf-8-sig'))
        result = route_project(request, capabilities)
        if 'reviewContext' in request:
            from jed_review import suggest_gates
            result['reviewRequirements'] = suggest_gates(request['reviewContext'])
        payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(payload, encoding='utf-8')
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        print(payload, end='')
        return 0 if result['status'] == 'route_ready' else 2
    except (ValueError, OSError) as exc:
        print(f'Invalid route input: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
