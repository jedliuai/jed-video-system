"""Behavior checks for immutable inputs, boundary quality, and failed execution."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/jed-video-system/src"))
from jed_video_use.transcription import cache_key, normalize, run_transcription, sha256_file


class TranscriptAdapterTests(unittest.TestCase):
    def setUp(self):
        self.source = {"path": "source.mp4", "sha256": "a" * 64, "durationSeconds": 4.0}
        self.raw = {"language_code": "zh", "text": "甲乙丙", "words": [
            {"type": "word", "text": "甲", "start": .2, "end": .4, "confidence": .9},
            {"type": "word", "text": "乙", "start": .4, "end": .6},
            {"type": "word", "text": "丙", "start": .6, "end": .8}],
            "source_segments": [{"text": "甲乙丙", "start": .1, "end": 1.0, "words": [
                {"word": "甲", "start": .2, "end": .4, "score": .9},
                {"word": "乙"}, {"word": "丙", "start": .59, "end": .8, "score": .8}]}]}

    def test_same_filename_different_content_has_different_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / "a/clip.mp4", Path(directory) / "b/clip.mp4"
            a.parent.mkdir(); b.parent.mkdir()
            a.write_bytes(b"first source"); b.write_bytes(b"second source")
            self.assertNotEqual(cache_key(sha256_file(a), {}, {}, {}), cache_key(sha256_file(b), {}, {}, {}))

    def test_configuration_and_helper_changes_invalidate_cache(self):
        key = cache_key("a", {"language": "zh"}, {"runner": "old"}, {"whisperx": "3"})
        for configuration, helpers, versions in [({"language": "en"}, {"runner": "old"}, {"whisperx": "3"}),
                                                  ({"language": "zh"}, {"runner": "new"}, {"whisperx": "3"}),
                                                  ({"language": "zh"}, {"runner": "old"}, {"whisperx": "4"})]:
            self.assertNotEqual(key, cache_key("a", configuration, helpers, versions))

    def test_interpolation_and_adjustment_remain_explicit(self):
        result = normalize(self.raw, self.source, {})
        self.assertEqual([word["timingQuality"] for word in result["words"]],
                         ["forced_aligned", "interpolated", "helper_adjusted"])
        self.assertEqual(result["quality"]["approximateWordCount"], 2)
        self.assertFalse(result["quality"]["manualReviewComplete"])

    def test_illegal_word_ranges_are_rejected(self):
        for start, end in [(-.1, .4), (.4, .2), (.2, 5), (.2, .2), (float("nan"), .4), (True, .4)]:
            with self.subTest(start=start, end=end):
                raw = deepcopy(self.raw)
                raw["words"][0].update(start=start, end=end)
                with self.assertRaises(ValueError):
                    normalize(raw, self.source, {})

    def test_illegal_segment_range_is_rejected(self):
        raw = deepcopy(self.raw)
        raw["source_segments"][0]["end"] = 5
        with self.assertRaisesRegex(ValueError, "segment 0"):
            normalize(raw, self.source, {})

    def test_overlapping_words_are_rejected(self):
        raw = deepcopy(self.raw)
        raw["words"][1]["start"] = .3
        with self.assertRaisesRegex(ValueError, "overlapping"):
            normalize(raw, self.source, {})

    def test_unknown_mapping_is_conservatively_approximate(self):
        raw = deepcopy(self.raw)
        raw["words"][0]["text"] = "different"
        result = normalize(raw, self.source, {})
        self.assertEqual(result["words"][0]["timingQuality"], "unknown")
        self.assertTrue(result["words"][0]["approximateBoundary"])

    def test_helper_failure_is_saved_as_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "clip.mp4"; source.write_bytes(b"source")
            helpers = root / "skill/helpers"; helpers.mkdir(parents=True)
            (helpers / "transcribe.py").write_text("helper")
            (helpers / "whisperx_runner.py").write_text("runner")
            with patch("jed_video_use.transcription.subprocess.check_output", side_effect=['{"whisperx":"3"}', "4"]), \
                 patch("jed_video_use.transcription.subprocess.run", return_value=subprocess.CompletedProcess([], 7)):
                with self.assertRaisesRegex(RuntimeError, "exit code 7"):
                    run_transcription(source, root / "output", root / "skill", Path(sys.executable), root / "models")
            manifests = list((root / "output").glob("*/manifest.json"))
            self.assertEqual(len(manifests), 1)
            manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "failed")
            self.assertFalse((manifests[0].parent / "transcript.json").exists())

    def test_cli_failure_reports_nonzero_status(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / "plugins/jed-video-system/scripts/transcribe.py"),
                                     str(Path(directory) / "does-not-exist.mp4")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
