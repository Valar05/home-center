#!/usr/bin/env python3
"""Deterministic canaries for Ritsu primary-evidence closure."""
from __future__ import annotations

import unittest
from pathlib import Path

from ritsu_primary_gate import GAP, COMPLETE, PRIMARY, SUMMARY, audit_episode, audit_paths

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "fixtures/ritsu-continuity/episode-ledger.v0.jsonl"
ACTIVE = ROOT / "fixtures/ritsu-continuity/active-retrieval.v0.jsonl"
LATIN = "ritsu-latin-cassette-intercom-v1"
AGAIN = "latin-again-correction-v1"


def episode(*, sources=None):
    return {
        "record_type": "episode",
        "id": LATIN,
        "aliases": ["latin plays"],
        "summary_tier": "accepted_summary",
        "accepted_summary": (
            "Recurring Latin cassette/intercom ambience in Ritsu/Drew roleplay; "
            "the device became repetitive; Drew corrected Ritsu with AGAIN about the Latin; "
            "automatic Latin ambience was dropped."
        ),
        "primary_sources": list(sources or []),
    }


def correction(*, sources=None, edge="CORRECTED_BY"):
    return {
        "record_type": "correction",
        "id": AGAIN,
        "episode_id": LATIN,
        "edge": edge,
        "trigger": "AGAIN",
        "effect": "Automatic Latin ambience was dropped after Drew's correction.",
        "provenance_tier": "accepted_summary",
        "primary_sources": list(sources or []),
    }


class PrimaryGateTests(unittest.TestCase):
    def test_canonical_latin_fixture_stays_gap_until_both_primary_bindings_exist(self):
        result = audit_paths(LEDGER, ACTIVE, LATIN)
        self.assertEqual(GAP, result["status"])
        self.assertEqual(SUMMARY, result["provenance"])
        self.assertIn("episode_primary_transcript", result["missing"])
        self.assertIn(f"correction_primary:{AGAIN}", result["missing"])
        self.assertEqual("latin-primary-retrieval-v1", result["retrieval_id"])
        self.assertFalse(result["can_close_active_retrieval"])

    def test_text_without_stable_source_id_cannot_impersonate_primary(self):
        rows = [
            episode(sources=[{"source": "test", "text": "Exact Latin scene."}]),
            correction(sources=[{"source": "test", "text": "AGAIN."}]),
        ]
        result = audit_episode(rows, [], LATIN)
        self.assertEqual(GAP, result["status"])
        self.assertEqual(SUMMARY, result["provenance"])
        self.assertIn("episode_primary_transcript", result["missing"])
        self.assertIn(f"correction_primary:{AGAIN}", result["missing"])

    def test_episode_primary_alone_does_not_erase_missing_again_evidence(self):
        rows = [
            episode(sources=[{
                "source_id": "chatgpt:conversation:latin-episode:turn-42",
                "text": "Exact Latin scene.",
            }]),
            correction(),
        ]
        result = audit_episode(rows, [], LATIN)
        self.assertEqual(GAP, result["status"])
        self.assertEqual(PRIMARY, result["provenance"])
        self.assertNotIn("episode_primary_transcript", result["missing"])
        self.assertIn(f"correction_primary:{AGAIN}", result["missing"])
        self.assertFalse(result["can_close_active_retrieval"])

    def test_stable_episode_and_again_primary_bindings_close_gate(self):
        rows = [
            episode(sources=[{
                "source_id": "chatgpt:conversation:latin-episode:turn-42",
                "text": "Exact Latin scene.",
            }]),
            correction(sources=[{
                "source_id": "chatgpt:conversation:latin-again:turn-57",
                "text": "AGAIN.",
            }]),
        ]
        result = audit_episode(rows, [], LATIN)
        self.assertEqual(COMPLETE, result["status"])
        self.assertEqual(PRIMARY, result["provenance"])
        self.assertEqual([], result["missing"])
        self.assertTrue(result["can_close_active_retrieval"])

    def test_orphaned_correction_blocks_completion(self):
        rows = [
            episode(sources=[{
                "source_id": "chatgpt:conversation:latin-episode:turn-42",
                "text": "Exact Latin scene.",
            }]),
            correction(
                edge="ASSOCIATES",
                sources=[{
                    "source_id": "chatgpt:conversation:latin-again:turn-57",
                    "text": "AGAIN.",
                }],
            ),
        ]
        result = audit_episode(rows, [], LATIN)
        self.assertEqual(GAP, result["status"])
        self.assertIn(f"correction_edge_missing:{AGAIN}", result["missing"])

    def test_latest_closed_retrieval_suppresses_older_open_metadata(self):
        rows = [episode(), correction()]
        active = [
            {"id": "r1", "episode_id": LATIN, "status": "open"},
            {"id": "r1", "episode_id": LATIN, "status": "closed"},
        ]
        result = audit_episode(rows, active, LATIN)
        self.assertEqual(GAP, result["status"])
        self.assertNotIn("retrieval_id", result)


if __name__ == "__main__":
    unittest.main()
