#!/usr/bin/env python3
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("fortress_multimedia.py")
spec = importlib.util.spec_from_file_location("fortress_multimedia", MODULE_PATH)
fm = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fm)


class FortressMultimediaTest(unittest.TestCase):
    def test_choose_lanes_prefers_phone_when_capable_and_cool(self):
        device = {
            "commands": {"ffmpeg": "/bin/ffmpeg", "godot4": "/bin/godot4", "blender": "/bin/blender"},
            "media": {"encoderMarkers": ["mediacodec", "h264"]},
            "thermal": {"maxCelsius": 39.0},
        }
        cfg = {"policy": {"cloudEscalation": False}}
        lanes = fm.choose_lanes(device, cfg)
        self.assertTrue(lanes["phoneMedia"]["enabled"])
        self.assertTrue(lanes["phoneMedia"]["hardwareCodecDetected"])
        self.assertEqual(lanes["game"]["preferred"], "phone")
        self.assertEqual(lanes["blender"]["preferred"], "phone")
        self.assertFalse(lanes["cloudEscalationAllowed"])

    def test_hot_device_spills_heavy_work_off_phone(self):
        device = {
            "commands": {"ffmpeg": "/bin/ffmpeg", "godot": "/bin/godot", "blender": "/bin/blender"},
            "media": {"encoderMarkers": ["mediacodec"]},
            "thermal": {"maxCelsius": 48.0},
        }
        lanes = fm.choose_lanes(device, {"policy": {"cloudEscalation": False}})
        self.assertTrue(lanes["phoneLocal"]["throttled"])
        self.assertFalse(lanes["phoneMedia"]["enabled"])
        self.assertEqual(lanes["game"]["preferred"], "fleet")
        self.assertEqual(lanes["blender"]["preferred"], "fleet-gpu")

    def test_no_blender_does_not_fake_phone_gpu_blender(self):
        device = {
            "commands": {"ffmpeg": "/bin/ffmpeg", "godot": None, "godot4": None, "blender": None},
            "media": {"encoderMarkers": []},
            "thermal": {"maxCelsius": None},
        }
        lanes = fm.choose_lanes(device, {"policy": {"cloudEscalation": False}})
        self.assertEqual(lanes["blender"]["preferred"], "fleet-gpu")
        self.assertIsNone(lanes["blender"]["phoneExecutable"])

    def test_registry_has_all_combined_arms_organs(self):
        cfg = json.loads((Path(__file__).parents[1] / "config/fortress-multimedia.json").read_text(encoding="utf-8"))
        self.assertEqual(set(cfg["organs"]), {"venice", "media", "blender", "game"})
        self.assertFalse(cfg["policy"]["cloudEscalation"])
        self.assertFalse(cfg["policy"]["rawShell"])

    def test_unknown_recipe_fails_closed(self):
        with mock.patch.object(fm, "load_config", return_value={"recipes": {"device-profile": {"action": "profile"}}}):
            result = fm.run_recipe("make-me-anything")
        self.assertFalse(result["ok"])
        self.assertIn("unknown recipe", result["blocked"])


if __name__ == "__main__":
    unittest.main()
