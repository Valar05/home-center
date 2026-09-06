#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(os.environ.get(
    "FORTRESS_HOME_CENTER",
    "/storage/emulated/0/Documents/GodotProjects/home-center",
)).resolve()
READER = REPO / "tools/fortress_read_aloud.py"
SERVER = REPO / "tools/pocket_tts_local_server.py"
STATE = Path.home() / ".local/state/home-center/pocket-tts"
PID_FILE = STATE / "server.pid"
LOG_FILE = STATE / "server.log"
HEALTH_URL = "http://127.0.0.1:10205/health"
SPEAK_URL = "http://127.0.0.1:10205/speak"
DEFAULT_CANARY = "Pocket TTS resurrection canary. The deterministic voice lane is alive."


@dataclass(frozen=True)
class Fault:
    code: str
    layer: str
    prediction: str
    next_action: str
    terminal: bool = False


FAULTS = {
    "F001_READER_MISSING": Fault(
        "F001_READER_MISSING", "source",
        "The phone checkout is missing the canonical Pocket TTS adapter.",
        "Fast-forward the phone Home Center checkout to the reviewed GitHub head; do not reinstall Pocket TTS yet.",
    ),
    "F002_SERVER_SOURCE_MISSING": Fault(
        "F002_SERVER_SOURCE_MISSING", "source",
        "The phone checkout does not contain the localhost service added by this campaign.",
        "Fast-forward the phone Home Center checkout to the reviewed GitHub head.",
    ),
    "F010_POCKET_EXEC_MISSING": Fault(
        "F010_POCKET_EXEC_MISSING", "engine",
        "$HOME/bin/pocket-tts-phone is absent or not executable; historical phone runtime was not preserved or was replaced.",
        "Restore the pinned Pocket TTS 2.1.0 wrapper/runtime before changing Android code.",
    ),
    "F020_RISH_MISSING": Fault(
        "F020_RISH_MISSING", "transport",
        "Shizuku/rish is unavailable, so Termux cannot invoke the owned Android playback component.",
        "Repair the existing Shizuku/rish bridge only; do not add an alternate player.",
    ),
    "F030_PLAYBACK_COMPONENT_MISSING": Fault(
        "F030_PLAYBACK_COMPONENT_MISSING", "android",
        "The installed Home Center APK does not expose PocketTtsPlaybackActivity or the installed APK is stale.",
        "Install the APK built from this campaign branch, then rerun doctor.",
    ),
    "F040_LOCAL_SERVICE_DOWN": Fault(
        "F040_LOCAL_SERVICE_DOWN", "service",
        "All canonical Pocket prerequisites may be present, but the localhost service is not listening.",
        "Run this campaign with --activate; it starts exactly one canonical localhost service.",
    ),
    "F050_DOCTOR_FAILED": Fault(
        "F050_DOCTOR_FAILED", "doctor",
        "The canonical reader doctor failed without a more specific historical boundary code.",
        "Inspect the embedded doctor receipt; repair only the named boundary, then rerun.",
    ),
    "F051_READER_NON_JSON": Fault(
        "F051_READER_NON_JSON", "contract",
        "The canonical reader stopped producing its machine-readable contract.",
        "Repair fortress_read_aloud.py output before attempting playback.",
    ),
    "F052_SPEECH_TIMEOUT": Fault(
        "F052_SPEECH_TIMEOUT", "runtime",
        "Pocket synthesis/playback did not terminate inside the bounded acceptance window.",
        "Reconcile the existing synthesis/playback process and receipt; do not blindly replay.",
    ),
    "F060_PLAYBACK_UNVERIFIED": Fault(
        "F060_PLAYBACK_UNVERIFIED", "acceptance",
        "Audio generation may have happened, but Home Center did not prove completed physical playback.",
        "Use the receipt to distinguish synthesis, Activity launch, play_start, and play_finish; fix the first missing transition.",
    ),
    "OK": Fault(
        "OK", "accepted",
        "The canonical Pocket engine, Home Center playback component, and localhost invocation lane are healthy.",
        "No repair. Preserve this head and receipt as last-known-good.",
        terminal=True,
    ),
}


def fault(code: str, detail: str = "", evidence: dict | None = None) -> dict:
    item = FAULTS.get(code, FAULTS["F050_DOCTOR_FAILED"])
    return {
        "ok": code == "OK",
        "fault": asdict(item),
        "detail": detail,
        "evidence": evidence or {},
    }


