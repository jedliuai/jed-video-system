"""One timeline mapping for live previews and isolated motion overlays.

Input is an explicitly authored plan. This compiler performs no client-intake
decisions, ASR inference, download, cutting, or rendering.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import math


def finite_number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label}: expected a finite number")
    return float(value)


def seconds_to_frame(seconds, fps: int) -> int:
    if isinstance(fps, bool) or not isinstance(fps, int) or fps not in (30, 60):
        raise ValueError("fps must be 30 or 60")
    finite_number(seconds, "seconds")
    return int((Decimal(str(seconds)) * fps).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def interval(item: dict, duration: float, label: str) -> tuple[float, float]:
    start = finite_number(item.get("sourceStartSeconds"), f"{label}.sourceStartSeconds")
    end = finite_number(item.get("sourceEndSeconds"), f"{label}.sourceEndSeconds")
    if not 0 <= start < end <= duration:
        raise ValueError(f"{label}: source interval must satisfy 0 <= start < end <= duration")
    return start, end


def compile_plan(plan: dict, transcript: dict) -> dict:
    if plan.get("schemaVersion") != "0.1.0":
        raise ValueError("Unsupported edit-plan schemaVersion")
    if not isinstance(plan.get("projectId"), str) or not plan["projectId"]:
        raise ValueError("projectId must be a nonempty string")
    fps = plan.get("fps")
    seconds_to_frame(0, fps)
    source = plan.get("source", {})
    duration = finite_number(source.get("durationSeconds"), "source.durationSeconds")
    if duration <= 0:
        raise ValueError("Source duration must be positive")
    public_file = source.get("publicFile")
    if not isinstance(public_file, str) or not public_file:
        raise ValueError("source.publicFile must be nonempty")
    transcript_hash = transcript.get("source", {}).get("sha256")
    if not transcript_hash or source.get("transcriptSourceSha256") != transcript_hash:
        raise ValueError("Transcript source SHA256 does not match plan.transcriptSourceSha256")
    transcript_duration = finite_number(transcript["source"].get("durationSeconds"), "transcript duration")
    if duration > transcript_duration + .001:
        raise ValueError("Plan exceeds the audited transcript time domain")

    words = {}
    previous_end = 0.0
    for word in transcript.get("words", []):
        word_id = word.get("id")
        if not isinstance(word_id, str) or word_id in words:
            raise ValueError("Transcript word IDs must be unique strings")
        timing = word.get("sourceTime", {})
        start = finite_number(timing.get("start"), f"{word_id}.start")
        end = finite_number(timing.get("end"), f"{word_id}.end")
        if not 0 <= start < end <= transcript_duration + .001 or start < previous_end - .001:
            raise ValueError(f"Invalid transcript interval/order for {word_id}")
        previous_end = end
        words[word_id] = word
    if not words:
        raise ValueError("Plan compilation requires an audited word-level transcript")

    compiled_clips, indexed_clips = [], {}
    output_cursor = 0
    original_ranges = []
    for clip in plan.get("clips", []):
        clip_id = clip.get("id")
        if not isinstance(clip_id, str) or not clip_id or clip_id in indexed_clips:
            raise ValueError("Clip IDs must be unique nonempty strings")
        speed = finite_number(clip.get("speed"), f"clip {clip_id}.speed")
        if speed != 1:
            raise ValueError("Only speed=1 is supported; retiming requires a separate mapping implementation")
        start, end = interval(clip, duration, f"clip {clip_id}")
        if any(max(start, prior_start) < min(end, prior_end) for prior_start, prior_end in original_ranges):
            raise ValueError(f"clip {clip_id}: overlapping source ranges are not supported")
        for word_id, word in words.items():
            word_start, word_end = word["sourceTime"]["start"], word["sourceTime"]["end"]
            if word_start < start < word_end or word_start < end < word_end:
                raise ValueError(f"clip {clip_id}: cut boundary is inside word {word_id}")
        source_start_frame, source_end_frame = seconds_to_frame(start, fps), seconds_to_frame(end, fps)
        frame_duration = source_end_frame - source_start_frame
        if frame_duration <= 0:
            raise ValueError(f"clip {clip_id}: empty frame interval after rounding")
        compiled = {"id": clip_id, "sourceStartFrame": source_start_frame,
                    "outputStartFrame": output_cursor, "durationInFrames": frame_duration}
        compiled_clips.append(compiled)
        indexed_clips[clip_id] = {"start": start, "end": end, **compiled}
        original_ranges.append((start, end))
        output_cursor += frame_duration
    if not compiled_clips:
        raise ValueError("Plan must contain at least one clip")

    def map_frame(time, clip):
        return clip["outputStartFrame"] + seconds_to_frame(time, fps) - clip["sourceStartFrame"]

    compiled_overlays, timing_review = [], []
    overlay_ids = set()
    for overlay in plan.get("overlays", []):
        overlay_id = overlay.get("id")
        if not isinstance(overlay_id, str) or not overlay_id or overlay_id in overlay_ids:
            raise ValueError("Overlay IDs must be unique nonempty strings")
        overlay_ids.add(overlay_id)
        clip = indexed_clips.get(overlay.get("clipId"))
        if clip is None:
            raise ValueError(f"overlay {overlay_id}: unknown clipId")
        start, end = interval(overlay, duration, f"overlay {overlay_id}")
        if start < clip["start"] or end > clip["end"]:
            raise ValueError(f"overlay {overlay_id}: event must be fully contained by its clip")
        event_start, event_end = map_frame(start, clip), map_frame(end, clip)
        if event_end <= event_start:
            raise ValueError(f"overlay {overlay_id}: empty frame interval after rounding")

        def anchor(word_id, role: str) -> int:
            word = words.get(word_id)
            if word is None:
                raise ValueError(f"overlay {overlay_id}: unknown anchor word {word_id}")
            word_start, word_end = word["sourceTime"]["start"], word["sourceTime"]["end"]
            if not start <= word_start < word_end <= end:
                raise ValueError(f"overlay {overlay_id}: anchor {word_id} must lie fully inside the event window")
            output_frame = map_frame(word_start, clip)
            local_frame = output_frame - event_start
            if not 0 <= local_frame < event_end - event_start:
                raise ValueError(f"overlay {overlay_id}: anchor {word_id} rounds outside the event frame window")
            quality = word.get("timingQuality", "unknown")
            approximate = word.get("approximateBoundary", True) or quality != "forced_aligned"
            timing_review.append({"wordId": word_id, "overlayId": overlay_id, "role": role,
                                  "text": word.get("text", ""), "sourceTime": deepcopy(word["sourceTime"]),
                                  "timingQuality": quality, "approximateBoundary": bool(approximate),
                                  "outputCueFrame": output_frame, "localCueFrame": local_frame,
                                  "manualAudioReviewComplete": transcript.get("quality", {}).get("manualReviewComplete", False)})
            return local_frame

        content = deepcopy(overlay.get("content", {}))
        if not isinstance(content, dict) or not isinstance(content.get("points", []), list):
            raise ValueError(f"overlay {overlay_id}: invalid content/points")
        headline_cue = anchor(overlay.get("headlineAnchorWordId"), "headline")
        for index, point in enumerate(content.get("points", [])):
            point["cueFrame"] = anchor(point.pop("anchorWordId", None), f"point-{index}")
        compiled_overlays.append({"id": overlay_id, "outputStartFrame": event_start,
                                  "durationInFrames": event_end - event_start,
                                  "headlineCueFrame": headline_cue, "content": content})

    compiled_captions = []
    for index, caption in enumerate(plan.get("captions", [])):
        start, end = interval(caption, duration, f"caption {index}")
        text = caption.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError(f"caption {index}: text must be nonempty")
        for clip in indexed_clips.values():
            intersection_start, intersection_end = max(start, clip["start"]), min(end, clip["end"])
            if intersection_start < intersection_end:
                start_frame, end_frame = map_frame(intersection_start, clip), map_frame(intersection_end, clip)
                if start_frame >= end_frame:
                    raise ValueError(f"caption {index}: retained intersection is shorter than a displayable frame")
                compiled_captions.append({"startFrame": start_frame, "endFrame": end_frame, "text": text})
    compiled_captions.sort(key=lambda caption: (caption["startFrame"], caption["endFrame"]))
    return {"sourceSrc": public_file, "fps": fps, "durationInFrames": output_cursor,
            "clips": compiled_clips, "overlays": compiled_overlays,
            "captions": compiled_captions, "timingReview": timing_review}
