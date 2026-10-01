"""Meaningful version, scope, refusal, and local-only behavior checks."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/jed-video-system/src"))
from jed_review import evaluate_gate, new_state, record_decision, register_candidate, request_review, suggest_gates, validate_state


def candidate(key="visual-01", **changes):
    value = {
        "candidateId": key, "scope": "visual_sample", "scopeId": "talking-head-intro",
        "revision": "r1", "contentRevision": "script-r1", "artifactDigest": "a" * 64,
        "artifactKind": "video", "locator": "work/renders/sample.mp4", "patternId": "A-direct-overlay",
        "operationVersion": "overlay-engine-1", "operations": ["add_overlay"],
        "coverage": "sample", "dependsOn": [],
    }
    value.update(changes)
    return value


def approve(state, key):
    state = request_review(state, key, "请看这版小样后确认节奏和呈现。")
    return record_decision(state, state["requests"][-1]["requestId"], "approved", "沿用这版。", "客户输入")


class ReviewGatesTests(unittest.TestCase):
    def setUp(self):
        self.state = register_candidate(new_state("demo"), candidate())

    def test_request_does_not_approve(self):
        state = request_review(self.state, "visual-01", "请确认这段样片。")
        result = evaluate_gate(state, "visual-01")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(state["requests"][0]["status"], "pending")
        self.assertEqual(self.state["requests"], [])

    def test_current_explicit_receipt_allows(self):
        state = approve(self.state, "visual-01")
        self.assertTrue(evaluate_gate(state, "visual-01")["allowed"])
        self.assertFalse(state["requests"][0]["decision"]["identityVerified"])

    def test_rejected_and_revise_stop_execution(self):
        for decision in ("rejected", "revise"):
            with self.subTest(decision=decision):
                state = request_review(self.state, "visual-01", "请确认。")
                state = record_decision(state, state["requests"][-1]["requestId"], decision)
                self.assertEqual(evaluate_gate(state, "visual-01")["status"], "blocked")

    def test_pending_request_is_idempotent(self):
        state = request_review(self.state, "visual-01", "请确认。")
        self.assertEqual(state, request_review(state, "visual-01", "不用重复询问。"))

    def test_approved_request_is_not_reasked(self):
        state = approve(self.state, "visual-01")
        self.assertEqual(state, request_review(state, "visual-01", "不用重复询问。"))

    def test_every_material_version_change_invalidates(self):
        changes = {
            "revision": "r2", "contentRevision": "script-r2", "artifactDigest": "b" * 64,
            "patternId": "new-style", "operationVersion": "engine-2", "scopeId": "tutorial",
            "operations": ["add_overlay", "add_broll"], "artifactKind": "image",
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                state = approve(self.state, "visual-01")
                state = register_candidate(state, candidate(**{field: value}))
                self.assertFalse(evaluate_gate(state, "visual-01")["allowed"])
                self.assertEqual(state["requests"][0]["status"], "stale")

    def test_locator_only_move_keeps_identical_artifact_receipt(self):
        state = approve(self.state, "visual-01")
        state = register_candidate(state, candidate(locator="another/same-content.mp4"))
        self.assertTrue(evaluate_gate(state, "visual-01")["allowed"])

    def test_stale_request_cannot_receive_late_approval(self):
        state = request_review(self.state, "visual-01", "请确认。")
        request_id = state["requests"][-1]["requestId"]
        state = register_candidate(state, candidate(artifactDigest="b" * 64))
        with self.assertRaisesRegex(ValueError, "pending, current"):
            record_decision(state, request_id, "approved")

    def test_new_request_after_revision_can_be_approved(self):
        state = approve(self.state, "visual-01")
        state = register_candidate(state, candidate(revision="r2", artifactDigest="b" * 64))
        state = approve(state, "visual-01")
        self.assertTrue(evaluate_gate(state, "visual-01")["allowed"])
        self.assertEqual(len(state["requests"]), 2)

    def test_unrelated_audio_approval_survives_visual_change(self):
        state = register_candidate(self.state, candidate("audio-01", scope="audio_sample", artifactKind="audio", operations=["add_sfx"]))
        state = approve(approve(state, "visual-01"), "audio-01")
        state = register_candidate(state, candidate(revision="r2"))
        self.assertTrue(evaluate_gate(state, "audio-01")["allowed"])
        self.assertFalse(evaluate_gate(state, "visual-01")["allowed"])

    def test_dependency_change_invalidates_transitively(self):
        state = register_candidate(self.state, candidate("rough-01", scope="rough_cut", dependsOn=["visual-01"]))
        state = register_candidate(state, candidate("final-01", scope="final_delivery", dependsOn=["rough-01"]))
        for key in ("visual-01", "rough-01", "final-01"):
            state = approve(state, key)
        state = register_candidate(state, candidate(contentRevision="script-r2"))
        for key in ("visual-01", "rough-01", "final-01"):
            self.assertFalse(evaluate_gate(state, key)["allowed"])

    def test_same_batch_can_reuse_approved_sample(self):
        state = approve(self.state, "visual-01")
        batch = candidate("batch-01", coverage="batch", approvedSampleId="visual-01", artifactDigest="b" * 64)
        state = register_candidate(state, batch)
        result = evaluate_gate(state, "batch-01")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["status"], "approved_sample_reuse")
        self.assertEqual(len(state["requests"]), 1)

    def test_batch_reuse_does_not_cross_style_content_scope_or_operations(self):
        changes = {"revision": "r2", "contentRevision": "script-r2", "scopeId": "tutorial", "scope": "audio_sample", "patternId": "new-style", "operationVersion": "2", "operations": ["add_broll"]}
        for field, value in changes.items():
            with self.subTest(field=field):
                state = approve(self.state, "visual-01")
                batch = candidate("batch-01", coverage="batch", approvedSampleId="visual-01", **{field: value})
                state = register_candidate(state, batch)
                self.assertFalse(evaluate_gate(state, "batch-01")["allowed"])

    def test_unapproved_sample_cannot_authorize_batch(self):
        state = register_candidate(self.state, candidate("batch-01", coverage="batch", approvedSampleId="visual-01"))
        self.assertFalse(evaluate_gate(state, "batch-01")["allowed"])

    def test_sample_update_stops_existing_batch_reuse(self):
        state = register_candidate(approve(self.state, "visual-01"), candidate("batch-01", coverage="batch", approvedSampleId="visual-01"))
        state = register_candidate(state, candidate(artifactDigest="c" * 64))
        self.assertFalse(evaluate_gate(state, "batch-01")["allowed"])

    def test_new_sample_approval_does_not_resurrect_old_batch(self):
        state = register_candidate(approve(self.state, "visual-01"), candidate("batch-01", coverage="batch", approvedSampleId="visual-01"))
        state = register_candidate(state, candidate(artifactDigest="c" * 64))
        state = approve(state, "visual-01")
        self.assertFalse(evaluate_gate(state, "batch-01")["allowed"])
        state = register_candidate(state, candidate("batch-01", coverage="batch", approvedSampleId="visual-01", artifactDigest="b" * 64))
        self.assertTrue(evaluate_gate(state, "batch-01")["allowed"])

    def test_pending_batch_is_not_silently_passed_by_sample(self):
        state = register_candidate(approve(self.state, "visual-01"), candidate("batch-01", coverage="batch", approvedSampleId="visual-01"))
        state = request_review(state, "batch-01", "这次批量仍请看一下。")
        self.assertFalse(evaluate_gate(state, "batch-01")["allowed"])

    def test_explicit_mechanical_authorization_needs_no_repeat_question(self):
        state = register_candidate(self.state, candidate("technical-01", scope="technical_preparation", artifactKind="report", operations=["transcribe", "compile_plan"]))
        result = evaluate_gate(state, "technical-01", {"authorizedMechanicalOperations": ["transcribe", "compile_plan"]})
        self.assertTrue(result["allowed"])
        self.assertEqual(result["status"], "auto_authorized")

    def test_labeling_deletion_mechanical_does_not_bypass_gate(self):
        state = register_candidate(self.state, candidate("technical-01", scope="technical_preparation", operations=["delete_speech"]))
        self.assertFalse(evaluate_gate(state, "technical-01", {"authorizedMechanicalOperations": ["delete_speech"]})["allowed"])

    def test_partial_mechanical_authorization_does_not_allow_all(self):
        state = register_candidate(self.state, candidate("technical-01", scope="technical_preparation", operations=["transcribe", "compile_plan"]))
        self.assertFalse(evaluate_gate(state, "technical-01", {"authorizedMechanicalOperations": ["transcribe"]})["allowed"])

    def test_visual_audio_and_whole_video_need_actual_media_kind(self):
        for scope in ("speech_structure", "visual_sample", "audio_sample", "rough_cut", "final_delivery"):
            with self.subTest(scope=scope):
                state = register_candidate(new_state("demo"), candidate(scope=scope, artifactKind="plan"))
                with self.assertRaises(ValueError):
                    request_review(state, "visual-01", "还未渲染，不该提前问。")

    def test_empty_context_does_not_force_review_funnel(self):
        self.assertEqual(suggest_gates({}), [])
        self.assertEqual(suggest_gates({"operations": ["transcribe", "render_preview"]}), [])

    def test_new_visual_requires_prepare_before_human_request(self):
        context = {"visualChanges": {"newStyle": True}}
        self.assertEqual(suggest_gates(context)[0]["status"], "prepare_sample")
        context["artifacts"] = {"visual_sample": {"locator": "sample.mp4", "artifactDigest": "a" * 64, "revision": "r1", "artifactKind": "video"}}
        self.assertEqual(suggest_gates(context)[0]["status"], "ready_to_request")
        context["artifacts"]["visual_sample"]["artifactKind"] = "plan"
        self.assertEqual(suggest_gates(context)[0]["status"], "prepare_sample")

    def test_confirmations_follow_actual_changes_and_requested_delivery(self):
        context = {"speechChanges": {"deletesMeaningfulContent": True}, "audioChanges": {"changesMood": True}, "delivery": {"reviewRequested": True}}
        self.assertEqual([x["scope"] for x in suggest_gates(context)], ["speech_structure", "audio_sample"])
        context["delivery"]["requested"] = True
        self.assertEqual(suggest_gates(context)[-1]["scope"], "final_delivery")

    def test_cycles_and_unknown_dependencies_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "dependency first"):
            register_candidate(self.state, candidate("other", dependsOn=["unknown"]))
        state = register_candidate(self.state, candidate("other", dependsOn=["visual-01"]))
        with self.assertRaisesRegex(ValueError, "cyclic"):
            register_candidate(state, candidate(dependsOn=["other"]))

    def test_persisted_roundtrip_and_tampering_check(self):
        state = approve(self.state, "visual-01")
        restored = json.loads(json.dumps(state))
        self.assertTrue(evaluate_gate(restored, "visual-01")["allowed"])
        restored["candidates"]["visual-01"]["operations"] = ["delete_speech"]
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            validate_state(restored)

    def test_cannot_overwrite_a_decision_or_invent_request(self):
        state = approve(self.state, "visual-01")
        with self.assertRaises(ValueError):
            record_decision(state, state["requests"][0]["requestId"], "rejected")
        with self.assertRaises(ValueError):
            record_decision(state, "unknown", "approved")

    def test_cli_roundtrip_local_state_and_evaluate_exit_code(self):
        cli = ROOT / "plugins/jed-video-system/scripts/review.py"
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state.json"
            spec = Path(temporary) / "candidate.json"
            artifact = Path(temporary) / "sample.mp4"
            artifact.write_bytes(b"rendered artifact bytes; media self-check belongs to the host")
            value = candidate(locator=str(artifact), artifactDigest=hashlib.sha256(artifact.read_bytes()).hexdigest())
            spec.write_text(json.dumps(value), encoding="utf-8")
            def run(*args):
                return subprocess.run([sys.executable, str(cli), *args], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run("init", "--state", str(state), "--project-id", "demo").returncode, 0)
            self.assertEqual(run("init", "--state", str(state), "--project-id", "demo").returncode, 1)
            self.assertEqual(run("register", "--state", str(state), "--candidate", str(spec)).returncode, 0)
            self.assertEqual(run("request", "--state", str(state), "--candidate-id", "visual-01", "--prompt", "请确认小样").returncode, 0)
            request_id = json.loads(state.read_text(encoding="utf-8"))["requests"][-1]["requestId"]
            self.assertEqual(run("evaluate", "--state", str(state), "--candidate-id", "visual-01").returncode, 2)
            self.assertEqual(run("decide", "--state", str(state), "--request-id", request_id, "--decision", "approved").returncode, 0)
            self.assertEqual(run("evaluate", "--state", str(state), "--candidate-id", "visual-01").returncode, 0)

    def test_same_style_new_motion_real_footage_or_pacing_still_need_review(self):
        for context, scope in [
            ({"visualChanges": {"newMotionPattern": True}}, "visual_sample"),
            ({"visualChanges": {"firstRealFootageApplication": True}}, "visual_sample"),
            ({"speechChanges": {"changesPacing": True}}, "speech_structure"),
            ({"speechChanges": {"ambiguousMeaning": True}}, "speech_structure"),
        ]:
            with self.subTest(context=context):
                self.assertEqual(suggest_gates(context)[0]["scope"], scope)

    def test_batch_visual_permission_does_not_approve_semantic_or_final_actions(self):
        for scope in ("speech_structure", "rough_cut", "final_delivery"):
            with self.subTest(scope=scope):
                state = register_candidate(new_state("demo"), candidate(scope=scope))
                state = register_candidate(approve(state, "visual-01"), candidate("batch-01", scope=scope, coverage="batch", approvedSampleId="visual-01"))
                self.assertFalse(evaluate_gate(state, "batch-01")["allowed"])

    def test_request_snapshot_cannot_silently_point_at_another_artifact(self):
        state = request_review(self.state, "visual-01", "请确认。")
        state["requests"][0]["artifact"]["digest"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "artifact"):
            validate_state(state)

    def test_cli_rejects_missing_changed_and_url_artifacts_without_pending_request(self):
        cli = ROOT / "plugins/jed-video-system/scripts/review.py"
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state.json"
            spec = Path(temporary) / "candidate.json"
            state.write_text(json.dumps(new_state("demo")), encoding="utf-8")
            def run(*args):
                return subprocess.run([sys.executable, str(cli), *args], capture_output=True, text=True, encoding="utf-8")
            for locator in (str(Path(temporary) / "missing.mp4"), "https://example.com/sample.mp4"):
                spec.write_text(json.dumps(candidate(locator=locator)), encoding="utf-8")
                self.assertEqual(run("register", "--state", str(state), "--candidate", str(spec)).returncode, 1)
                self.assertEqual(json.loads(state.read_text(encoding="utf-8"))["candidates"], {})
            artifact = Path(temporary) / "sample.mp4"
            artifact.write_bytes(b"original")
            spec.write_text(json.dumps(candidate(locator=str(artifact), artifactDigest=hashlib.sha256(b"original").hexdigest())), encoding="utf-8")
            self.assertEqual(run("register", "--state", str(state), "--candidate", str(spec)).returncode, 0)
            artifact.write_bytes(b"changed")
            self.assertEqual(run("request", "--state", str(state), "--candidate-id", "visual-01", "--prompt", "看小样").returncode, 1)
            self.assertEqual(json.loads(state.read_text(encoding="utf-8"))["requests"], [])

    def test_cli_rechecks_transitive_dependency_media_before_allowing_or_asking(self):
        cli = ROOT / "plugins/jed-video-system/scripts/review.py"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dependency = root / "sample.mp4"
            rough = root / "rough.mp4"
            final = root / "final.mp4"
            for artifact in (dependency, rough, final):
                artifact.write_bytes(artifact.name.encode("utf-8"))
            state = register_candidate(new_state("demo"), candidate(locator=str(dependency), artifactDigest=hashlib.sha256(dependency.read_bytes()).hexdigest()))
            state = register_candidate(state, candidate("rough-01", scope="rough_cut", dependsOn=["visual-01"], locator=str(rough), artifactDigest=hashlib.sha256(rough.read_bytes()).hexdigest()))
            state = register_candidate(state, candidate("final-01", scope="final_delivery", dependsOn=["rough-01"], locator=str(final), artifactDigest=hashlib.sha256(final.read_bytes()).hexdigest()))
            state = approve(state, "final-01")
            state_file = root / "state.json"
            state_file.write_text(json.dumps(state), encoding="utf-8")
            dependency.write_bytes(b"changed without registration")
            def run(*args):
                return subprocess.run([sys.executable, str(cli), *args], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run("evaluate", "--state", str(state_file), "--candidate-id", "final-01").returncode, 1)
            self.assertEqual(run("request", "--state", str(state_file), "--candidate-id", "final-01", "--prompt", "最终确认").returncode, 1)
            self.assertEqual(json.loads(state_file.read_text(encoding="utf-8")), state)

    def test_speech_pacing_cannot_be_accepted_with_json_plan(self):
        context = {"speechChanges": {"changesPacing": True}, "artifacts": {"speech_structure": {"locator": "plan.json", "artifactDigest": "a" * 64, "revision": "r1", "artifactKind": "plan"}}}
        self.assertEqual(suggest_gates(context)[0]["status"], "prepare_sample")
        context["artifacts"]["speech_structure"]["artifactKind"] = "audio"
        self.assertEqual(suggest_gates(context)[0]["status"], "ready_to_request")


if __name__ == "__main__":
    unittest.main()
