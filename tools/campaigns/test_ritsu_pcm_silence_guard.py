"""Synthetic PCM-only offline tests: no voice synthesis or phone operation."""
from array import array
import importlib.util
from pathlib import Path
import tempfile
import unittest
import wave

spec = importlib.util.spec_from_file_location("guard", Path(__file__).with_name("ritsu_pcm_silence_guard.py"))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
RATE = 24000


def samples(value, millis):
    return array("h", [value] * (RATE * millis // 1000)).tobytes()


class SilenceGuardTests(unittest.TestCase):
    def test_suffix_and_tail_preserved_exactly(self):
        original = samples(0, 550) + samples(7200, 770) + samples(0, 120)
        self.assertEqual(guard.decide(original)["safeCandidateCutMs"], 350)
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "input.wav"
            dest = Path(td) / "out.wav"
            guard.pcm_write_new(source, original)
            self.assertEqual(guard.inspect(source)["leadingQuietMs"], 550)
            result = guard.candidate(source, dest)
            self.assertEqual(guard.pcm_read(source), original)
            self.assertEqual(guard.pcm_read(dest), original[350 * RATE * 2 // 1000:])
            self.assertTrue(guard.pcm_read(dest).endswith(samples(0, 120)))
            self.assertTrue(result["auditionRequired"])
            self.assertTrue(result["preservedTrailingSamples"])
            with self.assertRaises(FileExistsError):
                guard.candidate(source, dest)

    def test_soft_initial_sound_is_preserved(self):
        soft_onset = samples(0, 150) + samples(110, 220) + samples(5000, 500)
        self.assertEqual(guard.decide(soft_onset)["safeCandidateCutMs"], 0)

    def test_all_silent_or_short_audio_never_cut(self):
        self.assertEqual(guard.decide(samples(0, 2000))["safeCandidateCutMs"], 0)
        self.assertEqual(guard.decide(samples(0, 300))["safeCandidateCutMs"], 0)

    def test_maximum_cut_protects_ending(self):
        audio = samples(0, 2000) + samples(5000, 1000) + samples(0, 2000)
        result = guard.decide(audio)
        self.assertEqual(result["safeCandidateCutMs"], 800)
        self.assertEqual(result["leadingQuietMs"], 2000)

    def test_dither_makes_strict_zero_but_louder_speech_starts_later(self):
        # Generated audio may contain low-level nonzero PCM before speech.
        # The old conservative cut detector correctly refuses to cut it.
        pcm = samples(110, 550) + samples(7000, 900)
        self.assertEqual(guard.decide(pcm)["leadingQuietMs"], 0)
        self.assertEqual(guard.decide(pcm)["safeCandidateCutMs"], 0)
        profile = guard.energy_profile(pcm)
        self.assertEqual(profile["candidateOnsetMsByThreshold"]["minus40dB"], 550)
        self.assertEqual(profile["candidateOnsetMsByThreshold"]["adaptive"], 550)
        self.assertTrue(profile["noAutoCut"])

    def test_instant_onset_and_all_quiet_diagnostics(self):
        voiced = guard.energy_profile(samples(6000, 800))
        self.assertEqual(voiced["candidateOnsetMsByThreshold"]["minus30dB"], 0)
        quiet = guard.energy_profile(samples(0, 800))
        self.assertIsNone(quiet["candidateOnsetMsByThreshold"]["minus50dB"])

    def test_unknown_audio_format_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "wrong.wav"
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(44100)
                wav.writeframes(b"\0"*1000)
            with self.assertRaises(ValueError):
                guard.pcm_read(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
