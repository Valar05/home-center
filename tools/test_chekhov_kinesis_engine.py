#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("chekhov_kinesis_engine.py")
spec = importlib.util.spec_from_file_location("chekhov_kinesis_engine", MODULE_PATH)
engine = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(engine)


def test_coffee_pot_aggressive_membership_without_invented_mechanics():
    graph = engine.derive_graph({
        "items": [
            {"id": "coffee.used", "label": "Coffee pot", "text": "Coffee pot used as a weapon and struck him with it."},
            {"id": "coffee.thought", "label": "Coffee pot", "text": "Coffee the pot thought about violently murdering the toaster."},
            {"id": "coffee.opinion", "label": "Coffee pot", "text": "Coffee pot had violent enough opinions."},
        ]
    })
    by_id = {item["id"]: item for item in graph["items"]}
    assert by_id["coffee.used"]["included"] is True
    assert "USED" in by_id["coffee.used"]["evidence"]["states"]
    assert "STRIKE" in by_id["coffee.used"]["mechanics"]["primitives"]
    assert by_id["coffee.thought"]["included"] is True
    assert "IMAGINED" in by_id["coffee.thought"]["evidence"]["states"]
    assert by_id["coffee.thought"]["mechanics"]["status"] == "UNKNOWN"
    assert by_id["coffee.opinion"]["included"] is True
    assert "OPINIONATED" in by_id["coffee.opinion"]["evidence"]["states"]
    assert by_id["coffee.opinion"]["mechanics"]["status"] == "UNKNOWN"


def test_halligan_compresses_to_wedge_and_architecture_without_fake_hand_hold():
    item = {
        "id": "arsenal.tetsuya.halligan",
        "label": "Halligan",
        "state": "USED",
        "text": "The crowbar became a door, wedged into the failing frame, holding the route open.",
        "sourceRefs": ["drive:1RrgqSJxFYu4_27pcY5DUWVAqwn8-IUifiuc49-xEmpE"],
    }
    record = engine.derive_graph({"frameId": "sim-frame-chekhov-arsenal-v4", "items": [item]})["items"][0]
    assert record["evidence"]["sourceRefs"] == ["drive:1RrgqSJxFYu4_27pcY5DUWVAqwn8-IUifiuc49-xEmpE"]
    assert "HOLD" not in record["mechanics"]["primitives"]
    assert record["mechanics"]["compression"]["channels"]["body_interface"] == "unknown"
    assert "WEDGE" in record["mechanics"]["primitives"]
    assert "BECOME_ARCHITECTURE" in record["mechanics"]["primitives"]
    assert "ROLE_CHANGE" in record["mechanics"]["fourthDoorClasses"]
    assert "SYSTEM_CHANGE" in record["mechanics"]["fourthDoorClasses"]


def test_explicit_hand_hold_can_still_support_body_interface():
    record = engine.derive_graph([{
        "id": "sword.held",
        "label": "Sword",
        "chekhov": True,
        "text": "He held the sword loosely in his right hand.",
    }])["items"][0]
    assert "HOLD" in record["mechanics"]["primitives"]
    assert record["mechanics"]["compression"]["channels"]["body_interface"] == ["HOLD"]


def test_nonviolent_ordinary_object_is_not_auto_admitted():
    graph = engine.derive_graph([{"id": "cup", "label": "Cup", "text": "A cup sat on the table."}])
    assert graph["includedCount"] == 0
    assert graph["items"][0]["mechanics"]["status"] == "UNKNOWN"


def test_upstream_miner_can_force_high_recall_membership_without_mechanics():
    graph = engine.derive_graph([{"id": "oddity", "label": "Odd object", "chekhov": True, "text": "No mechanics witnessed."}])
    item = graph["items"][0]
    assert item["included"] is True
    assert item["mechanics"]["status"] == "UNKNOWN"


def test_order_does_not_change_graph_hash():
    a = {"id": "a", "text": "weapon"}
    b = {"id": "b", "text": "refused to use the weapon"}
    first = engine.derive_graph({"frameId": "frame", "items": [a, b]})
    second = engine.derive_graph({"frameId": "frame", "items": [b, a]})
    assert first["inputSha256"] == second["inputSha256"]
    assert first["graphSha256"] == second["graphSha256"]
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_duplicate_identity_fails_closed():
    try:
        engine.derive_graph([{"id": "same", "text": "weapon"}, {"id": "same", "text": "weapon"}])
    except ValueError as exc:
        assert "duplicate Chekhov item ids" in str(exc)
    else:
        raise AssertionError("duplicate identities must fail closed")
