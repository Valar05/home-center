"""No-GPU regression checks for the Windows Ritsu repertoire runtime."""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = ROOT / "tools/campaigns/ritsu_voice_api_repertoire_v1.py"
CATALOG = ROOT / "functions/ritsu_voice_profiles.json"
WORKER = ROOT / "workers/ritsu_warm_ticket_worker.py"
SUPERVISOR = ROOT / "tools/campaigns/ritsu_warm_api_supervisor.py"
SENDER = ROOT / "tools/campaigns/ritsu_say_repertoire_v1.py"
PROFILES = {"normal", "whisper", "amused", "happy", "upset", "somber"}


class VoiceRuntimeContract(unittest.TestCase):
    def test_exact_six_registered_profiles_at_minus_one(self):
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(set(data["profiles"]), PROFILES)
        for name, profile in data["profiles"].items():
            self.assertEqual(profile["pitchSemitones"], -1, name)
            self.assertTrue(profile["referenceFile"].endswith(".wav"), name)
            self.assertTrue(profile["referenceText"].strip(), name)

    def test_formant_preserving_rubberband_and_not_librosa_shift(self):
        source = API.read_text(encoding="utf-8")
        self.assertIn("rubberband=pitch=", source)
        self.assertIn(":formant=preserved", source)
        self.assertNotRegex(source, r"\bclips\[0\]\s*=\s*librosa\.effects\.pitch_shift")

    def test_failed_job_does_not_poison_loaded_model(self):
        source = API.read_text(encoding="utf-8")
        self.assertIn("if model is None: state['model']='error'", source)
        self.assertIn("jobs[jid].update(state='failed'", source)

    def test_worker_and_sender_forward_profile_without_shell(self):
        worker = WORKER.read_text(encoding="utf-8")
        sender = SENDER.read_text(encoding="utf-8")
        self.assertIn("'--profile', profile", worker)
        self.assertIn("'speaker':a.profile", sender)
        self.assertIn("RITSU_WARM_ASMR_MAINTENANCE", worker)
        self.assertIn("AMBIGUOUS_PREVIOUS_ATTEMPT", worker)

    def test_supervisor_honors_pause_and_does_not_kill_processes(self):
        source = SUPERVISOR.read_text(encoding="utf-8")
        self.assertIn("if PAUSE.exists():", source)
        self.assertIn("if listening():", source)
        self.assertIn("CreateMutexW", source)
        self.assertNotIn("taskkill", source.lower())
        self.assertNotIn("TerminateProcess", source)


if __name__ == "__main__":
    unittest.main()
