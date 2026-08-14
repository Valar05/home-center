#!/usr/bin/env python3
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "adam_observation_ledger", ROOT / "tools" / "adam_observation_ledger.py"
)
assert spec and spec.loader
obs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obs)

assert obs.parse_observation("Pills taken") == {
    "eventType": "medication_adherence", "status": "confirmed_taken",
}
assert obs.parse_observation("I've taken my pills")["status"] == "confirmed_taken"
assert obs.parse_observation("I have already taken a shower")["activity"] == "shower"
assert obs.parse_observation("Log three more drops")["count"] == 3
assert obs.parse_observation("No more nicotine tonight")["eventType"] == "commitment"
assert obs.parse_observation("Log two puffs of weed")["substance"] == "cannabis"
assert obs.looks_like_observation("Pills taken") is True

for rejected in [
    "Stage direct: she takes pills",
    "How many drops should I take next?",
    "Take three drops",
    "I did not take my pills",
    "Do not log three drops",
    "I need a shower",
    "I did not shower",
    "I am going to take two puffs of weed",
    "Take two puffs",
    "Take two puffs of weed",
    "In the story, she says no more nicotine",
]:
    assert obs.looks_like_observation(rejected) is False, rejected
    try:
        obs.parse_observation(rejected)
    except obs.ObservationError:
        pass
    else:
        raise AssertionError(f"must reject non-observation: {rejected}")


class FakeClient:
    calls = 0

    def call_tool(self, operation, args):
        assert operation == "docs_append"
        FakeClient.calls += 1
        return {"auditRequestId": args["requestId"]}


with tempfile.TemporaryDirectory() as directory:
    obs.STATE_PATH = Path(directory) / "observations.json"
    obs._client = FakeClient
    first = obs.record("  Pills taken\n", "event-1")
    replay = obs.record("  Pills taken\n", "event-1")
    assert first["rawPreserved"] is True
    assert replay["idempotent"] is True
    assert replay["eventId"] == first["eventId"]
    assert FakeClient.calls == 1
    try:
        obs.record("Pills taken", "event-1")
    except obs.ObservationError:
        pass
    else:
        raise AssertionError("same request id with changed exact input must conflict")

print("Adam observation after-the-fact classifier: PASS")
