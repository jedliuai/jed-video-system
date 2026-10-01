import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/jed-video-system/src'))
from jed_chapters.delivery import accepted_recipe, asset_props, sha
from jed_review import new_state, register_candidate, request_review, record_decision


class ChapterDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.event = {'id': 'demo', 'outputStartFrame': 204, 'durationInFrames': 54,
            'styleId': 'paper', 'styleRevision': 'r1', 'audioPolicy': 'continue_source',
            'title': '实机演示', 'number': '02', 'artSrc': 'art.png'}
        self.props = {'sourceSrc': 'source.mp4', 'fps': 30, 'durationInFrames': 1224,
            'clips': [{'id': 'main'}], 'overlays': [{'id': 'old'}], 'captions': [{'text': '原字幕'}],
            'chapterTransitions': [self.event]}
        self.path = self.root / 'props.json'
        self.path.write_text(json.dumps(self.props), encoding='utf-8')
        self.sample = self.root / 'sample.mp4'
        self.sample.write_bytes(b'synthetic sample')
        common = {'revision': 'r1', 'contentRevision': 'c1', 'patternId': 'paper',
            'operationVersion': 'chapter-r1', 'scopeId': 'chapters'}
        self.state = register_candidate(new_state('synthetic-project'), {**common,
            'candidateId': 'props', 'scope': 'technical_preparation', 'coverage': 'single',
            'operations': ['compile_plan'], 'artifactKind': 'plan',
            'locator': str(self.path), 'artifactDigest': sha(self.path)})
        self.state = register_candidate(self.state, {**common, 'candidateId': 'sample',
            'scope': 'visual_sample', 'coverage': 'sample', 'operations': ['add_chapter_transition'],
            'artifactKind': 'video', 'locator': str(self.sample), 'artifactDigest': sha(self.sample),
            'dependsOn': ['props']})
        self.state = request_review(self.state, 'sample', 'Synthetic fixture only')

    def accept(self):
        self.state = record_decision(self.state, self.state['requests'][-1]['requestId'],
                                    'approved', 'Synthetic fixture only')

    def test_accepted_recipe_does_not_approve_the_whole_video(self):
        self.accept()
        result = accepted_recipe(self.state, 'sample', self.path, self.props)
        self.assertTrue(result['chapterRecipeApproved'])
        self.assertFalse(result['wholeVideoApproved'])

    def test_pending_recipe_is_not_executed(self):
        with self.assertRaisesRegex(ValueError, 'not currently accepted'):
            accepted_recipe(self.state, 'sample', self.path, self.props)

    def test_changed_actual_sample_is_rejected(self):
        self.accept()
        self.sample.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed/missing'):
            accepted_recipe(self.state, 'sample', self.path, self.props)

    def test_other_props_cannot_borrow_a_style_acceptance(self):
        self.accept()
        other = self.root / 'other.json'
        other.write_bytes(self.path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'exact accepted sample input'):
            accepted_recipe(self.state, 'sample', other, self.props)

    def test_asset_has_no_source_video_or_caption_layers(self):
        result = asset_props(self.props, self.event)
        self.assertEqual(result['durationInFrames'], 54)
        self.assertEqual(result['chapterTransitions'][0]['outputStartFrame'], 0)
        self.assertEqual((result['clips'], result['captions'], result['overlays']), ([], [], []))
        self.assertEqual(self.event['outputStartFrame'], 204)

    def test_asset_cannot_extend_beyond_timeline_or_pause_source(self):
        for change in ({'outputStartFrame': 1220}, {'audioPolicy': 'pause_source'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                asset_props(self.props, {**self.event, **change})


if __name__ == '__main__':
    unittest.main()
