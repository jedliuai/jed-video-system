"""Read-only intake CLI; optionally save its result JSON."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from jed_intake import evaluate


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig")) if path else None


def main():
    parser = argparse.ArgumentParser(description="Resolve conditional Jed video intake preferences.")
    parser.add_argument("--audit", required=True)
    parser.add_argument("--profile")
    parser.add_argument("--answers")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        result = evaluate(read(args.audit), read(args.profile), read(args.answers))
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload + "\n", encoding="utf-8")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(payload)
        return 0 if result["status"] == "ready_for_planning" else 2
    except (ValueError, OSError) as exc:
        print(f"Invalid intake input: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