def run_reader_doctor() -> dict:
    if not READER.is_file():
        return fault("F001_READER_MISSING", str(READER))
    proc = subprocess.run(
        [sys.executable, str(READER), "--doctor"],
        cwd=str(REPO), text=True, capture_output=True, timeout=60, check=False,
    )
    try:
        doctor = json.loads((proc.stdout or "").strip())
    except json.JSONDecodeError:
        return fault("F051_READER_NON_JSON", (proc.stderr or proc.stdout or "")[-4000:])
    if doctor.get("ok") is True:
        return {"ok": True, "fault": asdict(FAULTS["OK"]), "detail": "canonical doctor passed", "evidence": doctor}
    reason = str(doctor.get("blockedReason", "")).lower()
    if "pocket-tts-phone missing" in reason:
        code = "F010_POCKET_EXEC_MISSING"
    elif "rish unavailable" in reason:
        code = "F020_RISH_MISSING"
    elif "playbackactivity unavailable" in reason or "playback component" in reason:
        code = "F030_PLAYBACK_COMPONENT_MISSING"
    else:
        code = "F050_DOCTOR_FAILED"
    return fault(code, doctor.get("blockedReason", "doctor failed"), doctor)


def request_json(url: str, payload: dict | None = None, timeout: float = 8.0) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="GET" if data is None else "POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
        except Exception:
            body = {"ok": False, "detail": str(error)}
        return error.code, body


def service_health() -> dict:
    try:
        status, body = request_json(HEALTH_URL, timeout=4.0)
    except Exception as error:
        return fault("F040_LOCAL_SERVICE_DOWN", str(error))
    if status == 200 and body.get("ok") is True:
        return {"ok": True, "fault": asdict(FAULTS["OK"]), "detail": "localhost service healthy", "evidence": body}
    code = str(body.get("faultCode", "F050_DOCTOR_FAILED"))
    return fault(code if code in FAULTS else "F050_DOCTOR_FAILED", body.get("detail", f"HTTP {status}"), body)


def activate_service() -> dict:
    if not SERVER.is_file():
        return fault("F002_SERVER_SOURCE_MISSING", str(SERVER))
    existing = service_health()
    if existing.get("ok"):
        return existing
    doctor = run_reader_doctor()
    if not doctor.get("ok"):
        return doctor
    STATE.mkdir(parents=True, exist_ok=True)
    log = LOG_FILE.open("ab", buffering=0)
    process = subprocess.Popen(
        [sys.executable, str(SERVER)],
        cwd=str(REPO),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    PID_FILE.write_text(str(process.pid) + "\n", encoding="utf-8")
    deadline = time.monotonic() + 10.0
    last = fault("F040_LOCAL_SERVICE_DOWN", "service start pending")
    while time.monotonic() < deadline:
        time.sleep(0.25)
        last = service_health()
        if last.get("ok"):
            last["activation"] = {"started": True, "pid": process.pid, "log": str(LOG_FILE)}
            return last
        if process.poll() is not None:
            break
    return fault("F040_LOCAL_SERVICE_DOWN", "service failed to become healthy", {
        "pid": process.pid,
        "exitCode": process.poll(),
        "log": str(LOG_FILE),
        "lastHealth": last,
    })


def prove(text: str) -> dict:
    health = service_health()
    if not health.get("ok"):
        return health
    try:
        status, receipt = request_json(SPEAK_URL, {"text": text}, timeout=390.0)
    except Exception as error:
        return fault("F052_SPEECH_TIMEOUT", str(error))
    if status == 200 and receipt.get("ok") is True and receipt.get("playbackVerified") is True:
        return {
            "ok": True,
            "fault": asdict(FAULTS["OK"]),
            "detail": "end-to-end playback completed",
            "evidence": receipt,
        }
    code = str(receipt.get("faultCode", "F060_PLAYBACK_UNVERIFIED"))
    return fault(code if code in FAULTS else "F060_PLAYBACK_UNVERIFIED", receipt.get("detail", f"HTTP {status}"), receipt)


def campaign(activate: bool, prove_text: str | None) -> dict:
    source = {
        "repo": str(REPO),
        "reader": str(READER),
        "server": str(SERVER),
        "pidFile": str(PID_FILE),
    }
    doctor = run_reader_doctor()
    if not doctor.get("ok"):
        return {"schema": "fortress.pocket-tts-resurrection.v1", "phase": "doctor", "source": source, **doctor}
    service = activate_service() if activate else service_health()
    if not service.get("ok"):
        return {"schema": "fortress.pocket-tts-resurrection.v1", "phase": "activation", "source": source, **service}
    if prove_text is not None:
        accepted = prove(prove_text)
        return {"schema": "fortress.pocket-tts-resurrection.v1", "phase": "acceptance", "source": source, **accepted}
    return {"schema": "fortress.pocket-tts-resurrection.v1", "phase": "ready", "source": source, **service}


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic Pocket TTS fault lookup, activation, and physical proof campaign")
    parser.add_argument("--activate", action="store_true", help="start the canonical localhost service only after doctor passes")
    parser.add_argument("--prove", nargs="?", const=DEFAULT_CANARY, help="speak a canary and require completed Home Center playback")
    parser.add_argument("--fault-table", action="store_true", help="print the deterministic fault lookup table")
    args = parser.parse_args()
    if args.fault_table:
        print(json.dumps({key: asdict(value) for key, value in FAULTS.items()}, indent=2, sort_keys=True))
        return
    result = campaign(args.activate, args.prove)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if result.get("ok") else 2)


if __name__ == "__main__":
    main()
