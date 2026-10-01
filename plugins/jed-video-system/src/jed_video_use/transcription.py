"""Content-addressed, local-only WhisperX adapter using the installed helper."""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ADAPTER_VERSION = "0.1.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_key(source_hash: str, configuration: dict, helper_hashes: dict, versions: dict) -> str:
    identity = {"sourceSha256": source_hash, "configuration": configuration,
                "helperHashes": helper_hashes, "runtimeVersions": versions,
                "adapterVersion": ADAPTER_VERSION}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_interval(start, end, duration: float, label: str) -> None:
    if isinstance(start, bool) or isinstance(end, bool):
        raise ValueError(f"{label}: boolean timestamp")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        raise ValueError(f"{label}: missing/non-numeric timestamp")
    if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= duration + .001:
        raise ValueError(f"{label}: illegal source interval {start}..{end}, duration {duration}")


def normalize(raw: dict, source: dict, provenance: dict) -> dict:
    """Preserve helper source segments and mark uncertain normalized boundaries.

    The helper retains raw aligned segments, so known interpolation is detectable
    by matching normalized tokens sequentially against the original aligned tokens.
    If matching is ambiguous, conservatively mark the boundary as approximate.
    """
    duration = source["durationSeconds"]
    segments = []
    original_tokens = []
    for index, segment in enumerate(raw.get("source_segments", [])):
        start, end = segment.get("start"), segment.get("end")
        validate_interval(start, end, duration, f"segment {index}")
        segment_id = f"segment-{index:03d}"
        segments.append({"id": segment_id, "text": segment.get("text", ""),
                         "sourceTime": {"start": start, "end": end},
                         "timingQuality": "asr_segment", "approximateBoundary": True})
        for token in segment.get("words", []):
            value = str(token.get("word", token.get("text", ""))).strip()
            if value and any(char.isalnum() or "\u3400" <= char <= "\u9fff" for char in value):
                original_tokens.append((value, token, segment_id))

    words = []
    previous_end = 0.0
    pointer = 0
    for entry in raw.get("words", []):
        if entry.get("type") != "word":
            continue
        start, end = entry.get("start"), entry.get("end")
        validate_interval(start, end, duration, f"word {len(words)}")
        if start < previous_end - .001:
            raise ValueError(f"word {len(words)}: out-of-order/overlapping source interval")
        previous_end = end
        quality, segment_id = "unknown", None
        if pointer < len(original_tokens):
            text, original, candidate_id = original_tokens[pointer]
            if str(entry.get("text", "")).startswith(text):
                pointer += 1
                segment_id = candidate_id
                original_start, original_end = original.get("start"), original.get("end")
                if original_start is None or original_end is None:
                    quality = "interpolated"
                elif abs(start - original_start) <= .0011 and abs(end - original_end) <= .0011:
                    quality = "forced_aligned"
                else:
                    quality = "helper_adjusted"
        words.append({"id": f"word-{len(words):04d}", "text": entry.get("text", ""),
                      "sourceTime": {"start": start, "end": end},
                      "segmentId": segment_id, "speakerId": entry.get("speaker_id", "speaker_0"),
                      "confidence": entry.get("confidence"), "timingQuality": quality,
                      "approximateBoundary": quality != "forced_aligned"})
    if not words:
        raise ValueError("helper returned no word-level transcript")
    return {"schemaVersion": "0.1.0", "source": source, "provenance": provenance,
            "language": raw.get("language_code", "unknown"), "text": raw.get("text", ""),
            "segments": segments, "words": words,
            "quality": {"wordCount": len(words),
                        "approximateWordCount": sum(w["approximateBoundary"] for w in words),
                        "helperStats": raw.get("stats", {}),
                        "manualReviewComplete": False,
                        "note": "Forced alignment is an estimate; approximate tokens require review before precise cuts."}}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def run_transcription(source: Path, output_root: Path, skill_root: Path, python: Path,
                      model_dir: Path, *, configuration: dict | None = None) -> dict:
    source, output_root = source.resolve(), output_root.resolve()
    config = {"backend": "whisperx", "model": "large-v3-turbo", "device": "cuda",
              "computeType": "float16", "batchSize": 4, "language": "zh", "diarize": False}
    config.update(configuration or {})
    if config["backend"] != "whisperx" or config["diarize"]:
        raise ValueError("This adapter only enables local, single-speaker WhisperX")
    if not source.is_file():
        raise FileNotFoundError(source)
    helper = skill_root / "helpers" / "transcribe.py"
    runner = skill_root / "helpers" / "whisperx_runner.py"
    helper_hashes = {path.name: sha256_file(path) for path in [helper, runner]}
    query = "import importlib.metadata as m,json; print(json.dumps({k:m.version(k) for k in ['whisperx','torch','faster-whisper','ctranslate2']}))"
    versions = json.loads(subprocess.check_output([str(python), "-c", query], text=True))
    source_hash = sha256_file(source)
    key = cache_key(source_hash, config, helper_hashes, versions)
    cache_dir = output_root / key
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "manifest.json"
    normalized_path = cache_dir / "transcript.json"
    if manifest_path.is_file() and normalized_path.is_file():
        cached = json.loads(manifest_path.read_text(encoding="utf-8"))
        if cached.get("status") == "succeeded" and cached.get("cacheKey") == key:
            payload = json.loads(normalized_path.read_text(encoding="utf-8"))
            if payload["source"]["sha256"] != source_hash:
                raise ValueError("Cached transcript source hash does not match the immutable input")
            for word in payload["words"]:
                validate_interval(**word["sourceTime"], duration=payload["source"]["durationSeconds"], label=word["id"])
            for segment in payload["segments"]:
                validate_interval(**segment["sourceTime"], duration=payload["source"]["durationSeconds"], label=segment["id"])
            cached.update({"runtimePython": str(python.resolve()), "modelDirectory": str(model_dir.resolve())})
            write_json(manifest_path, cached)
            return {**cached, "cacheHit": True}
    duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(source)], text=True))
    manifest = {"cacheKey": key, "cacheHit": False, "status": "running",
                "sourcePath": str(source), "sourceSha256": source_hash,
                "configuration": config, "helperHashes": helper_hashes,
                "runtimeVersions": versions, "adapterVersion": ADAPTER_VERSION,
                "runtimePython": str(python.resolve()), "modelDirectory": str(model_dir.resolve()),
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "normalizedTranscript": str(normalized_path), "log": str(cache_dir / "helper.log")}
    write_json(manifest_path, manifest)
    command = [str(python), str(helper), str(source), "--edit-dir", str(cache_dir),
               "--backend", "whisperx", "--model", config["model"], "--device", config["device"],
               "--compute-type", config["computeType"], "--batch-size", str(config["batchSize"]),
               "--language", config["language"]]
    environment = dict(os.environ)
    environment.update({"WHISPERX_PYTHON": str(python), "WHISPERX_MODEL_DIR": str(model_dir),
                        "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"})
    try:
        with (cache_dir / "helper.log").open("w", encoding="utf-8") as log:
            process = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
        if process.returncode:
            raise RuntimeError(f"Video Use helper failed with exit code {process.returncode}; see {cache_dir / 'helper.log'}")
        raw_path = cache_dir / "transcripts" / f"{source.stem}.json"
        if sha256_file(source) != source_hash:
            raise RuntimeError("Source changed during transcription; cache cannot be associated with the initial hash")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        source_record = {"path": str(source), "sha256": source_hash, "durationSeconds": duration}
        payload = normalize(raw, source_record, {"cacheKey": key, "adapterVersion": ADAPTER_VERSION,
                                                "configuration": config, "helperHashes": helper_hashes,
                                                "runtimeVersions": versions})
        write_json(normalized_path, payload)
        manifest.update({"status": "succeeded", "rawTranscript": str(raw_path),
                         "wordCount": len(payload["words"]),
                         "approximateWordCount": payload["quality"]["approximateWordCount"]})
        write_json(manifest_path, manifest)
        return manifest
    except Exception as error:
        manifest.update({"status": "failed", "error": str(error)})
        write_json(manifest_path, manifest)
        raise
