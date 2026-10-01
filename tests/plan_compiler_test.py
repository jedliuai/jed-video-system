"""Time mapping tests across cuts, anchors, captions, and target frame rates."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/jed-video-system/src"))
from jed_plan import compile_plan, seconds_to_frame


class PlanCompilerTests(unittest.TestCase):
    def setUp(self):
        self.transcript = {"source": {"sha256": "a" * 64, "durationSeconds": 10},
                           "quality": {"manualReviewComplete": False}, "words": [
            {"id": "first", "text": "一", "sourceTime": {"start": 1.5, "end": 1.7},
             "timingQuality": "forced_aligned", "approximateBoundary": False},
            {"id": "second", "text": "二", "sourceTime": {"start": 2.5, "end": 2.7},
             "timingQuality": "forced_aligned", "approximateBoundary": False},
            {"id": "third", "text": "三", "sourceTime": {"start": 5.5, "end": 5.7},
             "timingQuality": "interpolated", "approximateBoundary": True}]}
        self.plan = {"schemaVersion": "0.1.0", "projectId": "example", "fps": 30,
                     "source": {"publicFile": "source.mp4", "durationSeconds": 10,
                                "transcriptSourceSha256": "a" * 64},
                     "clips": [{"id": "a", "sourceStartSeconds": 1, "sourceEndSeconds": 3, "speed": 1},
                               {"id": "b", "sourceStartSeconds": 5, "sourceEndSeconds": 7, "speed": 1}],
                     "overlays": [{"id": "event", "clipId": "b", "sourceStartSeconds": 5,
                                   "sourceEndSeconds": 6, "headlineAnchorWordId": "third",
                                   "content": {"headline": ["三"], "points": [{"title": "三", "anchorWordId": "third"}]}}],
                     "captions": [{"sourceStartSeconds": 2.5, "sourceEndSeconds": 5.5, "text": "跨剪辑字幕"}]}

    def test_two_cuts_map_anchor_once_and_split_caption(self):
        result = compile_plan(self.plan, self.transcript)
        self.assertEqual(result["durationInFrames"], 120)
        self.assertEqual(result["clips"][1], {"id": "b", "sourceStartFrame": 150, "outputStartFrame": 60, "durationInFrames": 60})
        self.assertEqual(result["overlays"][0]["outputStartFrame"], 60)
        self.assertEqual(result["overlays"][0]["headlineCueFrame"], 15)
        self.assertEqual(result["overlays"][0]["content"]["points"][0]["cueFrame"], 15)
        self.assertEqual(result["captions"], [{"startFrame": 45, "endFrame": 60, "text": "跨剪辑字幕"},
                                               {"startFrame": 60, "endFrame": 75, "text": "跨剪辑字幕"}])
        self.assertTrue(result["timingReview"][0]["approximateBoundary"])
        self.assertEqual(result["timingReview"][0]["outputCueFrame"], 75)

    def test_wrong_source_hash_is_rejected(self):
        self.plan["source"]["transcriptSourceSha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "SHA256"):
            compile_plan(self.plan, self.transcript)

    def test_unknown_anchor_is_rejected(self):
        self.plan["overlays"][0]["headlineAnchorWordId"] = "absent"
        with self.assertRaisesRegex(ValueError, "unknown anchor"):
            compile_plan(self.plan, self.transcript)

    def test_cut_inside_word_is_rejected(self):
        self.plan["clips"][0]["sourceStartSeconds"] = 1.6
        with self.assertRaisesRegex(ValueError, "inside word"):
            compile_plan(self.plan, self.transcript)

    def test_overlay_end_inside_word_is_allowed(self):
        self.plan["overlays"][0]["sourceEndSeconds"] = 5.6
        self.plan["overlays"][0]["headlineAnchorWordId"] = "first"
        self.plan["overlays"][0]["clipId"] = "a"
        self.plan["overlays"][0]["sourceStartSeconds"] = 1
        self.plan["overlays"][0]["sourceEndSeconds"] = 2.6
        self.plan["overlays"][0]["content"]["points"] = []
        result = compile_plan(self.plan, self.transcript)
        self.assertEqual(result["overlays"][0]["durationInFrames"], 48)

    def test_speed_change_is_rejected(self):
        self.plan["clips"][0]["speed"] = 2
        with self.assertRaisesRegex(ValueError, "speed=1"):
            compile_plan(self.plan, self.transcript)

    def test_overlapping_source_clips_are_rejected(self):
        self.plan["clips"][1].update(sourceStartSeconds=2, sourceEndSeconds=4)
        with self.assertRaisesRegex(ValueError, "overlapping source"):
            compile_plan(self.plan, self.transcript)

    def test_event_outside_clip_is_rejected(self):
        self.plan["overlays"][0]["sourceEndSeconds"] = 8
        with self.assertRaisesRegex(ValueError, "fully contained"):
            compile_plan(self.plan, self.transcript)

    def test_anchor_outside_event_is_rejected(self):
        self.plan["overlays"][0]["headlineAnchorWordId"] = "first"
        with self.assertRaisesRegex(ValueError, "inside the event"):
            compile_plan(self.plan, self.transcript)

    def test_nonfinite_and_unsupported_frame_rates_are_rejected(self):
        for value in (24, 30.0, True, float("nan")):
            plan = deepcopy(self.plan); plan["fps"] = value
            with self.assertRaises(ValueError):
                compile_plan(plan, self.transcript)
        for value in (float("nan"), float("inf"), True):
            plan = deepcopy(self.plan); plan["clips"][0]["sourceEndSeconds"] = value
            with self.assertRaises(ValueError):
                compile_plan(plan, self.transcript)

    def test_half_up_rounding_and_endpoint_subtraction(self):
        self.assertEqual(seconds_to_frame(.15, 30), 5)
        self.assertEqual(seconds_to_frame(.075, 60), 5)
        plan = deepcopy(self.plan)
        plan["clips"] = [{"id": "a", "sourceStartSeconds": .15, "sourceEndSeconds": 1.05, "speed": 1}]
        plan["overlays"], plan["captions"] = [], []
        result = compile_plan(plan, self.transcript)
        self.assertEqual(result["clips"][0]["sourceStartFrame"], 5)
        self.assertEqual(result["durationInFrames"], 27)  # round(31.5)-round(4.5)=32-5

    def test_30_and_60_share_time_domain_with_half_frame_error(self):
        for fps in (30, 60):
            plan = deepcopy(self.plan); plan["fps"] = fps
            result = compile_plan(plan, self.transcript)
            self.assertEqual(result["durationInFrames"], 4 * fps)
            for review in result["timingReview"]:
                self.assertAlmostEqual(review["outputCueFrame"] / fps, 2.5)
            for seconds in (.001, .0167, .15, 1.243, 6.805, 11.947):
                self.assertLessEqual(abs(seconds_to_frame(seconds, fps) / fps - seconds), .5 / fps + 1e-12)

    def test_plan_and_transcript_are_not_mutated(self):
        plan, transcript = deepcopy(self.plan), deepcopy(self.transcript)
        compile_plan(plan, transcript)
        self.assertEqual(plan, self.plan)
        self.assertEqual(transcript, self.transcript)


if __name__ == "__main__":
    unittest.main()
