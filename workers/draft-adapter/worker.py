"""Small new-draft worker using the locally pinned fork and existing Bridge.

stdin/stdout JSON is the boundary. It never edits an existing user draft.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from fractions import Fraction


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def frame_us(frame, fps):
    """Round a boundary once, rather than summing rounded frame durations."""
    if type(frame) is not int or frame < 0 or type(fps) is not int or fps < 1:
        raise ValueError("frame must be a nonnegative integer; fps must be positive")
    return round(Fraction(frame * 1_000_000, fps))


def span_us(start, duration, fps):
    if type(duration) is not int or duration <= 0:
        raise ValueError("durationFrames must be a positive integer")
    a, b = frame_us(start, fps), frame_us(start + duration, fps)
    return {"start": a, "duration": b - a}


def existing_file(raw):
    result = Path(raw).resolve()
    if not result.is_file():
        raise FileNotFoundError(str(result))
    return result


def metadata(path):
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                          capture_output=True, encoding="utf-8", timeout=60, check=True)
    data = json.loads(proc.stdout)
    stream = next((v for v in data["streams"] if v["codec_type"] == "video"), None)
    return {"durationUs": round(float(data["format"].get("duration", 0)) * 1_000_000),
            "video": stream, "streams": data["streams"]}


def validate_spec(spec):
    if spec.get("schemaVersion") != "jed-draft-probe/1":
        raise ValueError("unsupported schemaVersion")
    fps = spec.get("fps", 30)
    if type(fps) is not int or fps not in (30, 60):
        raise ValueError("this probe supports integer 30 or 60 fps only")
    span_us(0, spec["durationFrames"], fps)
    name = spec.get("name", "")
    if not re.fullmatch(r"jed-probe-[A-Za-z0-9_-]{1,72}", name):
        raise ValueError("name must be a distinct jed-probe-* name")
    start_us = spec.get("sourceStartUs", 0)
    if type(start_us) is not int or start_us < 0:
        raise ValueError("sourceStartUs must be a nonnegative integer")
    if not isinstance(spec.get("testText", "可编辑文字 · Alpha 检查"), str):
        raise ValueError("testText must be text")
    if not 0 <= spec.get("soundStartFrame", 15) < spec["durationFrames"]:
        raise ValueError("sound cue must be inside the draft")
    return spec


def import_bridge(spec):
    project = Path(spec["bridgeProject"]).resolve()
    if not (project / "jianying_bridge" / "core.py").is_file():
        raise FileNotFoundError("bridgeProject must point to the existing Jianying Bridge")
    sys.path.insert(0, str(project))
    from jianying_bridge.core import Bridge
    import pyJianYingDraft as draft
    return Bridge, draft, read_json(spec["bridgeConfig"])


def media_probe(spec):
    _, draft, _ = import_bridge(spec)
    results = []
    for raw in spec["paths"]:
        path = existing_file(raw)
        info = metadata(path)
        try:
            material = draft.VideoMaterial(str(path))
            parsed = {"status": "passed", "width": material.width, "height": material.height,
                      "durationUs": material.duration}
        except Exception as exc:
            parsed = {"status": "failed", "error": str(exc), "type": type(exc).__name__}
        results.append({"path": str(path), "sha256": sha256(path), "ffprobe": info,
                        "pyJianYingDraftMediaInfo": parsed,
                        "editorAlphaPlayback": "pending_ui_verification"})
    package = importlib.metadata.distribution("pyJianYingDraft")
    direct_url = package.read_text("direct_url.json")
    return {"schemaVersion": "jed-media-probe/1", "runtime": {"python": sys.executable,
            "pyJianYingDraft": package.version, "installationSource": json.loads(direct_url) if direct_url else None},
            "results": results}


def inspect_source(spec):
    Bridge, _, config = import_bridge(spec)
    bridge = Bridge(config)
    source = bridge.source(spec["sourceName"])
    file, _ = bridge.layout(source)
    content, encrypted = bridge.read(file)
    materials = {v["id"]: v for v in content["materials"].get("videos", [])}
    segments = []
    for track in content["tracks"]:
        if track["type"] != "video":
            continue
        for segment in track.get("segments", []):
            material = materials.get(segment["material_id"], {})
            segments.append({"segmentId": segment["id"], "path": material.get("path"),
                             "exists": Path(material.get("path", "")).is_file(),
                             "materialDurationUs": material.get("duration"),
                             "source": segment.get("source_timerange"), "target": segment.get("target_timerange")})
    return {"sourceName": spec["sourceName"], "readOnly": True, "encrypted": encrypted, "videoSegments": segments}


def structure_check(content, expected_duration):
    if content["duration"] != expected_duration:
        raise ValueError("unexpected draft duration")
    segment_ids = [s["id"] for t in content["tracks"] for s in t.get("segments", [])]
    if len(set(segment_ids)) != len(segment_ids):
        raise ValueError("duplicate segment IDs")
    materials = {v["id"] for values in content["materials"].values() if isinstance(values, list)
                 for v in values if isinstance(v, dict) and "id" in v}
    for index, track in enumerate(content["tracks"]):
        for segment in track.get("segments", []):
            if segment["material_id"] not in materials:
                raise ValueError("segment references a missing material")
            if track["type"] in ("video", "text", "sticker") and segment.get("render_index") != index:
                raise ValueError("unexpected render_index")
            for ref in segment.get("extra_material_refs", []):
                if ref not in materials:
                    raise ValueError(f"missing extra material reference: {ref}")
            target = segment["target_timerange"]
            if target.get("start", 0) < 0 or target["duration"] <= 0 or target.get("start", 0) + target["duration"] > expected_duration:
                raise ValueError("segment outside project")
    return {"status": "passed", "trackTypes": [t["type"] for t in content["tracks"]],
            "segmentCount": len(segment_ids), "visualLayerPlayback": "pending_ui_verification"}


def set_publication_root(bridge, directory, configured_root):
    """The existing publisher rebases inside-draft paths, not the parent draft root."""
    if configured_root:
        path = directory / "draft_meta_info.json"
        data, encrypted = bridge.read(path)
        data["draft_root_path"] = str(Path(configured_root).resolve())
        bridge.write(path, data, encrypted)


def build(spec, publish=False):
    validate_spec(spec)
    Bridge, draft, bridge_config = import_bridge(spec)
    fps, duration_frames = spec.get("fps", 30), spec["durationFrames"]
    duration = span_us(0, duration_frames, fps)["duration"]
    source, overlay, sound = [existing_file(spec[key]) for key in ("source", "overlay", "sound")]
    font = existing_file(spec["font"]) if spec.get("font") else None
    source_info, overlay_info, sound_info = [metadata(p) for p in (source, overlay, sound)]
    source_start = spec.get("sourceStartUs", 0)
    if source_start + duration > source_info["durationUs"] + 1_000:
        raise ValueError("source trim exceeds media duration")
    if overlay.suffix.lower() != ".png" and overlay_info["durationUs"] + 1_000 < duration:
        raise ValueError("overlay cannot be stretched past its rendered duration")
    sound_start = frame_us(spec.get("soundStartFrame", 15), fps)
    sound_duration = min(sound_info["durationUs"], duration - sound_start)
    if sound_duration <= 0:
        raise ValueError("empty sound range")
    base_dir = Path(spec["outputRoot"]).resolve()
    invocation = base_dir / uuid.uuid4().hex
    invocation.mkdir(parents=True, exist_ok=False)
    try:
        stage = invocation / "staging"
        stage.mkdir()
        # Explicit isolated User Data is essential: the fork defaults to the actual app index.
        isolated_user = invocation / "isolated-user-data"
        folder = draft.DraftFolder(str(stage), user_data_path=str(isolated_user))
        initial_name = spec["name"] + "-baseline"
        script = folder.create_draft(initial_name, 1920, 1080, fps, maintrack_adsorb=False)
        base_track = script.append_track(draft.TrackSpec(draft.TrackType.video, name="Jed · Base footage"))
        overlay_track = script.insert_track(draft.TrackSpec(draft.TrackType.video, name="Jed · Alpha overlay"), over_track=base_track)
        text_track = script.insert_track(draft.TrackSpec(draft.TrackType.text, name="Jed · Editable test text"), over_track=overlay_track)
        base_segment = draft.VideoSegment(str(source), draft.Timerange(0, duration),
                                         source_timerange=draft.Timerange(source_start, duration), volume=1)
        # Images have no source duration restriction in the material API.
        overlay_segment = draft.VideoSegment(str(overlay), draft.Timerange(0, duration), volume=0)
        text_segment = draft.TextSegment(spec.get("testText", "可编辑文字 · Alpha 检查"), draft.Timerange(0, duration),
                                         font_path=str(font) if font else None,
                                         style=draft.TextStyle(size=6, color=(1, 1, 1), align=1),
                                         border=draft.TextBorder(width=20),
                                         clip_settings=draft.ClipSettings(transform_y=-0.76))
        script.add_segment(base_segment, base_track)
        script.add_segment(overlay_segment, overlay_track)
        script.add_segment(text_segment, text_track)
        script.save(inline_materials=True)
        config = {**bridge_config, "draft_root": str(stage), "work_root": str(invocation / "bridge-work")}
        bridge = Bridge(config)
        if bridge.draft_root != stage.resolve():
            raise ValueError("JIANYING_DRAFT_ROOT overrides the isolated stage; clear that environment override before building")
        set_publication_root(bridge, stage / initial_name, bridge_config.get("draft_root"))
        prepared = bridge.prepare(initial_name, spec["name"], [{"path": str(sound),
            "start_seconds": sound_start / 1e6, "duration_seconds": sound_duration / 1e6,
            "source_start_seconds": 0, "volume": spec.get("soundVolume", .08),
            "fade_in_seconds": min(.01, sound_duration / 4e6),
            "fade_out_seconds": min(.05, sound_duration / 4e6), "label": "Jed alpha probe cue"}], "single")
        built = bridge.build(prepared["plan_id"])
        build_dir, bridge_manifest = bridge.load_build(built["build_id"])
        final_path = Path(built["draft_path"])
        content, _ = bridge.read(final_path / bridge_manifest["timeline_relative"])
        checked = structure_check(content, duration)
        manifest = {"schemaVersion": "jed-draft-result/1", "buildId": built["build_id"], "name": spec["name"],
                    "draftPath": str(final_path), "draftId": content["id"], "published": False,
                    "canvas": {"width": 1920, "height": 1080}, "fps": fps, "durationFrames": duration_frames,
                    "durationUs": duration, "sourceStartUs": source_start,
                    "sourceDraftModified": False, "bridgeManifest": str(build_dir / "manifest.json"),
                    "media": [{"role": role, "path": str(path), "sha256": sha256(path), "metadata": info}
                              for role, path, info in [("base", source, source_info), ("overlay", overlay, overlay_info), ("sound", sound, sound_info)]],
                    "tracks": [{"id": t["id"], "name": t.get("name"), "type": t["type"],
                                "segments": [{"id": s["id"], "materialId": s["material_id"],
                                              "sourceUs": s.get("source_timerange"), "targetUs": s["target_timerange"],
                                              "renderIndex": s.get("render_index")} for s in t["segments"]]} for t in content["tracks"]],
                    "checks": {"structure": checked, "bridge": built,
                               "uiOpen": "pending", "uiPlayback": "pending", "uiSaveReopen": "pending", "editorExport": "pending",
                               "computerUse": "Windows Computer Use Sky runtime is unavailable"}}
        manifest_path = invocation / "draft-manifest.json"
        write_json(manifest_path, manifest)
        if publish:
            # Existing Bridge owns the lock, backup, app-running checks and index transaction.
            publishing = Bridge({**bridge_config, "work_root": str(invocation / "bridge-work")})
            try:
                if bridge_config.get("draft_root") and publishing.draft_root != Path(bridge_config["draft_root"]).resolve():
                    raise ValueError("JIANYING_DRAFT_ROOT overrides the configured publication root")
                published = publishing.publish(built["build_id"])
                manifest.update(published=True, draftPath=published["draft_path"], publication=published)
            except Exception as exc:
                manifest["publication"] = {"published": False, "error": str(exc), "type": type(exc).__name__}
            write_json(manifest_path, manifest)
        return {"manifest": str(manifest_path), **manifest}
    except Exception as exc:
        write_json(invocation / "failure-report.json", {"error": str(exc), "type": type(exc).__name__, "stageRetained": str(invocation)})
        raise


def validate_preview(props):
    fps, total = props.get("fps"), props.get("durationInFrames")
    if type(fps) is not int or fps not in (30, 60):
        raise ValueError("preview supports 30/60 integer fps")
    span_us(0, total, fps)
    clips = props.get("clips", [])
    if len(clips) != 1 or clips[0].get("sourceStartFrame") != 0 or clips[0].get("outputStartFrame") != 0 or clips[0].get("durationInFrames") != total:
        raise ValueError("preview worker currently accepts one uninterrupted source clip starting at zero")
    previous_end = 0
    for caption in props.get("captions", []):
        start, end = caption.get("startFrame"), caption.get("endFrame")
        if type(start) is not int or type(end) is not int or start < previous_end or end <= start or end > total:
            raise ValueError("captions must be sorted, non-overlapping, inside the output")
        if not isinstance(caption.get("text"), str) or not caption["text"].strip():
            raise ValueError("empty or non-text caption")
        previous_end = end
    previous_end = 0
    ids = set()
    for event in props.get('chapterTransitions', []):
        start, length = event.get('outputStartFrame'), event.get('durationInFrames')
        if type(start) is not int or type(length) is not int or start < previous_end or length < 1 or start + length > total:
            raise ValueError('chapter transitions must be ordered, non-overlapping and inside the output')
        if not isinstance(event.get('id'), str) or not event['id'] or event['id'] in ids:
            raise ValueError('chapter IDs must be distinct')
        if event.get('audioPolicy') != 'continue_source':
            raise ValueError('chapter draft only covers a bridge with source audio continuing')
        ids.add(event['id'])
        previous_end = start + length
    return props


def chapter_event_digest(event):
    return hashlib.sha256(json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def chapter_media(props, spec):
    events = props.get('chapterTransitions', [])
    supplied = spec.get('chapterMedia', [])
    if not isinstance(supplied, list) or len(supplied) != len(events):
        raise ValueError('Every chapter event needs exactly one rendered asset')
    ids = [item.get('id') for item in supplied]
    if len(set(ids)) != len(ids) or set(ids) != {event['id'] for event in events}:
        raise ValueError('chapter media IDs differ from the timeline')
    by_id = {item['id']: item for item in supplied}
    checked = []
    for event in events:
        item = by_id[event['id']]
        path = existing_file(item['path'])
        if item.get('eventDigest') != chapter_event_digest(event) or sha256(path) != item.get('sha256'):
            raise ValueError('chapter asset or event differs from its render receipt')
        info = metadata(path)
        video = info['video'] or {}
        required = span_us(0, event['durationInFrames'], props['fps'])['duration']
        if info['durationUs'] + 1000 < required or video.get('codec_name') != 'prores' or not video.get('pix_fmt', '').startswith('yuva') or video.get('width') != 1920 or video.get('height') != 1080:
            raise ValueError('chapter asset needs matching-duration 1920x1080 ProRes Alpha')
        if Fraction(video.get('avg_frame_rate', '0/1')) != props['fps']:
            raise ValueError('chapter asset frame rate differs from timeline')
        checked.append({'event': event, 'path': path, 'metadata': info})
    return checked


def preview(spec, publish=False):
    """Original voice, editable captions and optional upper chapter Alpha track."""
    if spec.get("schemaVersion") != "jed-draft-preview/1" or "sound" in spec:
        raise ValueError("preview requires jed-draft-preview/1 and does not accept a sound asset")
    props_path = existing_file(spec["renderProps"])
    props = validate_preview(read_json(props_path))
    chapters = chapter_media(props, spec)
    normalized = {**spec, "schemaVersion": "jed-draft-probe/1", "fps": props["fps"], "durationFrames": props["durationInFrames"]}
    validate_spec(normalized)
    Bridge, draft, bridge_config = import_bridge(spec)
    from jianying_bridge.core import digest, remap_paths
    source, overlay = existing_file(spec["source"]), existing_file(spec["overlay"])
    font = existing_file(spec["font"])
    fps, duration_frames = props["fps"], props["durationInFrames"]
    overlay_frames = spec.get("overlayDurationFrames", 348)
    overlay_duration = span_us(0, overlay_frames, fps)["duration"]
    if overlay_frames > duration_frames:
        raise ValueError("overlay ends after source")
    duration = frame_us(duration_frames, fps)
    source_info, overlay_info = metadata(source), metadata(overlay)
    if source_info["durationUs"] + 1000 < duration or overlay_info["durationUs"] + 1000 < overlay_duration:
        raise ValueError("media duration is insufficient")
    invocation = Path(spec["outputRoot"]).resolve() / uuid.uuid4().hex
    invocation.mkdir(parents=True, exist_ok=False)
    try:
        stage = invocation / "staging"
        stage.mkdir()
        folder = draft.DraftFolder(str(stage), user_data_path=str(invocation / "isolated-user-data"))
        baseline_name = spec["name"] + "-baseline"
        script = folder.create_draft(baseline_name, 1920, 1080, fps, maintrack_adsorb=False)
        base_track = script.append_track(draft.TrackSpec(draft.TrackType.video, "Jed · Original footage and voice"))
        overlay_track = script.insert_track(draft.TrackSpec(draft.TrackType.video, "Jed · Approved A overlay"), over_track=base_track)
        caption_track = script.insert_track(draft.TrackSpec(draft.TrackType.text, "Jed · Editable original captions"), over_track=overlay_track)
        if chapters:
            chapter_track = script.insert_track(draft.TrackSpec(draft.TrackType.video, "Jed · Chapter transitions"), over_track=caption_track)
        script.add_segment(draft.VideoSegment(str(source), draft.Timerange(0, duration), source_timerange=draft.Timerange(0, duration), volume=1), base_track)
        script.add_segment(draft.VideoSegment(str(overlay), draft.Timerange(0, overlay_duration), volume=0), overlay_track)
        for caption in props.get("captions", []):
            timerange = span_us(caption["startFrame"], caption["endFrame"] - caption["startFrame"], fps)
            script.add_segment(draft.TextSegment(caption["text"], draft.Timerange(**timerange), font_path=str(font),
                style=draft.TextStyle(size=5, color=(1, 1, 1), align=1), border=draft.TextBorder(width=8),
                clip_settings=draft.ClipSettings(transform_y=-.8)), caption_track)
        for item in chapters:
            event = item['event']
            target_range = span_us(event['outputStartFrame'], event['durationInFrames'], fps)
            script.add_segment(draft.VideoSegment(str(item['path']), draft.Timerange(**target_range),
                source_timerange=draft.Timerange(0, target_range['duration']), volume=0), chapter_track)
        script.save(inline_materials=True)
        baseline = stage / baseline_name
        bridge = Bridge({**bridge_config, "draft_root": str(stage), "work_root": str(invocation / "bridge-work")})
        if bridge.draft_root != stage.resolve():
            raise ValueError("environment overrides the isolated stage")
        set_publication_root(bridge, baseline, bridge_config.get("draft_root"))
        # Bridge's verifier accepts a neutral material-preserving build as well as audio additions.
        # Visual assembly is already complete; no fabricated sound event is needed for publication.
        build_id = uuid.uuid4().hex
        build_dir = bridge.work / "builds" / build_id
        target = build_dir / spec["name"]
        shutil.copytree(baseline, target)
        (build_dir / "baseline").mkdir()
        files = {}
        for relative in ("draft_info.json", "draft_meta_info.json"):
            raw = (baseline / relative).read_bytes()
            (build_dir / "baseline" / relative).write_bytes(raw)
            data, encrypted = bridge.read(baseline / relative)
            updated = remap_paths(data, baseline, target)
            if relative == "draft_meta_info.json":
                updated["draft_name"] = spec["name"]
            bridge.write(target / relative, updated, encrypted)
            files[relative] = {"encrypted": encrypted, "baseline_sha256": digest(raw), "expected_hash": bridge.semantic_hash(updated, target)}
        content, _ = bridge.read(target / "draft_info.json")
        checked = structure_check(content, duration)
        transfer = {"build_id": build_id, "plan_id": "visual-preview", "name": spec["name"],
            "source_name": baseline_name, "source_path": str(baseline), "source_fingerprints": bridge.fingerprints(baseline),
            "timeline_relative": "draft_info.json", "legacy": True, "draft_id": content["id"], "files": files,
            "aliases": {}, "embedded_audio": [], "new_track_ids": [], "new_segment_ids": [],
            "sound_track_ids": [], "track_mode": "independent", "consolidate_track_ids": []}
        write_json(build_dir / "manifest.json", transfer)
        verification = bridge.verify(build_id)
        manifest = {"schemaVersion": "jed-draft-result/1", "mode": "preview", "name": spec["name"],
            "buildId": build_id, "draftId": content["id"], "draftPath": str(target), "published": False,
            "canvas": {"width": 1920, "height": 1080}, "sourceDraftModified": False,
            "fps": fps, "durationFrames": duration_frames, "durationUs": duration, "overlayDurationFrames": overlay_frames,
            "renderProps": str(props_path), "renderPropsSha256": sha256(props_path), "addedSoundEffects": 0,
            "chapterTransitions": [{**item['event'], 'mediaSha256': sha256(item['path']),
                'eventDigest': chapter_event_digest(item['event']), 'editorTitleEditable': False,
                'titleEditableInRemotionProps': True} for item in chapters],
            "originalVoice": {"source": str(source), "volume": 1, "sourceStartUs": 0},
            "captionStyle": {"pixelSizeIntent": 40, "editorSize": 5, "white": True, "blackBorderWidth": 8,
                "bottomPixelIntent": 88, "transformY": -.8, "font": str(font), "pixelAccuracy": "pending_ui_verification"},
            "bridgeManifest": str(build_dir / "manifest.json"),
            "media": [{"role": role, "path": str(path), "sha256": sha256(path), "metadata": info}
                      for role, path, info in [("base", source, source_info), ("overlay", overlay, overlay_info)] +
                          [("chapter:" + item['event']['id'], item['path'], item['metadata']) for item in chapters]],
            "tracks": [{"id": t["id"], "name": t.get("name"), "type": t["type"],
                "segments": [{"id": s["id"], "materialId": s["material_id"], "sourceUs": s.get("source_timerange"),
                    "targetUs": s["target_timerange"], "renderIndex": s.get("render_index")} for s in t["segments"]]} for t in content["tracks"]],
            "checks": {"structure": checked, "bridge": verification, "uiOpen": "pending", "uiPlayback": "pending",
                       "uiSaveReopen": "pending", "editorExport": "pending", "computerUse": "Windows Computer Use Sky runtime is unavailable"}}
        manifest_path = invocation / "draft-manifest.json"
        write_json(manifest_path, manifest)
        if publish:
            publishing = Bridge({**bridge_config, "work_root": str(invocation / "bridge-work")})
            try:
                if bridge_config.get("draft_root") and publishing.draft_root != Path(bridge_config["draft_root"]).resolve():
                    raise ValueError("environment overrides configured publication root")
                result = publishing.publish(build_id)
                manifest.update(published=True, draftPath=result["draft_path"], publication=result)
            except Exception as exc:
                manifest["publication"] = {"published": False, "error": str(exc), "type": type(exc).__name__}
            write_json(manifest_path, manifest)
        return {"manifest": str(manifest_path), **manifest}
    except Exception as exc:
        write_json(invocation / "failure-report.json", {"error": str(exc), "type": type(exc).__name__, "stageRetained": str(invocation)})
        raise


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "preview", "probe", "inspect-source"))
    parser.add_argument("--input", help="UTF-8 JSON file; omit to read stdin")
    parser.add_argument("--publish", action="store_true", help="build only: call the existing Bridge publication transaction")
    args = parser.parse_args()
    try:
        spec = read_json(args.input) if args.input else json.load(sys.stdin)
        with contextlib.redirect_stdout(sys.stderr):
            if args.command == "build":
                result = build(spec, args.publish)
            elif args.command == "preview":
                result = preview(spec, args.publish)
            elif args.command == "probe":
                result = media_probe(spec)
            else:
                result = inspect_source(spec)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
