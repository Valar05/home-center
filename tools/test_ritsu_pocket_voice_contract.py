#!/usr/bin/env python3
"""Regression contract for Ritsu Pocket Voice / Hot Pocket capability memory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RITSU = (ROOT / "skills/ritsu-pocket-voice/SKILL.md").read_text(encoding="utf-8")
EMBODIED = (ROOT / "skills/embodied-communication/SKILL.md").read_text(encoding="utf-8")
READ_ALOUD = (ROOT / "tools/fortress_read_aloud.py").read_text(encoding="utf-8")

required_ritsu = [
    "CAPABILITY ≠ CURRENT CARRIER CALLABILITY.",
    "HOT POCKET = ACTUAL POCKET TTS AUDIO PHYSICALLY PLAYED FROM THE ACTUAL PHONE.",
    "CURRENT_CARRIER_ACTION_NOT_EXPOSED",
    "RITSU_VOICE_CAPABILITY_AMNESIA",
    "RITSU_VOICE_CARRIER_CONFUSION",
    "RITSU_VOICE_HOT_POCKET_SUBSTITUTION",
    "Do not claim Pocket TTS itself is unavailable.",
    "produce audible sound through the wrong engine and call the commission complete",
    "rendered but not physically played",
]

required_embodied = [
    "Implemented",
    "Callable",
    "Rendered",
    "Played/Presented",
    "Never report `tool unavailable` when a more precise transition is known.",
    "Home Center -> Command Center -> Phone Hands -> primary-phone",
    "fortress-read 'EXACT TEXT'",
    "com.dclar.homecenter/.PocketTtsPlaybackActivity",
]

required_runtime = [
    'PLAYBACK_COMPONENT = "com.dclar.homecenter/.PocketTtsPlaybackActivity"',
    '"playStartObserved": True',
    '"playCompletedObserved": True',
    '"systemFallbackUsed": False',
    '"cloudFallbackUsed": False',
]

for needle in required_ritsu:
    assert needle in RITSU, f"Ritsu Pocket Voice missing anti-amnesia invariant: {needle}"
for needle in required_embodied:
    assert needle in EMBODIED, f"Embodied communication missing capability-stage invariant: {needle}"
for needle in required_runtime:
    assert needle in READ_ALOUD, f"fortress-read missing physical playback invariant: {needle}"

# The mnemonic must never degrade into permission to use a substitute engine.
assert "do not silently substitute another engine" in RITSU
assert "No substitute" in RITSU or "NO SUBSTITUTE" in RITSU

print("RITSU POCKET VOICE / HOT POCKET CONTRACT PASS")
