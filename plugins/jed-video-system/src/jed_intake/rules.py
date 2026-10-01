"""Resolve reachable questions separately from a future executable edit plan."""

from math import isfinite

VERSION = "0.1.0"
KINDS = ("talking_head", "screen_recording", "other")
CONFIDENCE_THRESHOLD = 0.8
CHOICES = {
    "broll.talking_head": (False, True),
    "broll.screen_recording": (False, True),
    "motion.screen_recording": (False, True),
    "speech.edit_mode": ("preserve", "review_trim"),
    "sound.mode": ("none", "subtle", "expressive"),
}
PROMPTS = {
    "broll.talking_head": "口播部分要加入 B-roll 吗？可以只使用人物与信息动效。",
    "broll.screen_recording": "已发现口播和教程录屏；录屏部分也要加入 B-roll 吗？",
    "motion.screen_recording": "录屏部分要加入重点圈画、局部放大或步骤标注吗？",
    "speech.edit_mode": "语音保持原节奏，还是先列出重复、口头语和较长停顿供审核后精修？",
    "sound.mode": "音效使用无音效、少量提示，还是较明显的节奏增强？",
}
SUGGESTIONS = {
    "broll.talking_head": False,
    "broll.screen_recording": False,
    "motion.screen_recording": True,
    "speech.edit_mode": "preserve",
    "sound.mode": "subtle",
}


def _document(document, name, fields):
    if not isinstance(document, dict) or document.get("schemaVersion") != VERSION:
        raise ValueError(f"{name} must be an object with schemaVersion={VERSION}")
    unknown = set(document) - fields
    if unknown:
        raise ValueError(f"Unknown {name} fields: {sorted(unknown)}")


def _mapping(document, key):
    values = document.get(key, {})
    if not isinstance(values, dict):
        raise ValueError(f"{key} must be an object")
    return values


def _preferences(values, name):
    for key, value in values.items():
        if key not in CHOICES:
            raise ValueError(f"Unknown {name} key: {key}")
        # bool is a subtype of int: do not accept 0/1 as a client's answer.
        if not any(type(value) is type(choice) and value == choice for choice in CHOICES[key]):
            raise ValueError(f"Invalid {name} value for {key}: {value!r}")


def _segments(audit):
    if not isinstance(audit.get("projectId"), str) or not audit["projectId"].strip():
        raise ValueError("projectId must be a nonempty string")
    if type(audit.get("transcriptReady")) is not bool:
        raise ValueError("transcriptReady must be a boolean")
    if "provenance" in audit and audit["provenance"] not in ("synthetic", "source-audit"):
        raise ValueError("Unsupported audit provenance")
    segments = audit.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Audit requires at least one segment")
    seen = set()
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError("Each segment must be an object")
        if set(segment) != {"id", "kind", "confidence", "startSeconds", "endSeconds", "hasSpeech"}:
            raise ValueError("Segment must contain exactly the documented audit fields")
        segment_id = segment.get("id")
        if not isinstance(segment_id, str) or not segment_id.strip() or segment_id in seen:
            raise ValueError("Segment IDs must be nonempty and unique")
        seen.add(segment_id)
        if segment.get("kind") not in (*KINDS, "unknown"):
            raise ValueError(f"Unsupported segment kind: {segment.get('kind')!r}")
        confidence = segment.get("confidence")
        if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
            raise ValueError("Segment confidence must be between 0 and 1")
        start, end = segment.get("startSeconds"), segment.get("endSeconds")
        if type(start) not in (int, float) or type(end) not in (int, float) or not isfinite(start) or not isfinite(end) or not 0 <= start < end:
            raise ValueError("Segment must have a positive, nonnegative source interval")
        if type(segment.get("hasSpeech")) is not bool:
            raise ValueError("Segment hasSpeech must be audited explicitly")
    return segments


