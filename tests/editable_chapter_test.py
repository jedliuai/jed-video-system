from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugins/jed-video-system/src'))
from jed_chapters.insertion import insert_chapters
from jed_chapters.editable import accepted_insertion, overlay_source_frame
from jed_chapters.delivery import sha
from jed_review import new_state, register_candidate, request_review, record_decision

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

worker = module('editable_worker', ROOT / 'workers/draft-adapter/worker.py')
inserted = module('editable_inserted', ROOT / 'workers/draft-adapter/inserted.py')


def props_fixture():
    base = {'fps': 30, 'durationInFrames': 600, 'sourceSrc': 'source.mp4',
        'clips': [{'sourceStartFrame': 0, 'outputStartFrame': 0, 'durationInFrames': 600}],
        'captions': [{'startFrame': 0, 'endFrame': 204, 'text': '前句'}, {'startFrame': 204, 'endFrame': 300, 'text': '后句'}],
        'overlays': [{'id': 'demo', 'outputStartFrame': 204, 'durationInFrames': 90}]}
    cards = [{'id': 'chapter', 'sourceBoundaryFrame': 204, 'durationInFrames': 54,
        'placement': 'insert_hold', 'audioPolicy': 'pause_source',
        'boundaryEvidence': {'kind': 'between_sentences', 'before': '前句', 'after': '后句'},
        'title': '实机演示', 'number': '02', 'artSrc': 'art.png', 'styleId': 'jed-paper-blue', 'styleRevision': 'r1',
        'sound': {'audioSrc': 'sound.wav', 'offsetFrames': 3, 'durationInFrames': 33, 'volume': 1}}]
    return insert_chapters(base, cards)


