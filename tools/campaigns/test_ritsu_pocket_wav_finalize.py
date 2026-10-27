"""Regression tests for known Pocket streaming WAV sentinel normalization."""
import struct
import unittest
from ritsu_pocket_wav_finalize import finalize_wav_bytes


def make_pcm(data_bytes=2400):
    payload = bytes([0x12, 0x34]) * (data_bytes // 2)
    header = bytearray(44)
    header[:4] = b"RIFF"
    struct.pack_into("<I", header, 4, 2_000_000_036)
    header[8:12] = b"WAVE"
    header[12:16] = b"fmt "
    struct.pack_into("<I", header, 16, 16)
    struct.pack_into("<HHIIHH", header, 20, 1, 1, 24_000, 48_000, 2, 16)
    header[36:40] = b"data"
    struct.pack_into("<I", header, 40, 2_000_000_000)
    return bytes(header) + payload


class StreamingWavTests(unittest.TestCase):
    def test_fixes_only_two_header_lengths(self):
        original = make_pcm()
        actual = finalize_wav_bytes(original)
        self.assertEqual(struct.unpack_from("<I", actual, 4)[0], len(original)-8)
        self.assertEqual(struct.unpack_from("<I", actual, 40)[0], len(original)-44)
        self.assertEqual(actual[44:], original[44:])
        self.assertEqual(actual[8:40], original[8:40])
        self.assertEqual(finalize_wav_bytes(actual), actual)

    def test_bad_size_alignment_refused(self):
        with self.assertRaises(ValueError):
            finalize_wav_bytes(make_pcm() + b"x")

    def test_unrecognized_stream_layout_preserved(self):
        wav = bytearray(make_pcm())
        wav[36:40] = b"LIST"
        self.assertEqual(finalize_wav_bytes(bytes(wav)), bytes(wav))

    def test_unrecognized_bytes_preserved(self):
        self.assertEqual(finalize_wav_bytes(b"not a wav"), b"not a wav")


if __name__ == "__main__":
    unittest.main()
