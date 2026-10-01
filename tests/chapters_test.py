from copy import deepcopy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/jed-video-system/src'))
from jed_chapters import compile_chapters


class ChapterTests(unittest.TestCase):
    def setUp(self):
        self.props = {'sourceSrc': 'source.mp4', 'fps': 30, 'durationInFrames': 600,
            'clips': [{'id': 'main', 'sourceStartFrame': 0, 'outputStartFrame': 0, 'durationInFrames': 600}],
            'overlays': [], 'captions': [{'startFrame': 210, 'endFrame': 260, 'text': '接下来演示'}]}
        self.plan = {'schemaVersion': '0.1.0', 'sourcePropsSha256': 'a' * 64,
            'source': {'publicFile': 'source.mp4', 'fps': 30, 'durationInFrames': 600, 'mediaSha256': 'b' * 64},
            'style': {'id': 'paper', 'revision': 'r1', 'referenceAsset': 'chapters/art.png',
                      'referenceSha256': 'c' * 64, 'imageBackend': 'synthetic-fixture'},
            'sections': [{'id': 'demo', 'kind': 'demonstration', 'startFrame': 200, 'endFrame': 600,
                'title': '实机演示', 'summary': '演示操作',
                'evidence': {'quote': '接下来演示', 'atFrame': 200, 'confidence': 0.96},
                'bridge': {'kind': 'spoken_bridge', 'startFrame': 200, 'endFrame': 260},
                'transition': {'number': '02', 'durationInFrames': 54, 'placement': 'cover_bridge', 'audioPolicy': 'continue_source'}}]}

    def compile(self):
        return compile_chapters(self.plan, self.props, 'a' * 64, 'b' * 64)

    def test_candidate_preserves_audio_clock_captions_and_source_props(self):
        original = deepcopy(self.props)
        result = self.compile()
        self.assertEqual(self.props, original)
        for key in original:
            self.assertEqual(result[key], original[key])
        self.assertEqual(result['chapterTransitions'][0]['outputStartFrame'], 200)
        self.assertFalse(result['chapterReview']['humanApproved'])

    def test_updated_timeline_or_source_requires_new_analysis(self):
        for key in ('timeline', 'source'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                compile_chapters(self.plan, self.props, 'd' * 64 if key == 'timeline' else 'a' * 64,
                                 'd' * 64 if key == 'source' else 'b' * 64)

    def test_uncertain_boundary_does_not_create_a_card(self):
        self.plan['sections'][0]['evidence']['confidence'] = 0.6
        with self.assertRaisesRegex(ValueError, 'Uncertain'):
            self.compile()

    def test_card_cannot_hide_an_operation_after_the_bridge(self):
        self.plan['sections'][0]['bridge']['endFrame'] = 240
        with self.assertRaisesRegex(ValueError, 'outside the verified spoken bridge'):
            self.compile()

    def test_pause_or_insert_cannot_silently_shift_audio(self):
        self.plan['sections'][0]['transition']['audioPolicy'] = 'pause_source'
        with self.assertRaisesRegex(ValueError, 'separate mapping'):
            self.compile()

    def test_edited_source_requires_new_source_to_output_mapping(self):
        self.props['clips'][0]['sourceStartFrame'] = 15
        with self.assertRaisesRegex(ValueError, 'new mapping'):
            self.compile()

    def test_ordered_sections_reject_overlap(self):
        other = deepcopy(self.plan['sections'][0])
        other['id'] = 'another'
        self.plan['sections'].append(other)
        with self.assertRaisesRegex(ValueError, 'nonoverlapping'):
            self.compile()

    def test_outline_does_not_force_transition_on_every_section(self):
        self.plan['sections'][0].pop('transition')
        self.assertEqual(self.compile()['chapterTransitions'], [])

    def test_reference_art_stays_local(self):
        self.plan['style']['referenceAsset'] = '../outside.png'
        with self.assertRaisesRegex(ValueError, 'local public asset'):
            self.compile()

    def test_transition_length_stays_inside_section(self):
        self.plan['sections'][0]['endFrame'] = 220
        with self.assertRaisesRegex(ValueError, 'within the chapter'):
            self.compile()

    def test_boundary_quote_requires_source_frame(self):
        self.plan['sections'][0]['evidence']['atFrame'] = 190
        with self.assertRaisesRegex(ValueError, 'source frame'):
            self.compile()

    def test_short_editable_title_and_number(self):
        self.plan['sections'][0]['transition']['number'] = '<script>'
        with self.assertRaisesRegex(ValueError, 'two editable digits'):
            self.compile()


if __name__ == '__main__':
    unittest.main()
