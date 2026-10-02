"""Exercise the real encoder: transparent blue must become premultiplied RGB."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workers/draft-adapter'))
from replace_overlay_media import decoded_frame

module = importlib.util.spec_from_file_location('alpha_encoder', ROOT / 'scripts/encode-jianying-alpha.py')
encoder = importlib.util.module_from_spec(module)
module.loader.exec_module(encoder)


@unittest.skipUnless(shutil.which('ffmpeg'), 'Real alpha encoding requires FFmpeg')
class AlphaEncodingTest(unittest.TestCase):
    def test_actual_prores_keeps_mask_and_scales_blue_at_partial_alpha(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                'color=c=0x2d6bff@0.5:size=16x16:r=30,format=rgba',
                '-frames:v', '3', '-start_number', '0', str(directory / 'element-%03d.png')], check=True)
            output = encoder.encode(directory, directory / 'probe.mov')
            png = decoded_frame(directory / 'element-000.png', 0)
            self.assertTrue(0 < png[3] < 255, 'Probe must actually have partial alpha')
            # ProRes normalizes 8-bit PNG alpha by up to one code value. The
            # replacement gate compares to the accepted ProRes, not to PNG.
            control = directory / 'straight.mov'
            subprocess.run(['ffmpeg', '-v', 'error', '-framerate', '30',
                '-i', str(directory / 'element-%03d.png'), '-vf', 'format=gbrap16le,format=yuva444p10le',
                '-c:v', 'prores_ks', '-profile:v', '4', '-alpha_bits', '16', '-an', str(control)], check=True)
            original, actual = decoded_frame(control, 0), decoded_frame(output, 0)
            self.assertLessEqual(abs(png[3] - actual[3]), 1)
            self.assertEqual(actual[3::4], original[3::4])
            for offset in range(0, len(original), 4):
                for channel in range(3):
                    expected = original[offset + channel] * original[offset + 3] / 255
                    self.assertLessEqual(abs(actual[offset + channel] - expected), 2)
            with self.assertRaisesRegex(ValueError, 'never overwritten'):
                encoder.encode(directory, output)

    def test_missing_sequence_frame_is_rejected_before_encoding(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'element-000.png').write_bytes(b'unused')
            (directory / 'element-002.png').write_bytes(b'unused')
            with self.assertRaisesRegex(ValueError, 'complete zero-based'):
                encoder.encode(directory, directory / 'probe.mov')


if __name__ == '__main__':
    unittest.main()
