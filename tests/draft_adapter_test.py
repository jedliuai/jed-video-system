"""Boundary and rejection checks, without installing or mutating editor state."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("jed_draft_worker", Path(__file__).parents[1] / "workers/draft-adapter/worker.py")
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class DraftBoundaries(unittest.TestCase):
    def test_adjacent_spans_share_exact_boundary(self):
        for fps in (30, 60):
            for frame in range(1000):
                first = worker.span_us(frame, 1, fps)
                second = worker.span_us(frame + 1, 1, fps)
                self.assertEqual(first["start"] + first["duration"], second["start"])
            self.assertEqual(worker.frame_us(fps * 3600, fps), 3_600_000_000)

    def test_zero_negative_fractional_duration_rejected(self):
        for duration in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                worker.span_us(0, duration, 30)

    def test_non_integer_frame_rejected(self):
        with self.assertRaises(ValueError):
            worker.frame_us(.5, 30)

    def test_draft_name_cannot_escape_root(self):
        for name in ("../official", "jed-probe-../x", "formal-draft", "jed-probe-"):
            with self.assertRaises(ValueError):
                worker.validate_spec({"schemaVersion": "jed-draft-probe/1", "name": name, "durationFrames": 90})

    def test_fps_and_version_are_explicit_capabilities(self):
        for patch in ({"fps": 29.97}, {"fps": 24}, {"schemaVersion": "later"}):
            with self.assertRaises(ValueError):
                worker.validate_spec({"schemaVersion": "jed-draft-probe/1", "name": "jed-probe-synthetic", "durationFrames": 90, **patch})

    def test_cue_must_be_inside_project(self):
        for cue in (-1, 90):
            with self.assertRaises(ValueError):
                worker.validate_spec({"schemaVersion": "jed-draft-probe/1", "name": "jed-probe-synthetic", "durationFrames": 90, "soundStartFrame": cue})

    def test_layer_and_material_references_checked(self):
        content = {"duration": 3_000_000, "materials": {"videos": [{"id": "base"}]},
                   "tracks": [{"type": "video", "segments": [{"id": "s", "material_id": "base",
                       "target_timerange": {"start": 0, "duration": 3_000_000}, "render_index": 0}]}]}
        self.assertEqual(worker.structure_check(content, 3_000_000)["status"], "passed")
        content["tracks"][0]["segments"][0]["render_index"] = 1
        with self.assertRaises(ValueError):
            worker.structure_check(content, 3_000_000)
        content["tracks"][0]["segments"][0]["render_index"] = 0
        content["tracks"][0]["segments"][0]["extra_material_refs"] = ["missing"]
        with self.assertRaises(ValueError):
            worker.structure_check(content, 3_000_000)

    def test_preview_caption_boundaries(self):
        props = {"fps": 30, "durationInFrames": 120,
                 "clips": [{"sourceStartFrame": 0, "outputStartFrame": 0, "durationInFrames": 120}],
                 "captions": [{"startFrame": 0, "endFrame": 60, "text": "保留修正字幕"},
                              {"startFrame": 60, "endFrame": 120, "text": "第二句"}]}
        self.assertEqual(worker.validate_preview(props), props)
        props["captions"][1]["startFrame"] = 59
        with self.assertRaises(ValueError):
            worker.validate_preview(props)
        props["captions"][1]["startFrame"] = 60
        props["captions"][1]["endFrame"] = 121
        with self.assertRaises(ValueError):
            worker.validate_preview(props)

    def test_preview_rejects_unimplemented_cuts(self):
        props = {"fps": 30, "durationInFrames": 120,
                 "clips": [{"sourceStartFrame": 30, "outputStartFrame": 0, "durationInFrames": 120}], "captions": []}
        with self.assertRaises(ValueError):
            worker.validate_preview(props)

    def test_preview_rejects_sound_field_before_external_import(self):
        with self.assertRaises(ValueError):
            worker.preview({"schemaVersion": "jed-draft-preview/1", "sound": "unwanted.wav"})


if __name__ == "__main__":
    unittest.main()
