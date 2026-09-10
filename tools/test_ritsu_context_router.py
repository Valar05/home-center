#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "ritsu_context_router.py"
SPEC = importlib.util.spec_from_file_location("ritsu_context_router", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

EPISODE_ID = "ritsu-latin-cassette-intercom-v1"
SUMMARY = (
    "Recurring Latin cassette/intercom ambience in Ritsu/Drew roleplay; "
    "the device became repetitive; Drew corrected Ritsu with AGAIN about the Latin; "
    "automatic Latin ambience was dropped."
)


class RitsuContextRouterContract(unittest.TestCase):
    def setUp(self) -> None:
        self.router = mod.RitsuContextRouter()

    def test_latin_plays_recovers_episode_before_world_knowledge(self) -> None:
        r = self.router.resolve("Latin plays")
        self.assertEqual(r.status, "MATCH")
        self.assertEqual(r.episode_id, EPISODE_ID)
        self.assertEqual(r.provenance_tier, "accepted_summary")
        self.assertEqual(r.summary, SUMMARY)
        self.assertFalse(r.world_knowledge_allowed)
        self.assertTrue(r.seek_primary)
        self.assertTrue(any("dropped" in c for c in r.corrections))

    def test_latin_plays_normalizes_punctuation_without_broad_semantic_guessing(self) -> None:
        r = self.router.resolve("  LATIN—PLAYS!!! ")
        self.assertEqual(r.episode_id, EPISODE_ID)
        self.assertFalse(r.world_knowledge_allowed)

    def test_exact_wording_without_primary_is_continuity_gap_not_fabrication(self) -> None:
        r = self.router.resolve("Latin plays", exact_wording=True)
        self.assertEqual(r.status, "CONTINUITY_GAP")
        self.assertEqual(r.provenance_tier, "unknown")
        self.assertEqual(r.summary, SUMMARY)
        self.assertTrue(r.seek_primary)
        self.assertFalse(r.world_knowledge_allowed)

    def test_again_immediate_bind_reuses_attributable_episode(self) -> None:
        r = self.router.resolve("Again.", working_state={"last_episode_id": EPISODE_ID})
        self.assertEqual(r.status, "MATCH")
        self.assertEqual(r.episode_id, EPISODE_ID)
        self.assertTrue(any("dropped" in c for c in r.corrections))

    def test_again_without_working_state_refuses_to_guess(self) -> None:
        r = self.router.resolve("Again.")
        self.assertEqual(r.status, "NEEDS_WORKING_STATE")
        self.assertFalse(r.world_knowledge_allowed)

    def test_canonical_negative_material_never_leaks_into_positive_result(self) -> None:
        payload = json.dumps(self.router.resolve("Latin plays").to_dict())
        for forbidden in (
            "Plautus",
            "Roman theater",
            "Roman drama",
            "LISTEN / THINK / BUILD / STAY / TEASE",
        ):
            self.assertNotIn(forbidden, payload)

    def test_prior_canaries_are_reserved_for_existing_owners(self) -> None:
        for cue in (
            "Pasta apostrophe far",
            "vector noodle",
            "What survives translation?",
            "filthy clean",
        ):
            with self.subTest(cue=cue):
                r = self.router.resolve(cue)
                self.assertEqual(r.status, "DEFER_EXISTING_CONTINUITY")
                self.assertFalse(r.world_knowledge_allowed)
                self.assertIsNotNone(r.delegated_owner)

    def test_unknown_cue_does_not_trigger_cathedral_retrieval(self) -> None:
        r = self.router.resolve("penguin was camouflaged")
        self.assertEqual(r.status, "NO_LOCAL_MATCH")
        self.assertTrue(r.world_knowledge_allowed)

    def test_ambiguous_aliases_fail_closed(self) -> None:
        policy = ROOT / "config" / "ritsu-os.v0.json"
        records = [
            {
                "record_type": "episode",
                "id": "a",
                "aliases": ["same cue"],
                "summary_tier": "accepted_summary",
                "accepted_summary": "a",
            },
            {
                "record_type": "episode",
                "id": "b",
                "aliases": ["same cue"],
                "summary_tier": "accepted_summary",
                "accepted_summary": "b",
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ledger.jsonl"
            ledger.write_text(
                "\n".join(json.dumps(x) for x in records) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "ambiguous deterministic alias"):
                mod.RitsuContextRouter(policy, ledger)


if __name__ == "__main__":
    unittest.main()
