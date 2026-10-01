"""CLI entry point for Jed's existing local Video Use installation."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from jed_video_use.transcription import run_transcription


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Content-addressed local WhisperX transcription")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("work/transcripts"))
    parser.add_argument("--skill-root", type=Path, default=Path.home() / ".codex/skills/video-use")
    parser.add_argument("--python", type=Path, default=Path("D:/AI-Runtimes/video-use-whisperx/.venv/Scripts/python.exe"))
    parser.add_argument("--model-dir", type=Path, default=Path("D:/AI-Models/whisperx"))
    args = parser.parse_args()
    try:
        result = run_transcription(args.source, args.output_root, args.skill_root, args.python, args.model_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
