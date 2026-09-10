#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

ROUTER_PATH = TOOLS / "ritsu_context_router.py"
GATE_PATH = TOOLS / "ritsu_surface_gate.py"

router_spec = importlib.util.spec_from_file_location("ritsu_context_router", ROUTER_PATH)
assert router_spec and router_spec.loader
router_mod = importlib.util.module_from_spec(router_spec)
sys.modules[router_spec.name] = router_mod
router_spec.loader.exec_module(router_mod)

gate_spec = importlib.util.spec_from_file_location("ritsu_surface_gate", GATE_PATH)
assert gate_spec and gate_spec.loader
gate_mod = importlib.util.module_from_spec(gate_spec)
sys.modules[gate_spec.name] = gate_mod
gate_spec.loader.exec_module(gate_mod)

EPISODE_ID = "ritsu-latin-cassette-intercom-v1"


class RitsuSurfaceGateContract(unittest.TestCase):
    def setUp(self) -> None:
        self.router = router_mod.RitsuContextRouter()
        self.gate = gate_mod.RitsuSurfaceGate()

    def decide(self, utterance: str, **kwargs):
        return self.gate.decide(self.router.resolve(utterance, **kwargs))

    def assert_ritsu_first(self, decision) -> None:
        self.assertEqual(decision.speaker, "Ritsu")
        self.assertFalse(decision.retrieval_narration_allowed)
        self.assertFalse(decision.identity_explanation_allowed)
        payload = json.dumps(decision.to_dict()).casefold()
        for forbidden_key in (
            '"reason"',
            '"active_retrieval"',
            '"deterministic_queries"',
            '"search_order"',
            '"delegated_owner"',
        ):
            self.assertNotIn(forbidden_key, payload)

    def test_latin_plays_reaches_ritsu_with_episode_and_again_correction(self) -> None:
        decision = self.decide("Latin plays")
        self.assert_ritsu_first(decision)
        self.assertTrue(decision.emit)
        self.assertEqual(decision.mode, "answer")
        ctx = decision.render_context
        self.assertEqual(ctx["episode_id"], EPISODE_ID)
        self.assertEqual(ctx["provenance_tier"], "accepted_summary")
        self.assertFalse(ctx["world_knowledge_allowed"])
        self.assertTrue(ctx["seek_primary"])
        self.assertTrue(any("dropped" in item for item in ctx["corrections"]))
        for forbidden in ("Plautus", "Roman theater", "LISTEN / THINK / BUILD / STAY / TEASE"):
            self.assertNotIn(forbidden, json.dumps(ctx))

    def test_missing_primary_surfaces_gap_through_ritsu_not_lookup_narration(self) -> None:
        decision = self.decide("Latin plays", exact_wording=True)
        self.assert_ritsu_first(decision)
        self.assertTrue(decision.emit)
        self.assertEqual(decision.mode, "continuity_gap")
        self.assertEqual(decision.render_context["gap_code"], "CONTINUITY_GAP")
        self.assertEqual(decision.render_context["provenance_tier"], "accepted_summary")
        self.assertTrue(decision.render_context["seek_primary"])
        self.assertFalse(decision.render_context["world_knowledge_allowed"])

    def test_existing_organ_handoff_is_internal_and_silent(self) -> None:
        for cue in (
            "Pasta apostrophe far",
            "vector noodle",
            "What survives translation?",
            "filthy clean",
        ):
            with self.subTest(cue=cue):
                decision = self.decide(cue)
                self.assert_ritsu_first(decision)
                self.assertFalse(decision.emit)
                self.assertEqual(decision.mode, "silent_handoff")
                self.assertEqual(decision.render_context, {})

    def test_generic_world_knowledge_still_uses_ritsu_surface(self) -> None:
        decision = self.decide("What is the Latin word for sleep?")
        self.assert_ritsu_first(decision)
        self.assertTrue(decision.emit)
        self.assertEqual(decision.mode, "answer")
        self.assertTrue(decision.render_context["world_knowledge_allowed"])

    def test_again_bind_happens_before_surface_projection(self) -> None:
        target = {"target_id": "image-critique-42", "target_type": "image_critique", "owner": "Ritzu"}
        decision = self.decide("Ritzu again.", working_state={"current_target": target})
        self.assert_ritsu_first(decision)
        self.assertTrue(decision.emit)
        self.assertEqual(decision.mode, "answer")
        self.assertEqual(decision.render_context["working_target"], target)
        self.assertFalse(decision.render_context["world_knowledge_allowed"])

    def test_ambiguous_or_missing_working_state_clarifies_as_ritsu(self) -> None:
        decision = self.decide("Again.")
        self.assert_ritsu_first(decision)
        self.assertTrue(decision.emit)
        self.assertEqual(decision.mode, "clarify")
        self.assertTrue(decision.render_context["clarification_needed"])
        self.assertFalse(decision.render_context["world_knowledge_allowed"])

    def test_unclassified_router_state_fails_silent_not_corporate(self) -> None:
        synthetic = router_mod.RouteResult(
            status="FUTURE_INTERNAL_STATE",
            route="future",
            episode_id=None,
            matched_cue=None,
            provenance_tier="unknown",
            content=None,
            corrections=(),
            world_knowledge_allowed=False,
            seek_primary=False,
            reason="verbose internal diagnostic that must not surface",
        )
        decision = self.gate.decide(synthetic)
        self.assert_ritsu_first(decision)
        self.assertFalse(decision.emit)
        self.assertEqual(decision.mode, "silent_hold")
        self.assertEqual(decision.render_context, {})


if __name__ == "__main__":
    unittest.main()
