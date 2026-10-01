"""Bind human decisions to specific artifacts and operations, not vague stages.

All mutators return a copy. Operator decisions are supplied input, never a claim
that the software authenticated a human or assessed an artifact's aesthetics.
"""

from copy import deepcopy
import hashlib
import json
import re


SCOPES = {
    "technical_preparation", "speech_structure", "visual_sample", "audio_sample",
    "rough_cut", "final_delivery",
}
MECHANICAL_OPERATIONS = {
    "probe_media", "transcribe", "align_transcript", "compile_plan",
    "render_preview", "export_local_preview", "copy_verified_media",
    "normalize_audio_clock",
}
KINDS = {"plan", "image", "video", "audio", "timeline", "report"}
VISUAL_KINDS = {"image", "video"}
VERSION_FIELDS = (
    "candidateId", "scope", "scopeId", "revision", "contentRevision",
    "artifactDigest", "artifactKind", "patternId", "operationVersion",
    "operations", "coverage", "dependsOn", "approvedSampleId",
    "dependencyFingerprints",
)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _digest(value, name="artifactDigest"):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _candidate(value):
    if not isinstance(value, dict):
        raise ValueError("candidate must be an object")
    result = deepcopy(value)
    for name in ("candidateId", "scopeId", "revision", "contentRevision", "patternId", "operationVersion", "locator"):
        _text(result.get(name), name)
    if result.get("scope") not in SCOPES:
        raise ValueError("unknown review scope")
    _digest(result.get("artifactDigest"))
    if result.get("artifactKind") not in KINDS:
        raise ValueError("unknown artifactKind")
    if result.get("coverage") not in {"single", "sample", "batch"}:
        raise ValueError("coverage must be single, sample, or batch")
    operations = result.get("operations")
    if not isinstance(operations, list) or not operations or any(not isinstance(x, str) or not x.strip() for x in operations):
        raise ValueError("operations must be a nonempty string array")
    if len(set(operations)) != len(operations):
        raise ValueError("duplicate operations")
    result["operations"] = sorted(operations)
    dependencies = result.setdefault("dependsOn", [])
    if not isinstance(dependencies, list) or any(not isinstance(x, str) or not x.strip() for x in dependencies):
        raise ValueError("dependsOn must be a string array")
    sample = result.get("approvedSampleId")
    if sample is not None:
        _text(sample, "approvedSampleId")
        if result["coverage"] != "batch":
            raise ValueError("only batch candidates may reuse a sample")
        dependencies = dependencies + [sample]
    else:
        result.pop("approvedSampleId", None)
    result["dependsOn"] = sorted(set(dependencies))
    dependency_versions = result.setdefault("dependencyFingerprints", {})
    if not isinstance(dependency_versions, dict):
        raise ValueError("dependencyFingerprints must be an object")
    for dependency, digest in dependency_versions.items():
        if dependency not in result["dependsOn"]:
            raise ValueError("fingerprint references an undeclared dependency")
        _digest(digest, "dependency fingerprint")
    if result["candidateId"] in result["dependsOn"]:
        raise ValueError("candidate cannot depend on itself")
    return result


