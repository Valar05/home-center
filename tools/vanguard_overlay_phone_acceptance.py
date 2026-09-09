#!/data/data/com.termux/files/usr/bin/python
"""Physical post-install acceptance sequence for Vanguard overlay.

This script begins only after the base phone campaign has already proved a live,
visible-user-armed microphone and advancing bounded ring. It deliberately requires a
real notification tap and one real spoken phrase. It never manufactures ARM LISTENING.

Exit codes:
  0  automated/user-assisted acceptance slice passed (reboot + Drew acceptance remain)
 30  repairable implementation/runtime failure; feed evidence to free-tab repair
 31  waiting for required human evidence (heartbeat tap or spoken phrase)
 32  phone/body instrumentation unavailable; do not guess
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE_PATH = HERE / "vanguard_overlay_campaign.py"
spec = importlib.util.spec_from_file_location("vanguard_overlay_acceptance_core", CORE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit(32)
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)

STATE = Path(os.environ.get("HC_VANGUARD_OVERLAY_STATE", str(core.STATE))).expanduser()
LATEST = STATE / "acceptance-latest.json"
HISTORY = STATE / "acceptance-history.jsonl"
PACKAGE = core.PACKAGE

FIELD_NAMES = (
    "overlay_mode",
    "listening_state",
    "mic_active",
    "ring_write_bytes",
    "ring_capacity_bytes",
    "transcript_segment_count",
    "last_transcript_at_ms",
    "last_transcript_start_sample",
    "last_transcript_end_sample",
    "latest_transcript_text",
    "keep_count",
    "last_keep_id",
    "last_keep_bytes",
    "actual_sample_rate_hz",
    "latest_error",
    "opinion_speaker",
    "opinion_provider_state",
)


def now_ms() -> int:
    return int(time.time() * 1000)


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def record(status: str, phase: str, detail: str, **extra) -> dict:
    row = {
        "schema": "vanguard-overlay-phone-acceptance-v1",
        "status": status,
        "phase": phase,
        "detail": detail,
        "atMs": now_ms(),
        "requested": True,
        "implemented": True,
        "tested": True,
        "deployed": True,
        "accepted": False,
        **extra,
    }
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    atomic_json(LATEST, row)
    print(json.dumps(row, sort_keys=True), flush=True)
    return row


def parse_fields(raw: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in FIELD_NAMES:
        marker = key + "="
        if marker not in raw:
            continue
        tail = raw.split(marker, 1)[1]
        # content query rows are comma-separated. latest_transcript_text must escape
        # commas in provider output if it wants to preserve them; this canary only
        # needs non-empty bounded text.
        fields[key] = tail.split(",", 1)[0].strip().strip("'").strip('"')
    return fields


def query_state() -> dict:
    result = core.rish(
        f"content query --uri content://com.homecenter.operatoroverlay.state/state 2>/dev/null || true",
        timeout=60,
    )
    raw = result["stdout"] + "\n" + result["stderr"]
    return {"rc": result["rc"], "raw": raw[-16000:], "fields": parse_fields(raw)}


def integer(fields: dict[str, str], key: str) -> int:
    try:
        return int(str(fields.get(key, "0")).strip())
    except ValueError:
        return 0


def truth(fields: dict[str, str], key: str) -> bool:
    return str(fields.get(key, "")).lower() in ("1", "true", "yes")


def visible_action(action: str) -> dict:
    return core.rish(
        f"am start -n {PACKAGE}/.MainActivity --es vanguard_action {action}",
        timeout=60,
    )


def wait_state(predicate, seconds: int, phase: str, heartbeat: int = 5) -> dict | None:
    deadline = time.time() + seconds
    next_note = 0.0
    last = None
    while time.time() < deadline:
        if core.stop_requested():
            record("stopped", phase, "Campaign STOP requested during physical acceptance.")
            raise SystemExit(core.EXIT_STOPPED)
        last = query_state()
        if predicate(last["fields"]):
            return last
        if time.time() >= next_note:
            next_note = time.time() + heartbeat
            record("waiting", phase, "Waiting for physical runtime evidence.", state=last["fields"])
        time.sleep(1)
    return last


def require_base_fields() -> dict:
    state = query_state()
    required = {
        "overlay_mode", "listening_state", "mic_active", "ring_write_bytes",
        "ring_capacity_bytes", "transcript_segment_count", "keep_count",
        "last_transcript_start_sample", "last_transcript_end_sample",
        "latest_transcript_text", "last_keep_id", "last_keep_bytes",
        "opinion_speaker", "opinion_provider_state",
    }
    missing = sorted(required - set(state["fields"]))
    if missing:
        record("repair-needed", "instrumentation", "Phone state provider lacks fields required by the committed canary protocol.", missing=missing, state=state["fields"])
        raise SystemExit(30)
    if not truth(state["fields"], "mic_active"):
        record("waiting-user", "instrumentation", "Post-install acceptance requires the already user-armed live microphone session; mic_active is false.", state=state["fields"])
        raise SystemExit(31)
    return state


def presentation_and_notification_restore() -> dict:
    for action, expected in (("FULL", "FULL"), ("BUBBLE", "BUBBLE")):
        result = visible_action(action)
        if result["rc"] != 0:
            record("repair-needed", "presentation", f"Visible MainActivity action {action} failed.", evidence=result)
            raise SystemExit(30)
        state = wait_state(lambda f, e=expected: f.get("overlay_mode") == e and truth(f, "mic_active"), 15, "presentation")
        if state is None or state["fields"].get("overlay_mode") != expected or not truth(state["fields"], "mic_active"):
            record("repair-needed", "presentation", f"{action} did not converge while preserving microphone capture.", state=(state or {}).get("fields"))
            raise SystemExit(30)

    result = visible_action("HIDE")
    if result["rc"] != 0:
        record("repair-needed", "notification-restore", "Visible HIDE action failed.", evidence=result)
        raise SystemExit(30)
    hidden = wait_state(lambda f: f.get("overlay_mode") == "HIDDEN" and truth(f, "mic_active"), 15, "notification-restore")
    if hidden is None or hidden["fields"].get("overlay_mode") != "HIDDEN" or not truth(hidden["fields"], "mic_active"):
        record("repair-needed", "notification-restore", "HIDE did not remove presentation while preserving listening.", state=(hidden or {}).get("fields"))
        raise SystemExit(30)

    core.notify(
        "Vanguard canary: tap the Home Center heartbeat",
        "The overlay is intentionally hidden and still listening. Tap the actual Home Center heartbeat notification now; shell RESTORE will not count.",
        "vanguard-overlay-notification-tap",
    )
    restored = wait_state(
        lambda f: f.get("overlay_mode") in ("BUBBLE", "FULL") and truth(f, "mic_active"),
        int(os.environ.get("HC_VANGUARD_OVERLAY_NOTIFICATION_TAP_SECONDS", "180")),
        "notification-restore",
    )
    if restored is None or restored["fields"].get("overlay_mode") not in ("BUBBLE", "FULL"):
        record("waiting-user", "notification-restore", "Real heartbeat notification tap was not observed before the timeout. No shell-generated restore was counted.", state=(restored or {}).get("fields"))
        raise SystemExit(31)
    record("passed", "notification-restore", "FULL/BUBBLE/HIDDEN and real heartbeat-tap restore preserved the live microphone session.", state=restored["fields"])
    return restored


def ui_exclusion_and_ritsu() -> None:
    visible_action("FULL")
    full = wait_state(lambda f: f.get("overlay_mode") == "FULL", 15, "persona")
    if full is None:
        record("repair-needed", "persona", "FULL presentation unavailable for persona/exclusion canary.")
        raise SystemExit(30)
    fields = full["fields"]
    if str(fields.get("opinion_speaker", "")).strip().lower() != "ritsu":
        record("repair-needed", "persona", "Live state does not identify Ritsu as default opinion speaker.", state=fields)
        raise SystemExit(30)

    dump = core.rish(
        "set -e; f=/data/local/tmp/vanguard-overlay-ui.xml; uiautomator dump \"$f\" >/dev/null 2>&1; cat \"$f\"; rm -f \"$f\"",
        timeout=45,
    )
    if dump["rc"] != 0 or "<hierarchy" not in dump["stdout"]:
        record("instrumentation-pending", "persona", "Ritsu state passed, but live UI hierarchy dump is unavailable; source Adam exclusion remains separate evidence.", rish=dump)
        return
    if re.search(r"\badam\b", dump["stdout"], flags=re.I):
        record("repair-needed", "persona", "Adam appeared in the live UI hierarchy; runtime exclusion contract failed.")
        raise SystemExit(30)
    record("passed", "persona", "Ritsu is the live default opinion speaker and the visible UI hierarchy contains no Adam token.", opinionProviderState=fields.get("opinion_provider_state"))


def speech_canary() -> dict:
    before = query_state()
    before_count = integer(before["fields"], "transcript_segment_count")
    before_write = integer(before["fields"], "ring_write_bytes")
    core.notify(
        "Vanguard canary: say one sentence",
        "Please speak one ordinary sentence near the phone now. Exact wording does not matter; this tests live text transform and sample mapping.",
        "vanguard-overlay-speech",
    )

    def new_segment(fields: dict[str, str]) -> bool:
        count = integer(fields, "transcript_segment_count")
        text = str(fields.get("latest_transcript_text", "")).strip()
        start = integer(fields, "last_transcript_start_sample")
        end = integer(fields, "last_transcript_end_sample")
        write = integer(fields, "ring_write_bytes")
        return count > before_count and bool(text) and end > start >= 0 and write > before_write

    observed = wait_state(
        new_segment,
        int(os.environ.get("HC_VANGUARD_OVERLAY_SPEECH_SECONDS", "120")),
        "speech",
    )
    if observed is None or not new_segment(observed["fields"]):
        record("waiting-user", "speech", "No complete new mapped transcript segment was observed before timeout. Campaign does not guess whether speech was supplied.", before=before["fields"], last=(observed or {}).get("fields"))
        raise SystemExit(31)

    fields = observed["fields"]
    sample_rate = integer(fields, "actual_sample_rate_hz")
    if sample_rate <= 0:
        record("repair-needed", "speech", "Live transcript appeared but actual sample rate is missing/invalid.", state=fields)
        raise SystemExit(30)
    record("passed", "speech", "A real spoken phrase produced bounded rolling text with monotonic raw-sample mapping.", state=fields)
    return observed


def keep_canary() -> dict:
    before = query_state()
    before_count = integer(before["fields"], "keep_count")
    result = visible_action("KEEP_LAST_60")
    if result["rc"] != 0:
        record("repair-needed", "keep", "Visible KEEP_LAST_60 action failed.", evidence=result)
        raise SystemExit(30)

    def promoted(fields: dict[str, str]) -> bool:
        return (
            integer(fields, "keep_count") == before_count + 1
            and bool(str(fields.get("last_keep_id", "")).strip())
            and integer(fields, "last_keep_bytes") > 0
        )

    after = wait_state(promoted, 30, "keep")
    if after is None or not promoted(after["fields"]):
        record("repair-needed", "keep", "Explicit KEEP did not produce exactly one durable non-empty bundle receipt.", before=before["fields"], last=(after or {}).get("fields"))
        raise SystemExit(30)
    record("passed", "keep", "KEEP LAST 60s produced exactly one durable bundle id with non-zero audio bytes.", state=after["fields"])
    return after


def stop_clear_canary() -> dict:
    before = query_state()
    before_keep = integer(before["fields"], "keep_count")
    result = visible_action("STOP_LISTENING")
    if result["rc"] != 0:
        record("repair-needed", "stop-clear", "Visible STOP_LISTENING action failed.", evidence=result)
        raise SystemExit(30)

    stopped = wait_state(
        lambda f: f.get("listening_state") == "OFF" and not truth(f, "mic_active") and integer(f, "transcript_segment_count") == 0,
        20,
        "stop-clear",
    )
    if stopped is None:
        record("repair-needed", "stop-clear", "STOP did not converge to OFF/mic released/transcript cleared.")
        raise SystemExit(30)

    first = integer(stopped["fields"], "ring_write_bytes")
    time.sleep(5)
    later = query_state()
    second = integer(later["fields"], "ring_write_bytes")
    if second != first:
        record("repair-needed", "stop-clear", "Raw logical write position kept advancing after STOP; microphone/capture teardown is not trustworthy.", beforeStop=before["fields"], stopped=stopped["fields"], later=later["fields"])
        raise SystemExit(30)
    if integer(later["fields"], "keep_count") < before_keep:
        record("repair-needed", "stop-clear", "STOP destroyed a previously explicit KEEP bundle receipt.", before=before["fields"], later=later["fields"])
        raise SystemExit(30)
    if integer(later["fields"], "transcript_segment_count") != 0 or truth(later["fields"], "mic_active"):
        record("repair-needed", "stop-clear", "Transient text or microphone liveness reappeared after STOP.", state=later["fields"])
        raise SystemExit(30)
    record("passed", "stop-clear", "STOP released microphone, stopped raw advancement, cleared rolling transcript, and preserved explicit KEEP receipt state.", state=later["fields"])
    return later


def main() -> int:
    try:
        base = require_base_fields()
        record("running", "acceptance", "Beginning user-assisted physical acceptance slice after initial live microphone canary.", state=base["fields"])
        presentation_and_notification_restore()
        ui_exclusion_and_ritsu()
        speech_canary()
        keep_canary()
        final_state = stop_clear_canary()
        record(
            "passed-partial",
            "acceptance",
            "Physical session acceptance passed through notification restore, speech mapping, KEEP and STOP/clear. Reboot-disarmed proof and Drew acceptance remain open by design.",
            finalState=final_state["fields"],
            remainingAcceptance=["explicit-reboot-disarmed-canary", "battery-thermal-observation", "Drew-acceptance"],
            accepted=False,
        )
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:
        record("body-blocked", "acceptance", f"{type(exc).__name__}: {exc}")
        return 32


if __name__ == "__main__":
    raise SystemExit(main())
