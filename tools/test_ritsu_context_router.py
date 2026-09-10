#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "ritsu_context_router.py"
SPEC = importlib.util.spec_from_file_location("ritsu_context_router", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

EPISODE_ID = "ritsu-latin-cassette-intercom-v1"
RETRIEVAL_ID = "latin-primary-retrieval-v1"
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
        self.assertEqual(r.content, SUMMARY)
        self.assertFalse(r.world_knowledge_allowed)
        self.assertTrue(r.seek_primary)
        self.assertTrue(any("dropped" in c for c in r.corrections))
        self.assertIsNotNone(r.active_retrieval)
        self.assertEqual(r.active_retrieval["id"], RETRIEVAL_ID)
        self.assertEqual(r.active_retrieval["status"], "open")
        self.assertEqual(r.active_retrieval["required_provenance"], "primary_transcript")

    def test_latin_plays_normalizes_punctuation_without_broad_semantic_guessing(self) -> None:
        r = self.router.resolve("  LATIN—PLAYS!!! ")
        self.assertEqual(r.episode_id, EPISODE_ID)
        self.assertFalse(r.world_knowledge_allowed)

    def test_natural_sentence_embeds_known_multiword_episode_alias(self) -> None:
        r = self.router.resolve("Can we go back to Latin plays for a second?")
        self.assertEqual(r.status, "MATCH")
        self.assertEqual(r.episode_id, EPISODE_ID)
        self.assertEqual(r.matched_cue, "latin plays")
        self.assertEqual(r.provenance_tier, "accepted_summary")
        self.assertTrue(any("dropped" in c for c in r.corrections))
        self.assertFalse(r.world_knowledge_allowed)

    def test_embedded_alias_matching_respects_token_boundaries(self) -> None:
        r = self.router.resolve("latin playscape")
        self.assertEqual(r.status, "NO_LOCAL_MATCH")
        self.assertTrue(r.world_knowledge_allowed)

    def test_weak_alias_inside_generic_sentence_does_not_hijack_world_knowledge(self) -> None:
        r = self.router.resolve("What is the Latin word for sleep?")
        self.assertEqual(r.status, "NO_LOCAL_MATCH")
        self.assertTrue(r.world_knowledge_allowed)

    def test_exact_wording_can_use_weak_alias_but_still_requires_primary(self) -> None:
        r = self.router.resolve("What did Ritsu say about the Latin?")
        self.assertEqual(r.status, "CONTINUITY_GAP")
        self.assertEqual(r.episode_id, EPISODE_ID)
        self.assertEqual(r.matched_cue, "the latin")
        self.assertEqual(r.required_provenance, "primary_transcript")
        self.assertFalse(r.world_knowledge_allowed)
        self.assertEqual(r.active_retrieval["id"], RETRIEVAL_ID)

    def test_exact_wording_without_primary_is_continuity_gap_not_fabrication(self) -> None:
        r = self.router.resolve("Latin plays", exact_wording=True)
        self.assertEqual(r.status, "CONTINUITY_GAP")
        self.assertEqual(r.provenance_tier, "accepted_summary")
        self.assertEqual(r.content, SUMMARY)
        self.assertEqual(r.required_provenance, "primary_transcript")
        self.assertTrue(r.seek_primary)
        self.assertFalse(r.world_knowledge_allowed)
        self.assertEqual(r.active_retrieval["id"], RETRIEVAL_ID)
        self.assertIn("Latin plays", r.active_retrieval["deterministic_queries"])
        self.assertIn("Drew AGAIN correction evidence", r.active_retrieval["closure_requires"])

    def test_active_retrieval_has_complete_five_pass_review(self) -> None:
        record = self.router.active_retrieval_by_episode[EPISODE_ID]
        self.assertEqual(tuple(record["review"]), mod.REVIEW_PASSES)
        for name in mod.REVIEW_PASSES:
            self.assertTrue(record["review"][name].strip())

    def test_active_retrieval_cannot_close_on_summary_or_adjacent_evidence(self) -> None:
        review = {name: f"pass {name}" for name in mod.REVIEW_PASSES}
        false_closure = {
            "record_type": "active_retrieval",
            "id": "false-close",
            "episode_id": EPISODE_ID,
            "status": "closed",
            "required_provenance": "primary_transcript",
            "review": review,
        }
        with tempfile.TemporaryDirectory() as td:
            active = Path(td) / "active.jsonl"
            active.write_text(json.dumps(false_closure) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot close without stable primary transcript"):
                mod.RitsuContextRouter(
                    ROOT / "config" / "ritsu-os.v0.json",
                    ROOT / "fixtures" / "ritsu-continuity" / "episode-ledger.v0.jsonl",
                    active,
                )

    def test_again_immediate_bind_reuses_attributable_episode(self) -> None:
        r = self.router.resolve("Again.", working_state={"last_episode_id": EPISODE_ID})
        self.assertEqual(r.status, "MATCH")
        self.assertEqual(r.episode_id, EPISODE_ID)
        self.assertTrue(any("dropped" in c for c in r.corrections))

    def test_ritzu_again_binds_current_target_before_older_episode(self) -> None:
        target = {
            "target_id": "image-critique-42",
            "target_type": "image_critique",
            "owner": "Ritzu",
        }
        r = self.router.resolve(
            "Ritzu again.",
            working_state={"current_target": target, "last_episode_id": EPISODE_ID},
        )
        self.assertEqual(r.status, "BOUND_WORKING_TARGET")
        self.assertEqual(r.route, "immediate_bind")
        self.assertIsNone(r.episode_id)
        self.assertEqual(r.bound_target, target)
        self.assertFalse(r.world_knowledge_allowed)

    def test_named_again_refuses_actor_mismatched_current_target(self) -> None:
        r = self.router.resolve(
            "Ritsu again.",
            working_state={
                "current_target": {
                    "target_id": "repair-7",
                    "target_type": "repair",
                    "owner": "Tetsuya",
                },
                "last_episode_id": EPISODE_ID,
            },
        )
        self.assertEqual(r.status, "NEEDS_WORKING_STATE")
        self.assertIsNone(r.episode_id)
        self.assertIsNone(r.bound_target)
        self.assertFalse(r.world_knowledge_allowed)

    def test_plain_again_can_bind_current_target_without_actor_guess(self) -> None:
        target = {"target_id": "repair-7", "target_type": "repair", "owner": "Tetsuya"}
        r = self.router.resolve("Again.", working_state={"current_target": target})
        self.assertEqual(r.status, "BOUND_WORKING_TARGET")
        self.assertEqual(r.bound_target, target)
        self.assertFalse(r.world_knowledge_allowed)

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

    def test_exact_wording_marker_can_embed_known_alias_without_semantic_search(self) -> None:
        r = self.router.resolve("What did Ritsu say about Latin plays?")
        self.assertEqual(r.status, "CONTINUITY_GAP")
        self.assertEqual(r.episode_id, EPISODE_ID)
        self.assertEqual(r.required_provenance, "primary_transcript")

    def test_primary_transcript_outranks_accepted_summary_when_stably_bound(self) -> None:
        policy = ROOT / "config" / "ritsu-os.v0.json"
        records = [{
            "record_type": "episode",
            "id": "primary",
            "aliases": ["primary cue"],
            "summary_tier": "accepted_summary",
            "accepted_summary": "summary only",
            "primary_sources": [{
                "source_id": "chatgpt:conversation:test:turn-42",
                "text": "PRIMARY WORDING",
            }],
        }]
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ledger.jsonl"
            ledger.write_text("\n".join(json.dumps(x) for x in records) + "\n", encoding="utf-8")
            router = mod.RitsuContextRouter(policy, ledger)
            r = router.resolve("primary cue", exact_wording=True)
            self.assertEqual(r.status, "MATCH")
            self.assertEqual(r.provenance_tier, "primary_transcript")
            self.assertEqual(r.content, "PRIMARY WORDING")
            self.assertFalse(r.seek_primary)
            self.assertIsNone(r.active_retrieval)

    def test_anonymous_text_cannot_impersonate_primary_transcript(self) -> None:
        policy = ROOT / "config" / "ritsu-os.v0.json"
        records = [{
            "record_type": "episode",
            "id": "anonymous-primary",
            "aliases": ["anonymous primary cue"],
            "summary_tier": "accepted_summary",
            "accepted_summary": "grounded summary",
            "primary_sources": [{"source": "clipboard", "text": "UNBOUND WORDING"}],
        }]
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ledger.jsonl"
            ledger.write_text("\n".join(json.dumps(x) for x in records) + "\n", encoding="utf-8")
            router = mod.RitsuContextRouter(policy, ledger)
            r = router.resolve("anonymous primary cue", exact_wording=True)
            self.assertEqual(r.status, "CONTINUITY_GAP")
            self.assertEqual(r.provenance_tier, "accepted_summary")
            self.assertEqual(r.content, "grounded summary")
            self.assertEqual(r.required_provenance, "primary_transcript")
            self.assertTrue(r.seek_primary)
            self.assertNotEqual(r.content, "UNBOUND WORDING")

    def test_closed_retrieval_requires_primary_correction_binding_too(self) -> None:
        policy = ROOT / "config" / "ritsu-os.v0.json"
        records = [
            {
                "record_type": "episode",
                "id": "close-check",
                "aliases": ["close check"],
                "accepted_summary": "summary",
                "summary_tier": "accepted_summary",
                "primary_sources": [{
                    "source_id": "chatgpt:conversation:test:episode",
                    "text": "PRIMARY EPISODE",
                }],
            },
            {
                "record_type": "correction",
                "id": "close-check-again",
                "episode_id": "close-check",
                "edge": "CORRECTED_BY",
                "effect": "Changed meaning.",
                "primary_sources": [],
            },
        ]
        active_record = {
            "record_type": "active_retrieval",
            "id": "close-check-retrieval",
            "episode_id": "close-check",
            "status": "closed",
            "required_provenance": "primary_transcript",
            "review": {name: f"pass {name}" for name in mod.REVIEW_PASSES},
        }
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ledger.jsonl"
            active = Path(td) / "active.jsonl"
            ledger.write_text("\n".join(json.dumps(x) for x in records) + "\n", encoding="utf-8")
            active.write_text(json.dumps(active_record) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stable primary transcript and correction evidence"):
                mod.RitsuContextRouter(policy, ledger, active)

    def test_ambiguous_aliases_fail_closed(self) -> None:
        policy = ROOT / "config" / "ritsu-os.v0.json"
        records = [
            {"record_type": "episode", "id": "a", "aliases": ["same cue"],
             "summary_tier": "accepted_summary", "accepted_summary": "a"},
            {"record_type": "episode", "id": "b", "aliases": ["same cue"],
             "summary_tier": "accepted_summary", "accepted_summary": "b"},
        ]
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ledger.jsonl"
            ledger.write_text("\n".join(json.dumps(x) for x in records) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ambiguous deterministic alias"):
                mod.RitsuContextRouter(policy, ledger)

    def test_ambiguous_embedded_aliases_fail_closed_without_world_fallback(self) -> None:
        policy = ROOT / "config" / "ritsu-os.v0.json"
        records = [
            {"record_type": "episode", "id": "a", "aliases": ["alpha cue"],
             "embedded_aliases": ["alpha cue"],
             "summary_tier": "accepted_summary", "accepted_summary": "a"},
            {"record_type": "episode", "id": "b", "aliases": ["beta cue"],
             "embedded_aliases": ["beta cue"],
             "summary_tier": "accepted_summary", "accepted_summary": "b"},
        ]
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ledger.jsonl"
            ledger.write_text("\n".join(json.dumps(x) for x in records) + "\n", encoding="utf-8")
            router = mod.RitsuContextRouter(policy, ledger)
            r = router.resolve("Can we compare alpha cue with beta cue?")
            self.assertEqual(r.status, "AMBIGUOUS_LOCAL_MATCH")
            self.assertEqual(r.candidate_episode_ids, ("a", "b"))
            self.assertIsNone(r.content)
            self.assertFalse(r.world_knowledge_allowed)


if __name__ == "__main__":
    unittest.main()