def _fingerprint(candidate):
    version = {key: candidate.get(key) for key in VERSION_FIELDS}
    encoded = json.dumps(version, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def new_state(project_id):
    return {"schemaVersion": 1, "projectId": _text(project_id, "projectId"), "candidates": {}, "requests": [], "nextRequest": 1}


def validate_state(state):
    if not isinstance(state, dict) or state.get("schemaVersion") != 1:
        raise ValueError("unsupported review-state schemaVersion")
    _text(state.get("projectId"), "projectId")
    if not isinstance(state.get("candidates"), dict) or not isinstance(state.get("requests"), list):
        raise ValueError("state needs candidates and requests")
    if not isinstance(state.get("nextRequest"), int) or isinstance(state["nextRequest"], bool) or state["nextRequest"] < 1:
        raise ValueError("nextRequest must be a positive integer")
    for key, candidate in state["candidates"].items():
        checked = _candidate(candidate)
        if checked["candidateId"] != key or candidate.get("fingerprint") != _fingerprint(checked):
            raise ValueError("candidate id or fingerprint mismatch")
        for dependency in checked["dependsOn"]:
            if dependency not in state["candidates"]:
                raise ValueError(f"unknown dependency: {dependency}")
        if set(checked["dependsOn"]) != set(checked["dependencyFingerprints"]):
            raise ValueError("candidate dependency fingerprint set is incomplete")
    request_ids = set()
    for request in state["requests"]:
        request_id = _text(request.get("requestId"), "requestId")
        if request_id in request_ids:
            raise ValueError("duplicate requestId")
        request_ids.add(request_id)
        if request.get("candidateId") not in state["candidates"]:
            raise ValueError("request references an unknown candidate")
        _digest(request.get("fingerprint"), "request fingerprint")
        if request.get("status") not in {"pending", "approved", "rejected", "revise", "stale"}:
            raise ValueError("invalid request status")
        if not isinstance(request.get("dependencies"), dict):
            raise ValueError("request dependencies must be an object")
        snapshot = _candidate(request.get("candidateSnapshot"))
        if snapshot["candidateId"] != request["candidateId"] or _fingerprint(snapshot) != request["fingerprint"]:
            raise ValueError("review request snapshot fingerprint mismatch")
        if request.get("artifact") != {"digest": snapshot["artifactDigest"], "kind": snapshot["artifactKind"], "locator": snapshot["locator"], "revision": snapshot["revision"]}:
            raise ValueError("review request artifact does not match its snapshot")
        if request.get("operations") != snapshot["operations"] or request.get("operationVersion") != snapshot["operationVersion"]:
            raise ValueError("review request operations do not match its snapshot")
        for key, digest in request["dependencies"].items():
            if key not in state["candidates"]:
                raise ValueError("request dependency is unknown")
            _digest(digest, "dependency fingerprint")
        if request["status"] in {"approved", "rejected", "revise"}:
            decision = request.get("decision", {})
            if decision.get("source") != "operator_input" or decision.get("identityVerified") is not False or decision.get("value") != request["status"]:
                raise ValueError("decision must explicitly identify unverified operator input")
    _check_cycles(state["candidates"])
    return state


def _check_cycles(candidates):
    visiting, visited = set(), set()
    def visit(key):
        if key in visiting:
            raise ValueError("cyclic review dependencies")
        if key in visited:
            return
        visiting.add(key)
        for dependency in candidates[key]["dependsOn"]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)
    for key in candidates:
        visit(key)


def register_candidate(state, candidate):
    validate_state(state)
    result = deepcopy(state)
    candidate = _candidate(candidate)
    key = candidate["candidateId"]
    for dependency in candidate["dependsOn"]:
        if dependency not in result["candidates"]:
            raise ValueError(f"register dependency first: {dependency}")
    candidate["dependencyFingerprints"] = {dependency: result["candidates"][dependency]["fingerprint"] for dependency in candidate["dependsOn"]}
    candidate["fingerprint"] = _fingerprint(candidate)
    previous = result["candidates"].get(key)
    result["candidates"][key] = candidate
    _check_cycles(result["candidates"])
    if previous and previous["fingerprint"] != candidate["fingerprint"]:
        affected = {key}
        while True:
            downstream = {name for name, item in result["candidates"].items() if set(item["dependsOn"]) & affected}
            expanded = affected | downstream
            if expanded == affected:
                break
            affected = expanded
        for request in result["requests"]:
            if request["candidateId"] in affected and request["status"] != "stale":
                request["previousStatus"] = request["status"]
                request["status"] = "stale"
                request["staleReason"] = f"candidate or dependency updated: {key}"
    return result


def _latest(state, key):
    return next((item for item in reversed(state["requests"]) if item["candidateId"] == key), None)


def _is_current(state, request):
    if request["fingerprint"] != state["candidates"][request["candidateId"]]["fingerprint"]:
        return False
    return all(state["candidates"][key]["fingerprint"] == fingerprint for key, fingerprint in request["dependencies"].items())


