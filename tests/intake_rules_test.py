"""Behavioral checks: dependency reachability and client intent preservation."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "jed-video-system"
sys.path.insert(0, str(PLUGIN / "src"))
from jed_intake import evaluate


class IntakeRulesTests(unittest.TestCase):
    def setUp(self):
        self.audit = json.loads((PLUGIN / "examples/audit-mixed.json").read_text(encoding="utf-8"))
        self.answers = json.loads((PLUGIN / "examples/project-answers.json").read_text(encoding="utf-8"))
        self.profile = json.loads((ROOT / "config/user-preferences.example.json").read_text(encoding="utf-8"))

    def test_no_implied_answer_from_suggestion(self):
        result = evaluate(self.audit)
        self.assertEqual(result["status"], "needs_answers")
        self.assertEqual(len(result["questions"]), 5)
        self.assertEqual(result["decisions"], {})
        self.assertIsNone(result["intakeIntent"])
        self.assertIsNone(result["executionPlan"])

    def test_mixed_screen_broll_question_follows_audit(self):
        result = evaluate(self.audit)
        question = next(q for q in result["questions"] if q["id"] == "broll.screen_recording")
        self.assertEqual(question["segmentIds"], ["demo"])

    def test_explicit_screen_preference_reused_without_reasking(self):
        result = evaluate(self.audit, self.profile)
        self.assertNotIn("broll.screen_recording", [q["id"] for q in result["questions"]])
        self.assertEqual(result["decisions"]["broll.screen_recording"], {"value": False, "source": "profile", "confirmed": True})

    def test_disabled_screen_broll_allows_motion_but_no_download(self):
        result = evaluate(self.audit, self.profile, self.answers)
        self.assertEqual(result["status"], "ready_for_planning")
        screen = result["intakeIntent"]["segmentPolicies"][1]
        self.assertFalse(screen["allowBroll"])
        self.assertFalse(screen["allowBrollSearchOrDownload"])
        self.assertTrue(screen["motionAnnotations"])
        self.assertFalse(result["productionAdaptersReady"])
        self.assertIsNone(result["executionPlan"])

    def test_project_overrides_profile(self):
        self.answers["answers"]["broll.screen_recording"] = True
        result = evaluate(self.audit, self.profile, self.answers)
        self.assertTrue(result["intakeIntent"]["segmentPolicies"][1]["allowBroll"])
        self.assertEqual(result["decisions"]["broll.screen_recording"]["source"], "project")

    def test_talking_head_broll_not_forced(self):
        result = evaluate(self.audit, self.profile, self.answers)
        self.assertFalse(result["intakeIntent"]["segmentPolicies"][0]["allowBroll"])

    def test_uncertain_classification_blocks_downstream_questions(self):
        self.audit["segments"][1]["confidence"] = 0.6
        result = evaluate(self.audit, self.profile, self.answers)
        self.assertEqual([q["id"] for q in result["questions"]], ["classify.demo"])
        self.assertIsNone(result["intakeIntent"])

    def test_unknown_with_high_confidence_still_needs_classification(self):
        self.audit["segments"][1]["kind"] = "unknown"
        result = evaluate(self.audit, self.profile, self.answers)
        self.assertEqual([q["id"] for q in result["questions"]], ["classify.demo"])

    def test_classification_override_changes_reachable_questions(self):
        self.audit["segments"][1]["kind"] = "unknown"
        self.answers["classifications"]["demo"] = "other"
        result = evaluate(self.audit, self.profile, self.answers)
        self.assertEqual(result["status"], "ready_for_planning")
        self.assertNotIn("motion.screen_recording", result["decisions"])
        self.assertEqual(result["intakeIntent"]["segmentPolicies"][1]["kind"], "other")

    def test_pure_screen_no_mixed_broll_question(self):
        self.audit["segments"] = self.audit["segments"][1:]
        result = evaluate(self.audit)
        keys = [q["id"] for q in result["questions"]]
        self.assertNotIn("broll.screen_recording", keys)
        self.assertNotIn("broll.talking_head", keys)
        self.assertIn("motion.screen_recording", keys)

    def test_no_speech_has_no_speech_edit_question(self):
        for segment in self.audit["segments"]:
            segment["hasSpeech"] = False
        result = evaluate(self.audit)
        self.assertNotIn("speech.edit_mode", [q["id"] for q in result["questions"]])

    def test_trimming_requires_transcript(self):
        self.audit["transcriptReady"] = False
        self.answers["answers"]["speech.edit_mode"] = "review_trim"
        result = evaluate(self.audit, self.profile, self.answers)
        self.assertEqual(result["status"], "needs_transcript")
        self.assertEqual(result["blockers"], ["aligned_transcript_required"])
        self.assertIsNone(result["intakeIntent"])

    def test_preserve_does_not_require_transcript_for_preferences(self):
        self.audit["transcriptReady"] = False
        result = evaluate(self.audit, self.profile, self.answers)
        self.assertEqual(result["status"], "ready_for_planning")

    def test_reject_invalid_values_versions_and_duplicate_ids(self):
        cases = []
        answers = deepcopy(self.answers)
        answers["answers"]["broll.talking_head"] = 0
        cases.append((self.audit, self.profile, answers))
        audit = deepcopy(self.audit)
        audit["schemaVersion"] = "9.0.0"
        cases.append((audit, self.profile, self.answers))
        audit = deepcopy(self.audit)
        audit["segments"][1]["id"] = "intro"
        cases.append((audit, self.profile, self.answers))
        audit = deepcopy(self.audit)
        audit["segments"][1]["endSeconds"] = float("inf")
        cases.append((audit, self.profile, self.answers))
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                evaluate(*args)

    def test_evaluation_does_not_mutate_input(self):
        originals = deepcopy((self.audit, self.profile, self.answers))
        evaluate(self.audit, self.profile, self.answers)
        self.assertEqual((self.audit, self.profile, self.answers), originals)

    def test_unknown_fields_and_stale_classification_rejected(self):
        answers = deepcopy(self.answers)
        answers["classifications"]["missing-segment"] = "talking_head"
        with self.assertRaises(ValueError):
            evaluate(self.audit, self.profile, answers)
        answers = deepcopy(self.answers)
        answers["execute"] = True
        with self.assertRaises(ValueError):
            evaluate(self.audit, self.profile, answers)

    def test_cli_ready_and_pending_exit_codes(self):
        base = [sys.executable, str(PLUGIN / "scripts/intake.py"), "--audit", str(PLUGIN / "examples/audit-mixed.json")]
        pending = subprocess.run(base, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(pending.returncode, 2)
        self.assertEqual(json.loads(pending.stdout)["status"], "needs_answers")
        ready = subprocess.run(base + ["--profile", str(ROOT / "config/user-preferences.example.json"), "--answers", str(PLUGIN / "examples/project-answers.json")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(ready.returncode, 0, ready.stderr)
        self.assertEqual(json.loads(ready.stdout)["status"], "ready_for_planning")


if __name__ == "__main__":
    unittest.main()
