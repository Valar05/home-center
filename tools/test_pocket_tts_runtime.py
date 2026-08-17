#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import time
import unittest
import wave
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("pocket_tts_runtime.py")
SPEC = importlib.util.spec_from_file_location("pocket_tts_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
runtime_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime_module
SPEC.loader.exec_module(runtime_module)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_wav(path: Path, seconds: float = 0.08) -> None:
    rate = 8000
    frames = max(1, int(rate * seconds))
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(b"\0\0" * frames)


class FakeEngine:
    def __init__(self, delay: float = 0.06):
        self.delay = delay
        self.calls = 0

    def render(self, text, profile, output):
        self.calls += 1
        started = time.perf_counter()
        time.sleep(self.delay)
        write_wav(output)
        return {"renderMs": (time.perf_counter() - started) * 1000, **runtime_module.wav_metrics(output)}


class FakePlayer:
    def __init__(self, delay: float = 0.10):
        self.delay = delay
        self.starts = 0

    def play(self, path, control):
        self.starts += 1
        started = time.perf_counter()
        deadline = started + self.delay
        while time.perf_counter() < deadline:
            control.checkpoint()
            time.sleep(0.005)
        return {"playMs": (time.perf_counter() - started) * 1000, "glitches": 0}


class FailOncePlayer(FakePlayer):
    def play(self, path, control):
        self.starts += 1
        if self.starts == 1:
            raise runtime_module.PocketTtsError("deterministic playback failure")
        return super().play(path, control)


class PocketRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        model = self.root / "model.bin"
        voices = self.root / "voices.bin"
        model.write_bytes(b"model")
        voices.write_bytes(b"voices")
        registry_path = self.root / "voices.json"
        registry_path.write_text(json.dumps({
            "schema": runtime_module.REGISTRY_SCHEMA,
            "profiles": [{
                "id": "companion-test",
                "role": "companion",
                "engine": "kokoro-onnx",
                "voice": "af_test",
                "modelPath": str(model),
                "modelSha256": file_hash(model),
                "voicesPath": str(voices),
                "voicesSha256": file_hash(voices),
                "license": "test-only",
                "source": "https://example.invalid/test-owned-fixture",
                "language": "en-us"
            }]
        }), "utf-8")
        self.registry = runtime_module.VoiceRegistry(registry_path)

    def tearDown(self):
        self.temp.cleanup()

    def make_runtime(self, engine=None, player=None):
        engine = engine or FakeEngine()
        pool = runtime_module.EnginePool({"kokoro-onnx": lambda: engine})
        return runtime_module.PocketTtsRuntime(
            self.registry,
            self.root / ("state-" + str(time.time_ns())),
            engine_pool=pool,
            player=player or FakePlayer(),
        ), engine

    def test_normalizer_and_chunker_are_deterministic_and_lossless(self):
        source = "  One\tthing.\nThen another thing!  " + ("A deliberately longer sentence follows. " * 4)
        normalized = runtime_module.normalize_text(source)
        self.assertTrue(normalized.startswith("One thing. Then another thing!"))
        chunks = runtime_module.chunk_text(normalized, 80)
        self.assertEqual("".join(chunks), normalized)
        self.assertGreater(len(chunks), 1)

    def test_speak_streams_before_full_render_and_measures_ttfa(self):
        runtime, engine = self.make_runtime()
        text = "First sentence arrives with enough detail to breathe. " * 7
        runtime.start("speak", text, "companion-test", max_chars=80)
        receipt = runtime.wait(5)
        self.assertEqual(receipt["status"], "completed")
        self.assertGreater(receipt["ttfaMs"], 0)
        self.assertLess(receipt["ttfaMs"], receipt["totalMs"])
        self.assertTrue(receipt["firstPlaybackBeforeRenderComplete"])
        self.assertEqual(receipt["glitches"], 0)
        self.assertFalse(receipt["cloudSpeechAllowed"])
        self.assertTrue(receipt["workers"]["synthesis"]["alive"])
        self.assertTrue(receipt["workers"]["playback"]["alive"])
        self.assertEqual(engine.calls, receipt["textChunks"])

    def test_second_speak_is_an_offline_cache_hit(self):
        shared_engine = FakeEngine(0.01)
        pool = runtime_module.EnginePool({"kokoro-onnx": lambda: shared_engine})
        state = self.root / "cache-state"
        first = runtime_module.PocketTtsRuntime(self.registry, state, pool, FakePlayer(0.01))
        text = "Cache me without asking a cloud to remember me."
        first.start("speak", text, "companion-test")
        first_receipt = first.wait(5)
        self.assertEqual(first_receipt["cacheHits"], 0)
        calls = shared_engine.calls

        second = runtime_module.PocketTtsRuntime(self.registry, state, pool, FakePlayer(0.01))
        second.start("speak", text, "companion-test")
        second_receipt = second.wait(5)
        self.assertEqual(second_receipt["cacheHitRatio"], 1.0)
        self.assertEqual(shared_engine.calls, calls)
        self.assertFalse(second_receipt["hostedDefaultMouth"])

    def test_stop_interrupts_active_playback_and_status_is_durable(self):
        runtime, _ = self.make_runtime(engine=FakeEngine(0.01), player=FakePlayer(1.0))
        runtime.start("speak", "Stop this sentence while it is physically playing.", "companion-test")
        deadline = time.monotonic() + 2
        while runtime.status()["ttfaMs"] is None and time.monotonic() < deadline:
            time.sleep(0.01)
        runtime.stop()
        receipt = runtime.wait(3)
        self.assertEqual(receipt["status"], "stopped")
        status_path = runtime.state_root / "status.json"
        self.assertEqual(json.loads(status_path.read_text("utf-8"))["status"], "stopped")

    def test_registry_rejects_hosted_or_unlicensed_voice(self):
        bad = self.root / "bad.json"
        bad.write_text(json.dumps({
            "schema": runtime_module.REGISTRY_SCHEMA,
            "profiles": [{"id": "cloud-bad", "role": "utility", "engine": "hosted", "voice": "x"}]
        }), "utf-8")
        with self.assertRaises(runtime_module.PocketTtsError):
            runtime_module.VoiceRegistry(bad)

    def test_terminal_playback_failure_stops_both_workers_before_receipt(self):
        engine = FakeEngine(0.04)
        player = FailOncePlayer(0.01)
        runtime, _ = self.make_runtime(engine=engine, player=player)
        text = "A bounded failure must stop later sound and later rendering. " * 12
        runtime.start("speak", text, "companion-test", max_chars=80)
        receipt = runtime.wait(5)
        self.assertEqual(receipt["status"], "failed")
        calls_at_terminal = engine.calls
        plays_at_terminal = player.starts
        time.sleep(0.25)
        self.assertEqual(engine.calls, calls_at_terminal)
        self.assertEqual(player.starts, plays_at_terminal)
        self.assertEqual(player.starts, 1)
        self.assertEqual(json.loads((runtime.state_root / "status.json").read_text("utf-8"))["status"], "failed")


if __name__ == "__main__":
    unittest.main()
