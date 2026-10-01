"""Observable dispatch behaviour with fake commands and real local evidence."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/jed-video-system/src'))
from jed_dispatch import dispatch
from jed_dispatch.runner import sha
from jed_review import new_state, register_candidate, request_review, record_decision


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ['motion-lab/public/source.mp4', 'motion-lab/public/fonts/jed-sans-regular.ttf',
                     'motion-lab/public/fonts/jed-sans-bold.ttf', 'motion-lab/package-lock.json',
                     'motion-lab/remotion.config.ts', 'motion-lab/src/Root.tsx',
                     'motion-lab/node_modules/@remotion/cli/remotion-cli.js',
                     'plugins/jed-video-system/src/jed_dispatch/runner.py', 'node', 'browser']:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name, encoding='utf-8')
        self.write('motion-lab/node_modules/@remotion/cli/package.json', {'version': '4.0.530'})
        self.write('local.json', {'remotion': {'browserExecutable': str(self.root / 'browser')}})
        self.write('props.json', {'sourceSrc': 'source.mp4', 'fps': 30, 'durationInFrames': 300})
        self.request = {'schemaVersion': '0.1.0', 'jobId': 'same-job', 'projectId': 'test',
                        'action': 'remotion-still', 'phase': 'prepare', 'frame': 180,
                        'localConfig': 'local.json', 'renderProps': 'props.json',
                        'intent': {'authorizedActions': ['remotion-still']}}
        self.capabilities = {'remotion': {'connected': True, 'features': ['fixed-motion'],
            'evidence': {'source': 'synthetic fixture', 'checkedAt': '2026-10-01'}}}
        self.which = patch('jed_dispatch.runner.shutil.which', return_value=str(self.root / 'node'))
        self.which.start()
        self.addCleanup(self.which.stop)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding='utf-8')

    def fake_run(self, argv, **kwargs):
        Path(argv[4]).write_bytes(b'fake png output')
        return subprocess.CompletedProcess(argv, 0, 'rendered', '')

    def test_plan_does_not_execute_or_create_job(self):
        with patch('jed_dispatch.runner.subprocess.run') as run:
            result = dispatch(self.root, self.request, self.capabilities)
        run.assert_not_called()
        self.assertEqual(result['status'], 'planned')
        self.assertFalse((self.root / 'work/dispatch/same-job').exists())

    def test_prepare_sample_can_run_before_aesthetic_approval(self):
        with patch('jed_dispatch.runner.subprocess.run', side_effect=self.fake_run) as run:
            result = dispatch(self.root, self.request, self.capabilities, execute=True)
        self.assertEqual(result['status'], 'succeeded')
        self.assertFalse(result['humanApproved'])
        self.assertFalse(result['published'])
        self.assertFalse(run.call_args.kwargs['shell'])

    def test_success_reuses_outputs_without_executing_twice(self):
        with patch('jed_dispatch.runner.subprocess.run', side_effect=self.fake_run) as run:
            dispatch(self.root, self.request, self.capabilities, execute=True)
            result = dispatch(self.root, self.request, self.capabilities, execute=True)
        self.assertTrue(result['reused'])
        self.assertEqual(run.call_count, 1)

    def test_changed_input_cannot_reuse_receipt(self):
        with patch('jed_dispatch.runner.subprocess.run', side_effect=self.fake_run):
            dispatch(self.root, self.request, self.capabilities, execute=True)
        (self.root / 'motion-lab/public/source.mp4').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'different inputs'):
            dispatch(self.root, self.request, self.capabilities, execute=True)

    def test_changed_output_cannot_reuse_receipt(self):
        with patch('jed_dispatch.runner.subprocess.run', side_effect=self.fake_run):
            dispatch(self.root, self.request, self.capabilities, execute=True)
        (self.root / 'work/dispatch/same-job/preview.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'output changed'):
            dispatch(self.root, self.request, self.capabilities, execute=True)

    def test_changed_implementation_cannot_reuse_receipt(self):
        with patch('jed_dispatch.runner.subprocess.run', side_effect=self.fake_run):
            dispatch(self.root, self.request, self.capabilities, execute=True)
        (self.root / 'motion-lab/src/Root.tsx').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'different inputs/implementation'):
            dispatch(self.root, self.request, self.capabilities, execute=True)

    def test_failure_is_recorded_and_not_automatically_retried(self):
        with patch('jed_dispatch.runner.subprocess.run', return_value=subprocess.CompletedProcess([], 9, '', 'bad')) as run:
            result = dispatch(self.root, self.request, self.capabilities, execute=True)
            with self.assertRaisesRegex(ValueError, 'Prior job did not succeed'):
                dispatch(self.root, self.request, self.capabilities, execute=True)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(run.call_count, 1)

    def test_missing_intent_blocks_before_process(self):
        self.request['intent']['authorizedActions'] = []
        with self.assertRaisesRegex(ValueError, 'lacks explicit project intent'):
            dispatch(self.root, self.request, self.capabilities, execute=True)

    def test_fake_connected_snapshot_does_not_replace_local_runtime(self):
        (self.root / 'browser').unlink()
        with self.assertRaisesRegex(ValueError, 'CLI, Node and browser'):
            dispatch(self.root, self.request, self.capabilities)

    def test_expected_hash_blocks_new_unreviewed_revision(self):
        self.request['expectedInputHashes'] = {'props.json': '0' * 64}
        with self.assertRaisesRegex(ValueError, 'expected reviewed revision'):
            dispatch(self.root, self.request, self.capabilities)

    def test_invalid_frame_is_rejected(self):
        for frame in (-1, 300, True):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                dispatch(self.root, {**self.request, 'frame': frame}, self.capabilities)

    def test_no_arbitrary_command_hosted_or_publication(self):
        for action in ('shell', 'chatcut-edit', 'publish-draft'):
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, 'Unsupported local action'):
                dispatch(self.root, {**self.request, 'action': action}, self.capabilities)

    def test_job_path_traversal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'jobId'):
            dispatch(self.root, {**self.request, 'jobId': '../escape'}, self.capabilities)

    def test_input_changed_during_render_records_failure(self):
        def change_and_render(argv, **kwargs):
            self.fake_run(argv, **kwargs)
            (self.root / 'motion-lab/public/source.mp4').write_bytes(b'new')
            return subprocess.CompletedProcess(argv, 0, '', '')
        with patch('jed_dispatch.runner.subprocess.run', side_effect=change_and_render):
            result = dispatch(self.root, self.request, self.capabilities, execute=True)
        self.assertEqual(result['status'], 'failed')

    def test_empty_backend_features_block(self):
        self.capabilities['remotion']['features'] = []
        with self.assertRaisesRegex(ValueError, 'backend capability'):
            dispatch(self.root, self.request, self.capabilities)

    def test_review_requires_current_project_and_all_inputs(self):
        from jed_dispatch.runner import _review
        sample = self.root / 'sample.mp4'
        sample.write_bytes(b'rough cut')
        candidate = {'candidateId': 'cut', 'scope': 'rough_cut', 'scopeId': 'whole',
                     'revision': 'r1', 'contentRevision': 'c1', 'patternId': 'a',
                     'operationVersion': 'v1', 'operations': ['assemble'], 'coverage': 'single',
                     'artifactKind': 'video', 'locator': str(sample), 'artifactDigest': sha(sample)}
        state = register_candidate(new_state('test'), candidate)
        state = request_review(state, 'cut', 'Synthetic test only')
        state = record_decision(state, state['requests'][-1]['requestId'], 'approved', 'Synthetic test input')
        with self.assertRaisesRegex(ValueError, 'all current props'):
            _review(state, 'cut', 'test', {str(self.root / 'props.json'): sha(self.root / 'props.json')})
        with self.assertRaisesRegex(ValueError, 'projectId'):
            _review(state, 'cut', 'other-project', {})

    def draft_fixture(self, approved=True, scope='rough_cut'):
        for name in ['motion-lab/public/live-source.mp4', 'work/renders/talking-head-overlay.mov',
                     'scripts/create-live-draft.ps1', 'workers/draft-adapter/worker.py',
                     'bridge-python', 'bridge-config.json', 'sample.mp4']:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
        (self.root / 'bridge/jianying_bridge').mkdir(parents=True)
        self.write('local.json', {'jianying': {'python': 'bridge-python',
            'bridgeConfig': 'bridge-config.json', 'bridgeProject': 'bridge'}})
        self.write('work/plans/live-render-props.json',
                   {'sourceSrc': 'live-source.mp4', 'fps': 30, 'durationInFrames': 300})
        request = {**self.request, 'action': 'create-isolated-draft',
                   'phase': 'reviewed-apply', 'renderProps': 'work/plans/live-render-props.json',
                   'intent': {'authorizedActions': ['create-isolated-draft']},
                   'reviewState': 'review.json', 'reviewCandidateId': 'cut'}
        capabilities = {'jianying-draft': {'connected': True, 'features': ['draft-assembly'],
            'evidence': {'source': 'synthetic fixture', 'checkedAt': '2026-10-01'}}}
        state = new_state('test')
        dependencies = []
        for i, name in enumerate(['work/plans/live-render-props.json',
            'motion-lab/public/live-source.mp4', 'motion-lab/public/fonts/jed-sans-regular.ttf',
            'motion-lab/public/fonts/jed-sans-bold.ttf', 'work/renders/talking-head-overlay.mov']):
            key = f'input-{i}'
            dependencies.append(key)
            path = self.root / name
            state = register_candidate(state, {'candidateId': key, 'scope': 'technical_preparation',
                'scopeId': name, 'revision': 'r1', 'contentRevision': 'c1', 'patternId': 'a',
                'operationVersion': 'v1', 'operations': ['probe_media'], 'coverage': 'single',
                'artifactKind': 'report', 'locator': str(path), 'artifactDigest': sha(path)})
        path = self.root / 'sample.mp4'
        state = register_candidate(state, {'candidateId': 'cut', 'scope': scope, 'scopeId': 'whole',
            'revision': 'r1', 'contentRevision': 'c1', 'patternId': 'a', 'operationVersion': 'v1',
            'operations': ['assemble'], 'coverage': 'single', 'artifactKind': 'video',
            'locator': str(path), 'artifactDigest': sha(path), 'dependsOn': dependencies})
        state = request_review(state, 'cut', 'Synthetic test only')
        if approved:
            state = record_decision(state, state['requests'][-1]['requestId'],
                                    'approved', 'Synthetic test input')
        self.write('review.json', state)
        return request, capabilities

    def fake_draft(self, argv, **kwargs):
        self.assertNotIn('-Publish', argv)
        output_root = Path(argv[argv.index('-OutputRoot') + 1])
        output_root.mkdir(parents=True)
        draft = output_root / 'isolated-draft'
        draft.mkdir()
        (draft / 'draft_info.json').write_text('{}', encoding='utf-8')
        evidence = output_root / 'result.json'
        evidence.write_text(json.dumps({'published': False, 'draftPath': str(draft)}), encoding='utf-8')
        return subprocess.CompletedProcess(argv, 0, f'Evidence: {evidence}\n', '')

    def test_reviewed_draft_runs_with_approved_cut_and_current_dependency_files(self):
        request, capabilities = self.draft_fixture()
        with patch('jed_dispatch.runner.subprocess.run', side_effect=self.fake_draft) as run:
            result = dispatch(self.root, request, capabilities, execute=True)
        self.assertEqual(result['status'], 'succeeded')
        self.assertTrue(result['humanApproved'])
        self.assertFalse(result['published'])
        self.assertFalse(result['externalEditorVerified'])
        self.assertEqual(run.call_count, 1)

    def test_pending_cut_cannot_execute_reviewed_draft(self):
        request, capabilities = self.draft_fixture(approved=False)
        with patch('jed_dispatch.runner.subprocess.run') as run:
            with self.assertRaisesRegex(ValueError, 'not approved'):
                dispatch(self.root, request, capabilities, execute=True)
        run.assert_not_called()

    def test_changed_overlay_cannot_execute_old_approved_cut(self):
        request, capabilities = self.draft_fixture()
        (self.root / 'work/renders/talking-head-overlay.mov').write_bytes(b'new overlay')
        with self.assertRaisesRegex(ValueError, 'dependency changed/missing'):
            dispatch(self.root, request, capabilities, execute=True)

    def test_approved_style_cannot_stand_in_for_concrete_cut(self):
        request, capabilities = self.draft_fixture(scope='visual_sample')
        with self.assertRaisesRegex(ValueError, 'concrete rough_cut'):
            dispatch(self.root, request, capabilities, execute=True)

    def test_isolated_draft_preparation_runs_without_approval_and_is_reused(self):
        request, capabilities = self.draft_fixture(approved=False)
        request['phase'] = 'prepare'
        request.pop('reviewState')
        request.pop('reviewCandidateId')
        with patch('jed_dispatch.runner.subprocess.run', side_effect=self.fake_draft) as run:
            first = dispatch(self.root, request, capabilities, execute=True)
            second = dispatch(self.root, request, capabilities, execute=True)
        self.assertEqual(first['status'], 'succeeded')
        self.assertFalse(first['humanApproved'])
        self.assertTrue(second['reused'])
        self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
