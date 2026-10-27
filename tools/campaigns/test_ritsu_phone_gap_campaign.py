#!/usr/bin/env python3
"""Deterministic, offline tests for the Ritsu Termux audio-gap campaign.

These tests validate parsing and bounded evidence semantics, not real phone
playback, deployment, or user-heard completeness.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).with_name("ritsu_phone_gap_campaign.py")
spec = importlib.util.spec_from_file_location("ritsu_gap_campaign", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def event(kind, seq, ms):
    return {"event": kind, "seq": seq, "deviceMonotonicMs": ms,
            "relayId": "a" * 24}

class GapCampaignTests(unittest.TestCase):
    def test_exact_order_and_gap(self):
        rows = [
            {"event": "playback_started", "seq": 1, "ms": 1000},
            {"event": "playback_finished", "seq": 1, "ms": 3100},
            {"event": "playback_started", "seq": 2, "ms": 3750},
            {"event": "playback_finished", "seq": 2, "ms": 5900},
            {"event": "playback_started", "seq": 3, "ms": 6130},
            {"event": "playback_finished", "seq": 3, "ms": 8300},
        ]
        answer = mod.trace_report(rows)
        self.assertEqual(answer["completedPairs"], 3)
        self.assertEqual(answer["gaps"], [
            {"from": 1, "to": 2, "gapSeconds": 0.65},
            {"from": 2, "to": 3, "gapSeconds": 0.23},
        ])
        self.assertEqual(answer["medianGapSeconds"], 0.44)
        self.assertEqual(answer["maxGapSeconds"], 0.65)

    def test_missing_and_corrupt_trace_do_not_invent_events(self):
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / "trace.jsonl"
            with mock.patch.object(mod, "TRACE", trace):
                self.assertEqual(mod.events(), ([], "TRACE_MISSING"))
                trace.write_text(json.dumps(event("playback_started", 1, 1000))
                                 + "\nnot valid json\n", encoding="utf-8")
                rows, status = mod.events()
                self.assertEqual(len(rows), 1)
                self.assertEqual(status, "PARSE_WARNINGS_1")

    def test_no_fictitious_pause_without_end_event(self):
        rows = [
            {"event": "playback_started", "seq": 1, "ms": 1000},
            {"event": "playback_started", "seq": 2, "ms": 2500},
            {"event": "playback_finished", "seq": 2, "ms": 4600},
        ]
        self.assertEqual(mod.trace_report(rows)["gaps"], [])

    def test_no_secret_paths_inspected(self):
        # Only installed source and WAV metadata; never read the relay token,
        # host, private audio transcript, or authentication headers.
        self.assertNotIn('relay-token.txt', SCRIPT.read_text(encoding="utf-8"))
        self.assertNotIn('ritsu-api-token.txt', SCRIPT.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
