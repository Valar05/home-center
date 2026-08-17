#!/usr/bin/env python3
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "adam_inner_fortress", ROOT / "tools" / "adam_inner_fortress.py"
)
assert spec and spec.loader
inner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inner)


def fake_detector(text):
    return text.lower().strip() == "pills taken"


def fake_recorder(text, request_id):
    return {
        "schema": "adam-observation-receipt-v1", "ok": True,
        "raw": text, "eventId": request_id,
    }


with tempfile.TemporaryDirectory() as directory:
    state = Path(directory) / "state.json"
    first_store = inner.SessionStore(state)

    before = inner.handle_turn(
        "Story.", store=first_store,
        observation_detector=fake_detector, observation_recorder=fake_recorder,
    )
    assert before["state"] == "INACTIVE"

    opened = inner.handle_turn(
        "  Inner Fortress\n", store=first_store, request_id="invoke-1",
        observation_detector=fake_detector, observation_recorder=fake_recorder,
    )
    assert opened["state"] == "ACTIVE_REHEARSAL"
    assert opened["authoritativeCharacter"] is False
    assert opened["judgmentJarApplied"] is False
    assert opened["raw"] == "  Inner Fortress\n"
    session_id = opened["sessionId"]

    replay = inner.handle_turn(
        "  Inner Fortress\n", store=first_store, request_id="invoke-1",
        observation_detector=fake_detector, observation_recorder=fake_recorder,
    )
    assert replay["idempotent"] is True
    assert replay["eventId"] == opened["eventId"]
    assert first_store.read()["activeSession"]["sequence"] == 1

    conflict = inner.handle_turn(
        "Inner Fortress", store=first_store, request_id="invoke-1",
        observation_detector=fake_detector, observation_recorder=fake_recorder,
    )
    assert conflict["state"] == "IDEMPOTENCY_CONFLICT"

    # A new object simulates Termux/Codex process loss and restart.
    restarted_store = inner.SessionStore(state)
    story = inner.handle_turn(
        "Story.", store=restarted_store, request_id="story-1",
        observation_detector=fake_detector, observation_recorder=fake_recorder,
    )
    assert story["route"] == "STORY_CONTINUE"
    assert story["sessionId"] == session_id
    assert story["sequence"] == 2
    assert story["state"] == "WAITING_CHATGPT_REHEARSAL"
    envelope = story["cognitionEnvelope"]
    assert envelope["operation"] == "codex_rehearsal.turn"
    assert envelope["exactInput"] == "Story."
    assert envelope["requestedPerformance"] == "She-Ra"
    assert envelope["performanceLabel"] == "CHATGPT_REHEARSAL_OF_SHE_RA"
    assert envelope["authoritativeCharacter"] is False
    assert "AUTHORITATIVE_SHE_RA_CHARACTER" in envelope["forbiddenClaims"]

    critique = inner.handle_turn(
        "Critique that", store=restarted_store, request_id="critique-1",
        observation_detector=fake_detector, observation_recorder=fake_recorder,
    )
    assert critique["route"] == "CRITIQUE"
    assert critique["sessionId"] == session_id

    direction = inner.handle_turn(
        "Stage direct: she takes pills", store=restarted_store, request_id="stage-1",
        observation_detector=lambda text: "pills" in text.lower(),
        observation_recorder=lambda text, request_id: (_ for _ in ()).throw(
            AssertionError("fictional stage direction reached real observation ledger")
        ),
    )
    assert direction["route"] == "STAGE_DIRECTION"
    assert direction["raw"] == "Stage direct: she takes pills"

    observation = inner.handle_turn(
        "Pills taken", store=restarted_store, request_id="pills-1",
        observation_detector=fake_detector, observation_recorder=fake_recorder,
    )
    assert observation["route"] == "OBSERVATION_LEDGER"
    assert observation["state"] == "OBSERVATION_RECORDED"
    assert restarted_store.read()["activeSession"]["sessionId"] == session_id

    closed = inner.handle_turn(
        "Exit Inner Fortress", store=restarted_store, request_id="close-1",
        observation_detector=fake_detector, observation_recorder=fake_recorder,
    )
    assert closed["state"] == "CLOSED"
    assert restarted_store.read()["activeSession"] is None

with tempfile.TemporaryDirectory() as directory:
    state = Path(directory) / "state.json"
    corrupt = b'{"schema": "wrong", "events": [1]}'
    state.write_bytes(corrupt)
    blocked = inner.handle_turn(
        "Inner Fortress", store=inner.SessionStore(state), request_id="corrupt-1",
        observation_detector=fake_detector, observation_recorder=fake_recorder,
    )
    assert blocked["state"] == "STATE_BLOCKED"
    assert state.read_bytes() == corrupt

print("Inner Fortress invoke / restart continuity / ledger routing: PASS")
