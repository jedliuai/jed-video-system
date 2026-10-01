import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/jed-video-system/src'))
from jed_chapters.insertion import insert_chapters, validate_inserted_timeline
from jed_chapters.insertion_audio import audio_filter


class ChapterInsertionTests(unittest.TestCase):
    def setUp(self):
        self.base = {'fps': 30, 'durationInFrames': 600, 'sourceSrc': 'source.mp4',
            'clips': [{'sourceStartFrame': 0, 'outputStartFrame': 0, 'durationInFrames': 600}],
            'captions': [{'startFrame': 0, 'endFrame': 204, 'text': 'before'}, {'startFrame': 204, 'endFrame': 300, 'text': 'after'}],
            'overlays': [{'outputStartFrame': 204, 'durationInFrames': 90, 'headlineCueFrame': 20}]}
        self.cards = [{'id': 'chapter-1', 'sourceBoundaryFrame': 204, 'durationInFrames': 54,
            'placement': 'insert_hold', 'audioPolicy': 'pause_source',
            'boundaryEvidence': {'kind': 'between_sentences', 'before': 'before', 'after': 'after'},
            'title': 'Demo', 'number': '02', 'artSrc': 'art.png', 'styleId': 'paper-blue', 'styleRevision': 'r1',
            'sound': {'audioSrc': 'sound.wav', 'offsetFrames': 3, 'durationInFrames': 33, 'volume': 1}}]

    def test_preserves_every_original_frame_and_adds_gap(self):
        result = insert_chapters(self.base, self.cards)
        self.assertEqual(result['durationInFrames'], 654)
        self.assertEqual(result['clips'], [
            {'id': 'source-0', 'sourceStartFrame': 0, 'outputStartFrame': 0, 'durationInFrames': 204},
            {'id': 'source-1', 'sourceStartFrame': 204, 'outputStartFrame': 258, 'durationInFrames': 396}])
        self.assertEqual(self.base['durationInFrames'], 600)

    def test_caption_edges_and_animation_cues(self):
        result = insert_chapters(self.base, self.cards)
        self.assertEqual(result['captions'][0]['endFrame'], 204)
        self.assertEqual(result['captions'][1]['startFrame'], 258)
        self.assertEqual(result['overlays'][0]['outputStartFrame'], 258)
        self.assertEqual(result['overlays'][0]['headlineCueFrame'], 20)

    def test_rejects_split_spoken_phrase(self):
        self.base['captions'][0]['endFrame'] = 205
        with self.assertRaisesRegex(ValueError, 'caption phrase'):
            insert_chapters(self.base, self.cards)

    def test_rejects_interrupted_animation(self):
        self.base['overlays'][0]['outputStartFrame'] = 200
        with self.assertRaisesRegex(ValueError, 'animation'):
            insert_chapters(self.base, self.cards)

    def test_rejects_sound_spilling_into_speech(self):
        self.cards[0]['sound']['durationInFrames'] = 54
        with self.assertRaisesRegex(ValueError, 'finish inside'):
            insert_chapters(self.base, self.cards)

    def test_rejects_double_insertion(self):
        with self.assertRaises(ValueError):
            insert_chapters(insert_chapters(self.base, self.cards), self.cards)

    def test_multiple_gaps_keep_source_order(self):
        second = copy.deepcopy(self.cards[0])
        second.update(id='chapter-2', sourceBoundaryFrame=400)
        result = insert_chapters(self.base, [*self.cards, second])
        self.assertEqual(result['durationInFrames'], 708)
        self.assertEqual(result['clips'][2]['sourceStartFrame'], 400)
        self.assertEqual(result['clips'][2]['outputStartFrame'], 508)

    def test_rejects_deleted_source_frames(self):
        result = insert_chapters(self.base, self.cards)
        result['clips'][1]['sourceStartFrame'] += 1
        with self.assertRaisesRegex(ValueError, 'preserved'):
            validate_inserted_timeline(result)

    def test_rejects_missing_card(self):
        result = insert_chapters(self.base, self.cards)
        result['chapterTransitions'] = []
        with self.assertRaises(ValueError):
            validate_inserted_timeline(result)

    def test_rejects_missing_or_tampered_sound(self):
        result = insert_chapters(self.base, self.cards)
        result['soundEffects'][0]['outputStartFrame'] = 258
        with self.assertRaisesRegex(ValueError, 'overlap'):
            validate_inserted_timeline(result)
        result['soundEffects'] = []
        with self.assertRaises(ValueError):
            validate_inserted_timeline(result)

    def test_requires_sentence_evidence_and_explicit_pause(self):
        self.cards[0]['audioPolicy'] = 'continue_source'
        with self.assertRaises(ValueError):
            insert_chapters(self.base, self.cards)
        self.cards[0]['audioPolicy'] = 'pause_source'
        self.cards[0]['boundaryEvidence'] = {}
        with self.assertRaises(ValueError):
            insert_chapters(self.base, self.cards)

    def test_audio_graph_concatenates_silence_instead_of_muting_words(self):
        graph = audio_filter(insert_chapters(self.base, self.cards))
        self.assertIn('atrim=start_sample=326400:end_sample=960000', graph)
        self.assertIn('anullsrc=r=48000:cl=stereo,atrim=end_sample=86400', graph)
        self.assertIn('[voice0][gap0][voice1]concat=n=3:v=0:a=1', graph)
        self.assertIn('adelay=331200S:all=1', graph)
        self.assertIn('normalize=0', graph)


if __name__ == '__main__':
    unittest.main()
