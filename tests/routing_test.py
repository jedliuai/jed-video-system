from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/jed-video-system/src'))
from jed_routing import route_project


def capability(*features, connected=True):
    return {'connected': connected, 'features': list(features),
            'evidence': {'source': 'synthetic test fixture', 'checkedAt': '2026-10-01T10:00:00+08:00'}}


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.request = {'schemaVersion': '0.1.0', 'projectId': 'fixture',
                        'destination': 'jianying', 'stages': ['transcribe', 'motion', 'assemble']}
        self.capabilities = {'video-use': capability('transcription'),
                             'remotion': capability('fixed-motion', 'video-preview'),
                             'jianying-draft': capability('draft-assembly', 'editable-captions'),
                             'chatcut-hosted': capability('script-edit', 'transcription',
                                 'editable-timeline', 'captions', 'composed-preview', 'video-export')}

    def test_local_route_keeps_existing_tools(self):
        result = route_project(self.request, self.capabilities)
        self.assertEqual([r['backend'] for r in result['routes']],
                         ['video-use', 'remotion', 'jianying-draft'])
        self.assertEqual(result['status'], 'route_ready')
        self.assertFalse(result['executionAuthorized'])

    def test_speech_edit_in_chatcut_uses_chatcut(self):
        self.request.update(destination='chatcut', stages=['speech_edit', 'captions', 'assemble'])
        result = route_project(self.request, self.capabilities)
        self.assertEqual(result['status'], 'route_ready')
        self.assertTrue(all(r['backend'] == 'chatcut-hosted' for r in result['routes']))

    def test_disconnected_tools_cannot_route(self):
        self.request.update(destination='chatcut', stages=['speech_edit'])
        self.capabilities['chatcut-hosted']['connected'] = False
        self.assertEqual(route_project(self.request, self.capabilities)['status'], 'blocked')

    def test_installed_without_capability_evidence_is_not_usable(self):
        self.capabilities['remotion'].pop('evidence')
        self.assertEqual(route_project(self.request, self.capabilities)['blockers'][0]['stage'], 'motion')

    def test_native_jianying_verification_is_not_structure_check(self):
        self.request['stages'] = ['assemble', 'verify', 'export']
        result = route_project(self.request, self.capabilities)
        self.assertEqual([b['stage'] for b in result['blockers']], ['verify', 'export'])

    def test_editor_destination_never_silently_falls_back(self):
        self.request.update(destination='chatcut', stages=['assemble'])
        self.capabilities.pop('chatcut-hosted')
        result = route_project(self.request, self.capabilities)
        self.assertIsNone(result['routes'][0]['backend'])
        self.assertEqual(result['timelineOwner'], 'chatcut')

    def test_explicit_override_is_not_ignored(self):
        self.request['backendOverrides'] = {'motion': 'chatcut-hosted'}
        self.assertEqual(route_project(self.request, self.capabilities)['blockers'][0]['reason'],
                         'requested_backend_unavailable')

    def test_chatcut_speech_handoff_to_jianying_requires_mapping(self):
        self.request['stages'] = ['speech_edit']
        result = route_project(self.request, self.capabilities)
        self.assertEqual(result['blockers'][0]['reason'], 'speech_handoff_mapping_not_implemented')
        self.capabilities['chatcut-handoff'] = capability('source-time-mapping')
        self.assertEqual(route_project(self.request, self.capabilities)['status'], 'route_ready')

    def test_whisperx_json_import_is_not_assumed(self):
        self.request.update(destination='chatcut', stages=['transcribe'])
        self.capabilities['chatcut-hosted']['features'].remove('transcription')
        self.assertEqual(route_project(self.request, self.capabilities)['blockers'][0]['reason'],
                         'external_transcript_import_not_verified')

    def test_remotion_overlay_needs_separate_asset_handoff(self):
        self.request.update(destination='chatcut', stages=['motion'])
        self.assertEqual(route_project(self.request, self.capabilities)['status'], 'blocked')
        self.capabilities['chatcut-handoff'] = capability('original-and-overlay-import')
        self.assertEqual(route_project(self.request, self.capabilities)['status'], 'route_ready')

    def test_false_connected_and_missing_features_do_not_pass(self):
        self.capabilities['video-use']['features'] = []
        self.assertEqual(route_project(self.request, self.capabilities)['status'], 'blocked')

    def test_preview_export_is_not_native_editor_export(self):
        self.request.update(destination='preview', stages=['export'])
        result = route_project(self.request, self.capabilities)
        self.assertEqual(result['routes'][0]['feature'], 'video-preview')

    def test_input_is_not_mutated(self):
        original = deepcopy(self.capabilities)
        route_project(self.request, self.capabilities)
        self.assertEqual(self.capabilities, original)

    def test_bad_input_is_rejected(self):
        for updates in ({'destination': 'capcut-web-draft'}, {'stages': ['motion', 'motion']},
                        {'stages': ['invented']}, {'projectId': ''},
                        {'backendOverrides': {'missing-stage': 'remotion'}}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                route_project({**self.request, **updates}, self.capabilities)

    def test_installation_string_cannot_replace_connected_boolean(self):
        self.capabilities['chatcut-hosted']['connected'] = 'installed'
        with self.assertRaises(ValueError):
            route_project(self.request, self.capabilities)

    def test_editable_motion_can_use_chatcut_within_chatcut(self):
        self.request.update(destination='chatcut', stages=['motion'], motionMode='editable')
        self.capabilities['chatcut-hosted']['features'].append('editable-motion')
        result = route_project(self.request, self.capabilities)
        self.assertEqual(result['status'], 'route_ready')
        self.assertEqual(result['routes'][0]['backend'], 'chatcut-hosted')

    def test_editable_motion_is_not_promised_to_transfer_to_jianying(self):
        self.request.update(stages=['motion'], motionMode='editable')
        self.capabilities['chatcut-hosted']['features'].append('editable-motion')
        self.assertEqual(route_project(self.request, self.capabilities)['blockers'][0]['reason'],
                         'alpha_graphic_handoff_not_verified')


if __name__ == '__main__':
    unittest.main()