class EditableChapterTests(unittest.TestCase):
    def test_motion_maps_to_original_alpha_clock(self):
        props = props_fixture()
        self.assertEqual(props['overlays'][0]['outputStartFrame'], 258)
        self.assertEqual(overlay_source_frame(props, props['overlays'][0]), 204)

    def test_motion_crossing_gap_is_rejected(self):
        props = props_fixture()
        with self.assertRaisesRegex(ValueError, 'cross'):
            overlay_source_frame(props, {'outputStartFrame': 190, 'durationInFrames': 40})

    def acceptance_fixture(self, directory, approved=True):
        props = props_fixture()
        path = Path(directory) / 'props.json'
        path.write_text(json.dumps(props), encoding='utf-8')
        sample = Path(directory) / 'sample.mp4'
        sample.write_bytes(b'synthetic review artifact')
        common = {'scopeId': 'chapter', 'revision': 'r2', 'contentRevision': 'live-r1',
            'patternId': 'paper-blue', 'operationVersion': 'insert-r2', 'coverage': 'sample'}
        state = register_candidate(new_state('test'), {**common, 'candidateId': 'props',
            'scope': 'technical_preparation', 'artifactKind': 'report', 'operations': ['probe_media'],
            'locator': str(path), 'artifactDigest': sha(path)})
        state = register_candidate(state, {**common, 'candidateId': 'sample', 'scope': 'audio_sample',
            'artifactKind': 'video', 'operations': ['insert_chapter_with_sound'], 'locator': str(sample),
            'artifactDigest': sha(sample), 'dependsOn': ['props']})
        state = request_review(state, 'sample', '请看具体样片。')
        if approved:
            state = record_decision(state, state['requests'][-1]['requestId'], 'approved', '认可衔接')
        return state, path, props, sample

    def test_current_insert_acceptance_is_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            state, path, props, _ = self.acceptance_fixture(directory)
            accepted = accepted_insertion(state, 'sample', path, props)
            self.assertTrue(accepted['chapterSoundAndPacingApproved'])
            self.assertFalse(accepted['wholeVideoApproved'])

    def test_pending_acceptance_cannot_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            state, path, props, _ = self.acceptance_fixture(directory, False)
            with self.assertRaisesRegex(ValueError, 'accepted'):
                accepted_insertion(state, 'sample', path, props)

    def test_changed_media_or_props_cannot_borrow_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            state, path, props, sample = self.acceptance_fixture(directory)
            sample.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'changed'):
                accepted_insertion(state, 'sample', path, props)

    def test_old_visual_acceptance_cannot_approve_insert_sound(self):
        with tempfile.TemporaryDirectory() as directory:
            state, path, props, _ = self.acceptance_fixture(directory)
            with self.assertRaises(ValueError):
                accepted_insertion(state, 'props', path, props)

    def test_missing_separate_media_is_not_dropped(self):
        with self.assertRaisesRegex(ValueError, 'separate material'):
            inserted.validate_layers(props_fixture(), {'schemaVersion': 'jed-draft-inserted/1', 'name': 'jed-probe-editable-test'}, worker)

    def test_native_png_can_keep_generator_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            props = props_fixture()
            spec = {'schemaVersion': 'jed-draft-inserted/1', 'name': 'jed-probe-editable-test'}
            info_by_path = {}
            for field, events, suffix in (('overlayMedia', props['overlays'], '.mov'), ('chapterImages', props['chapterTransitions'], '.png'), ('soundMedia', props['soundEffects'], '.wav')):
                spec[field] = []
                for event in events:
                    path = Path(directory) / (event['id'] + suffix)
                    path.write_bytes(b'synthetic media')
                    spec[field].append({'id': event['id'], 'path': str(path), 'sha256': worker.sha256(path), 'eventDigest': worker.chapter_event_digest(event)})
                    info_by_path[path] = {'durationUs': worker.frame_us(event['durationInFrames'], 30),
                        'video': {'width': 1672, 'height': 941} if field == 'chapterImages' else
                        {'width': 1920, 'height': 1080, 'codec_name': 'prores', 'pix_fmt': 'yuva444p12le', 'avg_frame_rate': '30/1'},
                        'streams': [{'codec_type': 'audio'}] if field == 'soundMedia' else []}
            with patch.object(worker, 'metadata', side_effect=lambda path: info_by_path[path]):
                self.assertEqual(inserted.validate_layers(props, spec, worker), props)

    def native_content_fixture(self, directory):
        props = props_fixture()
        roles = {role: role for role in ('footage', 'motion', 'captions', 'chapter-matte', 'chapter-art', 'chapter-number', 'chapter-title', 'chapter-brand', 'chapter-line', 'voice', 'sfx')}
        content = {'duration': worker.frame_us(props['durationInFrames'], 30), 'materials': {'videos': [], 'audios': [], 'texts': []}, 'tracks': []}
        counter = 0
        for index, role in enumerate(roles):
            kind = 'audio' if role in ('voice', 'sfx') else 'text' if role in ('captions', 'chapter-number', 'chapter-title', 'chapter-brand', 'chapter-line') else 'video'
            track = {'id': role, 'type': kind, 'segments': []}
            content['tracks'].append(track)
            if role in ('footage', 'voice'):
                events = props['clips']
            elif role == 'motion':
                events = props['overlays']
            elif role == 'captions':
                events = [{'outputStartFrame': cap['startFrame'], 'durationInFrames': cap['endFrame']-cap['startFrame'], 'text': cap['text']} for cap in props['captions']]
            elif role == 'sfx':
                events = props['soundEffects']
            else:
                events = props['chapterTransitions']
            for event in events:
                counter += 1
                key = str(counter)
                material = {'id': key}
                if kind == 'text':
                    value = event['text'] if role == 'captions' else event['title'] if role == 'chapter-title' else event['number'] if role == 'chapter-number' else 'Decoration'
                    font = Path(directory) / 'font.ttf'
                    font.write_bytes(b'synthetic font')
                    material['content'] = json.dumps({'text': value, 'styles': [{'font': {'id': '', 'path': str(font)}}]})
                    content['materials']['texts'].append(material)
                elif kind == 'video':
                    material['type'] = 'photo' if role in ('chapter-art', 'chapter-matte') else 'video'
                    media = Path(directory) / f'{key}.png'
                    media.write_bytes(b'synthetic')
                    material['path'] = str(media)
                    content['materials']['videos'].append(material)
                else:
                    content['materials']['audios'].append(material)
                segment = {'id': 'segment-' + key, 'material_id': key,
                    'target_timerange': worker.span_us(event['outputStartFrame'], event['durationInFrames'], 30),
                    'source_timerange': worker.span_us(event.get('sourceStartFrame', 0), event['durationInFrames'], 30),
                    'volume': 1 if kind == 'audio' else 0, 'render_index': index}
                if role == 'chapter-art':
                    segment['common_keyframes'] = [{'property_type': 'KFTypeAlpha'}]
                track['segments'].append(segment)
        return props, content, roles

    def test_saved_layers_retain_native_text_image_and_voice(self):
        with tempfile.TemporaryDirectory() as directory:
            props, content, roles = self.native_content_fixture(directory)
            checked = inserted.verify_layer_content(content, props, roles, worker)
            self.assertEqual(checked['editableCaptionCount'], 2)
            self.assertEqual(checked['nativeChapterImages'], 1)
            self.assertTrue(checked['separateSourceVoice'])

    def test_accidental_double_voice_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            props, content, roles = self.native_content_fixture(directory)
            content['tracks'][0]['segments'][0]['volume'] = 1
            with self.assertRaisesRegex(ValueError, 'voice separation'):
                inserted.verify_layer_content(content, props, roles, worker)

    def test_saved_caption_clock_or_text_cannot_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            props, content, roles = self.native_content_fixture(directory)
            track = next(track for track in content['tracks'] if track['id'] == 'captions')
            track['segments'][1]['target_timerange']['start'] -= 1800000
            with self.assertRaises(ValueError):
                inserted.verify_layer_content(content, props, roles, worker)

    def test_flattened_chapter_video_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            props, content, roles = self.native_content_fixture(directory)
            track = next(track for track in content['tracks'] if track['id'] == 'chapter-art')
            key = track['segments'][0]['material_id']
            next(material for material in content['materials']['videos'] if material['id'] == key)['type'] = 'video'
            with self.assertRaisesRegex(ValueError, 'native image'):
                inserted.verify_layer_content(content, props, roles, worker)

    def test_native_font_is_not_silently_lost(self):
        with tempfile.TemporaryDirectory() as directory:
            props, content, roles = self.native_content_fixture(directory)
            material = content['materials']['texts'][0]
            embedded = json.loads(material['content'])
            embedded['styles'][0]['font']['path'] = ''
            material['content'] = json.dumps(embedded)
            with self.assertRaisesRegex(ValueError, 'font file'):
                inserted.verify_layer_content(content, props, roles, worker)


if __name__ == '__main__':
    unittest.main()