def evaluate(audit, profile=None, project=None):
    """Return questions + confirmed constraints; never generate execution jobs."""
    profile = {"schemaVersion": VERSION} if profile is None else profile
    project = {"schemaVersion": VERSION} if project is None else project
    _document(audit, "audit", {"schemaVersion", "projectId", "provenance", "transcriptReady", "segments"})
    _document(profile, "profile", {"schemaVersion", "preferences", "notes"})
    _document(project, "project answers", {"schemaVersion", "answers", "classifications"})
    segments = _segments(audit)
    preferences = _mapping(profile, "preferences")
    answers = _mapping(project, "answers")
    classifications = _mapping(project, "classifications")
    if any(not isinstance(note, str) for note in _mapping(profile, "notes").values()):
        raise ValueError("Profile notes must be strings")
    _preferences(preferences, "preference")
    _preferences(answers, "answer")
    known_ids = {segment["id"] for segment in segments}
    for segment_id, kind in classifications.items():
        if segment_id not in known_ids or kind not in KINDS:
            raise ValueError(f"Invalid classification override for {segment_id}")

    result = {
        "schemaVersion": VERSION,
        "projectId": audit["projectId"],
        "status": "needs_answers",
        "questions": [],
        "blockers": [],
        "decisions": {},
        "resolvedSegments": [],
        "intakeIntent": None,
        "executionPlan": None,
        "productionAdaptersReady": False,
    }
    for segment in segments:
        kind = classifications.get(segment["id"], segment["kind"])
        overridden = segment["id"] in classifications
        if not overridden and (kind == "unknown" or segment["confidence"] < CONFIDENCE_THRESHOLD):
            result["questions"].append({
                "id": f"classify.{segment['id']}",
                "required": True,
                "prompt": f"片段 {segment['id']} 的分类尚不可靠，请确认它是口播、教程录屏还是其他画面。",
                "choices": list(KINDS),
                "answerTarget": f"classifications.{segment['id']}",
                "segmentIds": [segment["id"]],
            })
        else:
            result["resolvedSegments"].append({
                **segment, "kind": kind,
                "classificationSource": "project" if overridden else "audit",
            })
    # Client preferences cannot turn an uncertain content classification into certainty.
    if result["questions"]:
        result["blockers"].append("classification_required")
        return result

    resolved = result["resolvedSegments"]
    kinds = {segment["kind"] for segment in resolved}
    has_speech = any(segment["hasSpeech"] for segment in resolved)
    mixed = {"talking_head", "screen_recording"}.issubset(kinds)
    keys = []
    if "talking_head" in kinds:
        keys.append("broll.talking_head")
    if mixed:
        keys.append("broll.screen_recording")
    if "screen_recording" in kinds:
        keys.append("motion.screen_recording")
    if has_speech:
        keys.append("speech.edit_mode")
    keys.append("sound.mode")
    for key in keys:
        if key in answers or key in preferences:
            source = "project" if key in answers else "profile"
            result["decisions"][key] = {
                "value": answers[key] if source == "project" else preferences[key],
                "source": source,
                "confirmed": True,
            }
        else:
            result["questions"].append({
                "id": key, "required": True, "prompt": PROMPTS[key],
                "choices": list(CHOICES[key]), "suggested": SUGGESTIONS[key],
                "answerTarget": f"answers.{key}",
                "segmentIds": [segment["id"] for segment in resolved if (
                    (key.startswith("broll.") and segment["kind"] == key.split(".")[1])
                    or (key == "motion.screen_recording" and segment["kind"] == "screen_recording")
                    or (key == "speech.edit_mode" and segment["hasSpeech"])
                    or key == "sound.mode"
                )],
            })
    if result["questions"]:
        result["blockers"].append("client_answers_required")
        return result

    values = {key: decision["value"] for key, decision in result["decisions"].items()}
    if values.get("speech.edit_mode") == "review_trim" and not audit["transcriptReady"]:
        result["status"] = "needs_transcript"
        result["blockers"].append("aligned_transcript_required")
        return result

    policies = []
    for segment in resolved:
        key = f"broll.{segment['kind']}"
        broll = values.get(key, False) if segment["kind"] in ("talking_head", "screen_recording") else False
        policies.append({
            "segmentId": segment["id"], "kind": segment["kind"],
            "allowBroll": broll, "allowBrollSearchOrDownload": broll,
            "brollDecisionSource": result["decisions"].get(key, {}).get("source", "prototype_policy"),
            "motionAnnotations": bool(values.get("motion.screen_recording", False)) if segment["kind"] == "screen_recording" else False,
        })
    result["status"] = "ready_for_planning"
    result["intakeIntent"] = {
        "segmentPolicies": policies,
        "speechEditMode": values.get("speech.edit_mode", "not_applicable"),
        "soundMode": values["sound.mode"],
        "nextStep": "compile_edit_plan_after_adapter_validation",
        "note": "偏好约束已齐全；这不是带时间点的 edit-plan，也没有执行生产任务。",
    }
    return result
