#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from loopscore_compile import SCHEMA, compile_score

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "loopscore_asmr_punch_v1.json"


def main() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert raw["schema"] == SCHEMA

    first = compile_score(raw)
    second = compile_score(raw)

    assert first == second, "same score and seed must compile identically"
    assert first["schema"] == "fortress.loopscore.plan.v1"
    assert first["scoreId"] == "asmr-punch-beard-brush-v1"
    assert first["mode"] == "punch"
    assert first["summary"] == {
        "durationMs": first["summary"]["durationMs"],
        "clipEvents": 3,
        "speechEvents": 1,
        "silenceEvents": 3,
        "pocketTtsInvoked": False,
        "audioPlayed": False,
    }

    events = first["events"]
    clips = [event for event in events if event["kind"] == "clip"]
    speech = [event for event in events if event["kind"] == "speech"]
    silences = [event for event in events if event["kind"] == "silence"]

    assert len(clips) == 3
    assert len({event["take"] for event in clips}) >= 2, "sibling takes should prevent mechanical repetition"
    assert clips[0]["crossfadeInMs"] == 0
    assert clips[1]["crossfadeInMs"] == 32
    assert clips[2]["crossfadeInMs"] == 32
    assert speech[0]["forge"] == "pocket-tts"
    assert speech[0]["rendered"] is False
    assert speech[0]["played"] is False
    assert silences[0]["reason"] == "arrive"
    assert silences[-1]["reason"] == "stop"
    assert events[0]["kind"] == "silence"
    assert events[-1]["kind"] == "silence"

    print(json.dumps({
        "ok": True,
        "scoreId": first["scoreId"],
        "scoreSha256": first["scoreSha256"],
        "durationMs": first["summary"]["durationMs"],
        "clipEvents": first["summary"]["clipEvents"],
        "speechEvents": first["summary"]["speechEvents"],
        "silenceEvents": first["summary"]["silenceEvents"],
        "pocketTtsInvoked": first["summary"]["pocketTtsInvoked"],
        "audioPlayed": first["summary"]["audioPlayed"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
