#!/usr/bin/env python3
"""Static source contract for the Vanguard Pocket TTS overlay keep.

PASS is repository source-shape evidence only. It does not prove Android build,
phone deployment, Pocket model health, audible playback, or Drew acceptance.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "android" / "operator-overlay" / "app" / "src" / "main"
JAVA = APP / "java" / "com" / "homecenter" / "operatoroverlay"
ADDENDUM = ROOT / "campaigns" / "vanguard-overlay-resurrection" / "POCKET_TTS_KEEP_ADDENDUM.md"
STATE = JAVA / "OperatorState.java"
PROVIDER = JAVA / "OperatorStateProvider.java"
OVERLAY = JAVA / "OperatorOverlayService.java"
RELAY = ROOT / "tools" / "android_phone_home_center_relay.py"
CONSUMER = ROOT / "tools" / "operator_overlay_pocket_speech.py"

checks: list[dict] = []


def body(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def add(name: str, ok: bool, detail: str, path: Path | None = None) -> None:
    checks.append({
        "check": name,
        "ok": bool(ok),
        "detail": detail,
        "path": str(path.relative_to(ROOT)) if path and path.is_relative_to(ROOT) else (str(path) if path else None),
    })


addendum = body(ADDENDUM)
state = body(STATE)
provider = body(PROVIDER)
overlay = body(OVERLAY)
relay = body(RELAY)
consumer = body(CONSUMER)

add(
    "binding_addendum",
    "OVERLAY IS THE FACE" in addendum and "FORTRESS-READ IS THE THROAT" in addendum,
    "The 2026-09-09 overlay-surface correction is persisted in the commissioned branch.",
    ADDENDUM,
)

required_state = [
    "pocket_speech_request_id",
    "pocket_speech_text_b64",
    "pocket_speech_text_sha256",
    "pocket_speech_status",
    "pocket_speech_receipt_b64",
    "pocket_speech_updated_ms",
    "pocket_speech_fault",
]
for key in required_state:
    add(
        f"state_{key}",
        key in state.lower() and key in provider.lower(),
        f"Overlay state and provider both expose {key}.",
        PROVIDER,
    )

add(
    "overlay_speak_surface",
    "SPEAK" in overlay and "Pocket" in overlay and "pocket" in overlay.lower(),
    "FULL overlay exposes a bounded Pocket speech action instead of a separate launcher app.",
    OVERLAY,
)
add(
    "overlay_mute_authority",
    "muted" in overlay and "pocket" in overlay.lower(),
    "Overlay mute participates in Pocket speech behavior.",
    OVERLAY,
)
add(
    "legacy_adam_ui_removed",
    "Adam —" not in overlay and "submitAdamRequest" not in overlay and "adamModeButton" not in overlay,
    "Recovered overlay does not restore the legacy Adam input/mode wall.",
    OVERLAY,
)
add(
    "no_overlay_pocket_launcher",
    "PocketTtsControlActivity" not in overlay and "PocketTtsControlActivity" not in body(APP / "AndroidManifest.xml"),
    "Pocket TTS is not exposed as a second overlay-side launcher activity.",
    APP / "AndroidManifest.xml",
)

add(
    "consumer_exists",
    bool(consumer),
    "Termux-side overlay Pocket request consumer exists.",
    CONSUMER,
)
add(
    "consumer_canonical_reader",
    "fortress-read" in consumer and "pocket-tts-phone" in consumer and "playbackVerified" in consumer,
    "Consumer invokes the canonical Pocket reader and requires physical playback verification.",
    CONSUMER,
)
add(
    "consumer_exact_engine_identity",
    "pocket-home-center" in consumer and "com.dclar.homecenter/.PocketTtsPlaybackActivity" in consumer,
    "Consumer validates canonical provider/output component identity.",
    CONSUMER,
)
add(
    "consumer_no_http_daemon",
    "127.0.0.1:10205" not in consumer and "localhost:10205" not in consumer and "ThreadingHTTPServer" not in consumer,
    "Overlay speech does not depend on a parallel localhost TTS daemon.",
    CONSUMER,
)
add(
    "consumer_idempotent_receipt_state",
    all(token in consumer for token in ("handled", "request_id", "sha256", "receipt")) and "atomic" in consumer.lower(),
    "Consumer persists request identity/receipt state so relay restart cannot replay terminal speech.",
    CONSUMER,
)
add(
    "consumer_mute_gate",
    "muted" in consumer.lower() and "MUTED" in consumer,
    "Pending speech obeys overlay mute without substituting another engine.",
    CONSUMER,
)

add(
    "relay_imports_consumer",
    "operator_overlay_pocket_speech" in relay,
    "Home Center phone relay imports the overlay Pocket consumer.",
    RELAY,
)
add(
    "relay_services_local_requests",
    "consume_pending_pocket_speech" in relay,
    "Relay services durable overlay Pocket requests during its local loop.",
    RELAY,
)
add(
    "phone_shell_remains_background_lane",
    "TERMUX_SHELL_ACTIONS" in relay and "return termux_shell_execute(a)" in relay,
    "Existing bounded phone_shell recovery lane remains available and is not re-gated by overlay UI.",
    RELAY,
)

failed = [row["check"] for row in checks if not row["ok"]]
print(json.dumps({
    "schema": "vanguard-pocket-overlay-source-contract-v1",
    "ok": not failed,
    "checks": checks,
    "failed": failed,
    "truthBoundary": "PASS proves committed source shape only; Android build, relay deployment, Pocket doctor, request consumption, physical playback receipt and Drew acceptance remain separate evidence gates.",
}, indent=2, sort_keys=True))
raise SystemExit(0 if not failed else 1)
