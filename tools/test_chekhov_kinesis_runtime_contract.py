#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_chekhov_jar_is_default_phone_runtime():
    config = json.loads((ROOT / "config" / "judgment-jars.v1.json").read_text(encoding="utf-8"))
    selected = config["runtime"]["defaultPhoneJarIds"]
    assert "embodied-kinesis-voices" in selected
    assert "chekhov-kinesis-engine" in selected


def test_chekhov_jar_has_aggressive_intake_and_determinism_contract():
    jar = (ROOT / ".continue" / "rules" / "07-judgement-jar-chekhov-kinesis-engine.md").read_text(encoding="utf-8")
    assert "Chekhov ingress is shameless; kinesis inference is prissy" in jar
    assert "coffee pot thought about violently" in jar.lower()
    assert "coffee pot with violent enough opinions" in jar.lower()
    assert "Same normalized source state plus the same engine version" in jar
    assert "unknown" in jar
    assert "KINETIC_NONDETERMINISM" in jar


def test_fortress_intake_routes_live_and_mined_candidates_through_same_engine():
    skill = (ROOT / "skills" / "fortress-intake" / "SKILL.md").read_text(encoding="utf-8")
    assert "aggressive Chekhov admission pass" in skill
    assert "tools/chekhov_kinesis_engine.py" in skill
    assert "Automated conversation-mining and backfill jobs use the same Chekhov admission law" in skill
    assert "chekhov: true" in skill
    assert "unknown" in skill


def test_skill_exposes_story_simulator_grounded_motion_and_embodied_kinesis_joins():
    skill = (ROOT / "skills" / "chekhov-kinesis-engine" / "SKILL.md").read_text(encoding="utf-8")
    assert "Grounded Motion" in skill
    assert "Embodied Kinesis Voices" in skill
    assert "Story Simulator / Fourth Door" in skill
    assert "body_interface -> contact -> load -> constraint -> transfer -> terminal" in skill
