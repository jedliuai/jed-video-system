"""Text-edge replacement cannot apply unaccepted or visually different assets."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workers/draft-adapter'))
sys.path.insert(0, str(ROOT / 'plugins/jed-video-system/src'))
import replace_overlay_media as replacement
from jed_review import new_state, record_decision, register_candidate, request_review


class OverlayAcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.image = self.directory / 'sample.png'
        self.alpha = self.directory / 'sample.mov'
        self.image.write_bytes(b'accepted-image')
        self.alpha.write_bytes(b'accepted-alpha')
        state = new_state('replacement-test')
        def candidate(key, path, scope, kind, operations, dependencies):
            return dict(candidateId=key, scope=scope, scopeId='talking-head-edge-design-direction',
                revision='r1', contentRevision='frame-172', patternId='fine-edge', operationVersion='v1',
                artifactDigest=hashlib.sha256(path.read_bytes()).hexdigest(), artifactKind=kind,
                locator=str(path), coverage='single', operations=operations, dependsOn=dependencies)
        state = register_candidate(state, candidate('alpha', self.alpha, 'technical_preparation', 'video', ['probe_media'], []))
        state = register_candidate(state, candidate('image', self.image, 'visual_sample', 'image', ['choose_fine_white_edge_design'], ['alpha']))
        self.pending = request_review(state, 'image', 'Choose this rendered design')
        self.request_id = self.pending['requests'][0]['requestId']
        self.approved = record_decision(self.pending, self.request_id, 'approved', 'B', 'test-operator')
        self.state_path = self.directory / 'review.json'
        self.spec = dict(reviewState=str(self.state_path), approvalRequestId=self.request_id, candidateId='image',
            acceptedAlphaCandidateId='alpha', matchFrame=172, replacements=[{'path': str(self.directory / 'new.mov')}])

    def tearDown(self):
        self.temporary.cleanup()

    def save(self, state):
        self.state_path.write_text(json.dumps(state), encoding='utf-8')

    def test_pending_design_does_not_allow_replacement(self):
        self.save(self.pending)
        with patch.object(replacement, 'decoded_frame') as decode:
            with self.assertRaisesRegex(ValueError, 'explicit acceptance'):
                replacement.verify_acceptance(self.spec)
            decode.assert_not_called()

    def test_changed_accepted_image_does_not_allow_replacement(self):
        self.save(self.approved)
        self.image.write_bytes(b'different-image')
        with self.assertRaisesRegex(ValueError, 'Accepted image changed'):
            replacement.verify_acceptance(self.spec)

    def test_different_rendered_edge_does_not_allow_replacement(self):
        self.save(self.approved)
        with patch.object(replacement, 'decoded_frame', side_effect=[b'new-style', b'accepted-style']):
            with self.assertRaisesRegex(ValueError, 'does not reproduce'):
                replacement.verify_acceptance(self.spec)

    def test_matching_accepted_frame_keeps_editor_verification_pending(self):
        self.save(self.approved)
        with patch.object(replacement, 'decoded_frame', return_value=b'same-decoded-frame'):
            result = replacement.verify_acceptance(self.spec)
        self.assertTrue(result['decodedAlphaFrameMatches'])
        self.assertFalse(result['targetEditorVerified'])

    def test_transport_option_cannot_reinterpret_an_accepted_stroke_design(self):
        self.save(self.approved)
        with patch.object(replacement, 'decoded_frame', return_value=bytes([45, 107, 255, 255])):
            with self.assertRaisesRegex(ValueError, 'accepted no-edge design'):
                replacement.verify_acceptance({**self.spec, 'alphaTransport': 'premultiplied-rgb'})

    def test_unknown_transport_cannot_bypass_frame_matching(self):
        self.save(self.approved)
        with patch.object(replacement, 'decoded_frame', return_value=bytes([45, 107, 255, 255])):
            with self.assertRaisesRegex(ValueError, 'Unsupported alpha transport'):
                replacement.verify_acceptance({**self.spec, 'alphaTransport': 'ignore-colors'})

    def test_absolute_material_path_cannot_redirect_copy_to_source_draft(self):
        with self.assertRaisesRegex(ValueError, 'relative to the draft copy'):
            replacement.relative_media(str(self.alpha.resolve()))

    def test_parent_material_path_cannot_escape_copy(self):
        with self.assertRaisesRegex(ValueError, 'relative to the draft copy'):
            replacement.relative_media('../source/material.mov')


class AlphaTransportTest(unittest.TestCase):
    def test_matching_premultiplied_colors_preserve_alpha(self):
        straight = bytes([45, 107, 255, 128, 8, 18, 36, 255, 0, 0, 0, 0])
        actual = bytes([23, 54, 128, 128, 8, 18, 36, 255, 0, 0, 0, 0])
        proof = replacement.compare_premultiplied_rgba(actual, straight)
        self.assertTrue(proof['alphaMaskMatches'])

    def test_straight_blue_mislabelled_as_premultiplied_is_rejected(self):
        straight = bytes([45, 107, 255, 64])
        with self.assertRaisesRegex(ValueError, 'visible colors'):
            replacement.compare_premultiplied_rgba(straight, straight)

    def test_white_fringe_cannot_hide_in_large_transparent_area(self):
        straight = bytes([45, 107, 255, 64]) + bytes(40000)
        actual = bytes([245, 245, 255, 64]) + bytes(40000)
        with self.assertRaisesRegex(ValueError, 'visible colors'):
            replacement.compare_premultiplied_rgba(actual, straight)

    def test_changed_mask_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'transparency mask'):
            replacement.compare_premultiplied_rgba(bytes([0, 0, 0, 128]), bytes([0, 0, 0, 255]))

    def test_empty_visual_frame_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'visible colors'):
            replacement.compare_premultiplied_rgba(bytes(4), bytes(4))


if __name__ == '__main__':
    unittest.main()