def _dependencies_current(state, candidate):
    return all(
        state["candidates"][key]["fingerprint"] == fingerprint
        and _dependencies_current(state, state["candidates"][key])
        for key, fingerprint in candidate["dependencyFingerprints"].items()
    )


def _require_reviewable(candidate):
    scope, kind = candidate["scope"], candidate["artifactKind"]
    if scope == "visual_sample" and kind not in VISUAL_KINDS:
        raise ValueError("visual review requires a rendered image or video sample")
    if scope == "audio_sample" and kind not in {"audio", "video"}:
        raise ValueError("audio review requires an audible audio or video sample")
    if scope == "speech_structure" and kind not in {"audio", "video"}:
        raise ValueError("speech structure and pacing review requires an audible before/after sample; a plan alone is not acceptance")
    if scope in {"rough_cut", "final_delivery"} and kind != "video":
        raise ValueError("whole-video review requires an actual video")


def request_review(state, candidate_id, prompt):
    """Present a concrete candidate. This does not approve it or execute anything."""
    validate_state(state)
    _text(prompt, "prompt")
    if candidate_id not in state["candidates"]:
        raise ValueError("unknown candidateId")
    result = deepcopy(state)
    candidate = result["candidates"][candidate_id]
    if not _dependencies_current(result, candidate):
        raise ValueError("candidate has changed dependencies; register its current revision before requesting review")
    _require_reviewable(candidate)
    previous = _latest(result, candidate_id)
    if previous and _is_current(result, previous) and previous["status"] in {"pending", "approved"}:
        return result
    request_id = f"review-{result['nextRequest']}-{candidate['fingerprint'][:12]}"
    result["nextRequest"] += 1
    result["requests"].append({
        "requestId": request_id, "candidateId": candidate_id,
        "fingerprint": candidate["fingerprint"], "status": "pending", "prompt": prompt,
        "candidateSnapshot": deepcopy(candidate),
        "artifact": {"digest": candidate["artifactDigest"], "kind": candidate["artifactKind"], "locator": candidate["locator"], "revision": candidate["revision"]},
        "operations": candidate["operations"], "operationVersion": candidate["operationVersion"],
        "dependencies": {key: result["candidates"][key]["fingerprint"] for key in candidate["dependsOn"]},
    })
    return result


def record_decision(state, request_id, decision, note="", operator_label="operator"):
    """Record explicit input against its request ID; identity remains unverified."""
    validate_state(state)
    if decision not in {"approved", "rejected", "revise"}:
        raise ValueError("decision must be approved, rejected, or revise")
    _text(operator_label, "operator_label")
    if not isinstance(note, str):
        raise ValueError("note must be a string")
    result = deepcopy(state)
    request = next((item for item in result["requests"] if item["requestId"] == request_id), None)
    if request is None:
        raise ValueError("unknown requestId")
    if request["status"] != "pending" or not _is_current(result, request):
        raise ValueError("only a pending, current request can receive a decision")
    request["status"] = decision
    request["decision"] = {"value": decision, "note": note, "operatorLabel": operator_label, "source": "operator_input", "identityVerified": False}
    return result


