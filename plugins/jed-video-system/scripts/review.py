"""Local review-state CLI. Never connects to ChatCut, Jianying, or Remotion."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from jed_review import evaluate_gate, new_state, record_decision, register_candidate, request_review, suggest_gates, validate_state


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def verify_local_artifact(candidate):
    """Check actual local bytes, not video aesthetics or whether anyone watched."""
    locator = candidate.get("locator", "")
    if "://" in locator:
        raise ValueError("URL evidence needs a host-side artifact verifier; this local CLI never downloads it")
    path = Path(locator)
    if not path.is_file():
        raise ValueError(f"local artifact does not exist: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != candidate.get("artifactDigest"):
        raise ValueError("local artifact SHA-256 differs from the registered candidate; register a new revision")


def verify_candidate_artifacts(state, candidate_id, verified=None):
    verified = set() if verified is None else verified
    if candidate_id in verified:
        return
    candidate = state["candidates"][candidate_id]
    verify_local_artifact(candidate)
    verified.add(candidate_id)
    for dependency in candidate["dependsOn"]:
        verify_candidate_artifacts(state, dependency, verified)


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as stream:
            temporary = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description="Version-bound local operator review receipts; no external editing.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init")
    init.add_argument("--state", required=True)
    init.add_argument("--project-id", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("--state", required=True)
    register.add_argument("--candidate", required=True)
    request = subparsers.add_parser("request")
    request.add_argument("--state", required=True)
    request.add_argument("--candidate-id", required=True)
    request.add_argument("--prompt", required=True)
    decide = subparsers.add_parser("decide")
    decide.add_argument("--state", required=True)
    decide.add_argument("--request-id", required=True)
    decide.add_argument("--decision", choices=("approved", "rejected", "revise"), required=True)
    decide.add_argument("--note", default="")
    decide.add_argument("--operator-label", default="operator")
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--state", required=True)
    evaluate.add_argument("--candidate-id", required=True)
    evaluate.add_argument("--intent")
    suggest = subparsers.add_parser("suggest")
    suggest.add_argument("--context", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            if Path(args.state).exists():
                raise ValueError("state already exists; init never overwrites review history")
            result = new_state(args.project_id)
        elif args.command == "suggest":
            result = suggest_gates(read_json(args.context))
        else:
            state = validate_state(read_json(args.state))
            if args.command == "register":
                candidate = read_json(args.candidate)
                verify_local_artifact(candidate)
                for dependency in candidate.get("dependsOn", []) + ([candidate["approvedSampleId"]] if candidate.get("approvedSampleId") else []):
                    verify_candidate_artifacts(state, dependency)
                result = register_candidate(state, candidate)
            elif args.command == "request":
                verify_candidate_artifacts(state, args.candidate_id)
                result = request_review(state, args.candidate_id, args.prompt)
            elif args.command == "decide":
                request = next((item for item in state["requests"] if item["requestId"] == args.request_id), None)
                if request is None:
                    raise ValueError("unknown requestId")
                verify_candidate_artifacts(state, request["candidateId"])
                result = record_decision(state, args.request_id, args.decision, args.note, args.operator_label)
            else:
                verify_candidate_artifacts(state, args.candidate_id)
                result = evaluate_gate(state, args.candidate_id, read_json(args.intent) if args.intent else None)
        if args.command in {"init", "register", "request", "decide"}:
            save_json(args.state, result)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.command != "evaluate" or result["allowed"] else 2
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"Invalid review input: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