def evaluate_gate(state, candidate_id, intent=None):
    """A read-only permission result. It never invokes an external editor."""
    validate_state(state)
    if candidate_id not in state["candidates"]:
        raise ValueError("unknown candidateId")
    candidate = state["candidates"][candidate_id]
    result = {"candidateId": candidate_id, "scope": candidate["scope"], "status": "needs_review", "allowed": False, "reason": "No current operator approval exists for this candidate."}
    if not _dependencies_current(state, candidate):
        result.update(status="stale", reason="Candidate dependencies changed; register the regenerated candidate before continuing.")
        return result
    request = _latest(state, candidate_id)
    if request:
        result["approvalRequestId"] = request["requestId"]
        if not _is_current(state, request) or request["status"] == "stale":
            result.update(status="stale", reason="The artifact, operation version, or a dependency changed.")
            return result
        if request["status"] in {"rejected", "revise"}:
            result.update(status="blocked", reason=f"Operator decision: {request['status']}; revise the candidate before continuing.")
            return result
        if request["status"] == "approved":
            result.update(status="approved", allowed=True, reason="A current operator receipt covers this exact artifact and operations.")
            return result
        if request["status"] == "pending":
            result["reason"] = "A review request is pending; showing a sample is not approval."
            return result
    authorization = (intent or {}).get("authorizedMechanicalOperations", [])
    if not isinstance(authorization, list) or any(not isinstance(x, str) for x in authorization):
        raise ValueError("authorizedMechanicalOperations must be a string array")
    if candidate["scope"] == "technical_preparation" and set(candidate["operations"]) <= MECHANICAL_OPERATIONS & set(authorization):
        result.update(status="auto_authorized", allowed=True, reason="Project intent explicitly authorizes these mechanical operations.")
        return result
    if candidate["scope"] in {"visual_sample", "audio_sample"} and candidate["coverage"] == "batch" and candidate.get("approvedSampleId"):
        sample_id = candidate["approvedSampleId"]
        sample = state["candidates"][sample_id]
        receipt = _latest(state, sample_id)
        same_fields = ("scope", "scopeId", "revision", "contentRevision", "patternId", "operationVersion", "operations")
        if sample["coverage"] == "sample" and all(candidate[field] == sample[field] for field in same_fields) and receipt and receipt["status"] == "approved" and _is_current(state, receipt):
            result.update(status="approved_sample_reuse", allowed=True, approvalRequestId=receipt["requestId"], reason="This bounded batch uses the approved sample's scope, revision, pattern, content revision, and operations.")
    return result


def suggest_gates(context):
    """Suggest only actual aesthetic/semantic risks, without requesting approval.

    Empty input creates no mandatory funnel. An absent sample returns preparation,
    not a premature request. Mechanical work and future hypothetical delivery do
    not create review points.
    """
    if not isinstance(context, dict):
        raise ValueError("review context must be an object")
    result = []
    artifacts = context.get("artifacts", {})
    speech, visual, audio = (context.get(key, {}) for key in ("speechChanges", "visualChanges", "audioChanges"))
    conditions = [
        ("speech_structure", any(speech.get(key) is True for key in ("deletesMeaningfulContent", "reordersStatements", "changesClaims", "changesPacing", "ambiguousMeaning")), "Meaningful cuts, uncertain meaning, or altered pacing need an audible before/after sample."),
        ("visual_sample", any(visual.get(key) is True for key in ("newStyle", "newBroll", "changesEstablishedStyle", "affectsPersonRepresentation", "newMotionPattern", "firstRealFootageApplication")), "New visual treatment, motion, or first use on real footage needs a rendered sample."),
        ("audio_sample", any(audio.get(key) is True for key in ("newMusic", "newSfxStyle", "changesMood")), "New sound treatment needs an audible sample."),
        ("rough_cut", any(context.get(key) is True for key in ("majorStructureChanged", "combinedNewElements", "reviewWholeFlow")), "The combined flow needs a short or full rough cut."),
        ("final_delivery", context.get("delivery", {}).get("requested") is True and context.get("delivery", {}).get("reviewRequested") is True, "The current delivery request includes a final human review."),
    ]
    for scope, needed, reason in conditions:
        if not needed:
            continue
        artifact = artifacts.get(scope)
        ready = isinstance(artifact, dict) and isinstance(artifact.get("locator"), str) and bool(artifact["locator"].strip()) and isinstance(artifact.get("revision"), str) and bool(artifact["revision"].strip()) and isinstance(artifact.get("artifactDigest"), str) and re.fullmatch(r"[0-9a-f]{64}", artifact["artifactDigest"]) is not None
        required_kinds = {"speech_structure": {"audio", "video"}, "visual_sample": VISUAL_KINDS, "audio_sample": {"audio", "video"}, "rough_cut": {"video"}, "final_delivery": {"video"}}
        ready = ready and artifact.get("artifactKind") in required_kinds[scope]
        result.append({"scope": scope, "reason": reason, "status": "ready_to_request" if ready else "prepare_sample", "artifact": deepcopy(artifact) if ready else None})
    return result
