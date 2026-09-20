#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CFG = Path(os.path.expanduser("~/.config/home-center"))
PAIR = CFG / "codex-hub.json"
NODE = CFG / "phone-relay.json"

BASE = os.getenv(
    "HC_PHONE_RELAY_BASE",
    "https://us-central1-home-center-dclar.cloudfunctions.net/phoneHandsRelay",
)
DEVICE_ID = os.getenv("HC_PHONE_DEVICE_ID", "primary-phone")
POLL = float(os.getenv("HC_PHONE_RELAY_POLL_SECONDS", "2.0"))

STATE_DIR = Path(
    os.getenv(
        "HC_PHONE_STATE_DIR",
        os.path.expanduser("~/.local/state/home-center"),
    )
)
HEARTBEAT = Path(
    os.getenv(
        "HC_PHONE_RELAY_HEARTBEAT",
        str(STATE_DIR / "phone-relay-heartbeat.json"),
    )
)

ROOT = Path(__file__).resolve().parent.parent
RELAY_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sys.path.insert(0, str(ROOT / "tools"))

# CRITICAL ARCHITECTURE INVARIANT:
# The relay's startup, cloud polling, and background Termux shell lane must not
# import or execute Shizuku/rish. Shizuku-backed modules are imported lazily
# only when an explicitly interactive Android/UI action is requested.
from android_phone_termux_shell import execute as termux_shell_execute

FACTORY_ACTIONS = {
    "file_stat",
    "file_hash",
    "file_list",
    "file_mkdir",
    "file_copy",
    "file_move",
    "armory_inventory",
    "armory_ingest",
}
ARMORY_ACTIONS = {"armory_doctor", "armory_slice"}
WINDOW_ACTIONS = {"window_status", "window_probe", "window_compose", "window_focus", "window_swap"}
STATUS_TTS_ACTIONS = {"status_tts_doctor", "status_say"}
TERMUX_SHELL_ACTIONS = {"phone_shell"}
DIAGNOSTIC_ACTIONS = {"phone_diagnostics"}
OVERLAY_ACTIONS = {"operator_overlay_status", "operator_overlay_start", "operator_overlay_update"}
VENICE_ACTIONS = {"venice_ingest", "venice_observe", "venice_mine", "venice_status"}

SCREEN_DIRECT_ACTIONS = {
    "tap",
    "swipe",
    "text",
    "keyevent",
    "home",
    "back",
    "recents",
    "launch",
    "force_stop",
}
SCREEN_WINDOW_ACTIONS = {"window_compose", "window_focus", "window_swap"}

DEVICE_CAPABILITIES = [
    "phone_hands",
    "phone_files",
    "armory_worker",
    "window_composer",
    "status_tts",
    "termux_shell",
    "operator_overlay",
    "local_qwen",
    "coding_dungeon",
    "voice",
    "phone_diagnostics_readonly",
    "venice_reactor",
    "venice_audio_features",
    "background_termux_shizuku_independent",
]


def _screen_profile(action):
    kind = str((action or {}).get("action") or "")
    if kind in SCREEN_WINDOW_ACTIONS:
        return {"leaseMs": 2500, "yieldMs": 0}
    if kind in SCREEN_DIRECT_ACTIONS:
        return {"leaseMs": 2500, "yieldMs": 900}
    return None


def http(path, body=None, token=""):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method="GET" if body is None else "POST",
    )
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"HTTP {exc.code} {path}: "
            f'{exc.read().decode("utf-8", "replace")[:2000]}'
        ) from exc


def load_pair():
    if not PAIR.exists():
        raise RuntimeError(f"Home Center pairing missing: {PAIR}")
    return json.loads(PAIR.read_text())


def save_pair(cfg):
    PAIR.write_text(json.dumps(cfg, indent=2) + "\n")
    os.chmod(PAIR, 0o600)


def access_token():
    cfg = load_pair()
    if (
        cfg.get("accessToken")
        and int(cfg.get("expiresAtMs", 0)) > int(time.time() * 1000) + 60000
    ):
        return cfg["accessToken"]

    refresh = cfg.get("refreshToken")
    if not refresh:
        raise RuntimeError("Home Center refresh token missing; re-pair Termux once")

    gateway = cfg.get(
        "gatewayBase",
        "https://us-central1-home-center-dclar.cloudfunctions.net",
    )
    req = urllib.request.Request(
        gateway + "/termuxTokenRefresh",
        data=json.dumps({"refreshToken": refresh}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        out = json.loads(response.read().decode())

    cfg["accessToken"] = out["access_token"]
    cfg["refreshToken"] = out.get("refresh_token", refresh)
    cfg["expiresAtMs"] = (
        int(time.time() * 1000) + int(out.get("expires_in", 3300)) * 1000
    )
    save_pair(cfg)
    return cfg["accessToken"]


def ensure_device():
    CFG.mkdir(parents=True, exist_ok=True)
    if NODE.exists():
        data = json.loads(NODE.read_text())
        token = str(data.get("deviceToken") or "")
        if token:
            try:
                data["registration"] = http(
                    "/register",
                    {
                        "deviceId": DEVICE_ID,
                        "deviceToken": token,
                        "label": "Drew Android Phone",
                        "capabilities": DEVICE_CAPABILITIES,
                    },
                    access_token(),
                )
                NODE.write_text(json.dumps(data, indent=2) + "\n")
                os.chmod(NODE, 0o600)
            except Exception as exc:
                print(
                    "phone-relay registration refresh warning: " + str(exc),
                    file=sys.stderr,
                    flush=True,
                )
            return data

    token = secrets.token_urlsafe(48)
    registration = http(
        "/register",
        {
            "deviceId": DEVICE_ID,
            "deviceToken": token,
            "label": "Drew Android Phone",
            "capabilities": DEVICE_CAPABILITIES,
        },
        access_token(),
    )
    data = {
        "deviceId": DEVICE_ID,
        "deviceToken": token,
        "registeredAt": time.time(),
        "registration": registration,
    }
    NODE.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(NODE, 0o600)
    return data


def write_heartbeat(device_id, state, command_id=""):
    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    obj = {
        "schema": "home-center-phone-relay-heartbeat-v1",
        "deviceId": device_id,
        "pid": os.getpid(),
        "state": state,
        "lastSuccessAtEpoch": int(time.time()),
        "commandId": str(command_id or "")[:180],
        "sourceSha256": RELAY_SOURCE_SHA256,
        "baselineTransport": "termux-no-shizuku",
    }
    temp = HEARTBEAT.with_suffix(HEARTBEAT.suffix + ".tmp")
    temp.write_text(json.dumps(obj, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    os.replace(temp, HEARTBEAT)


def dungeon_run(payload):
    manifest = str(payload.get("manifest") or "").strip()
    if not manifest:
        raise RuntimeError("dungeon_run requires manifest")
    result = subprocess.run(
        [os.path.expanduser("~/bin/dungeon"), "run", manifest],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=int(payload.get("timeoutSeconds", 600)),
    )
    return {"exit": result.returncode, "output": result.stdout[-20000:]}


def dispatch(action):
    kind = action.get("action")

    if kind == "observe":
        from android_phone_hands_bridge import observe as hands_observe

        return hands_observe(
            bool(action.get("ui", True)),
            bool(action.get("screen", False)),
        )

    if kind == "local_ask":
        from android_phone_local_executive import execute as local_execute

        return local_execute(
            str(action.get("intent") or action.get("prompt") or "What is on my screen?")
        )

    if kind == "dungeon_run":
        return dungeon_run(action)

    if kind in VENICE_ACTIONS:
        from venice_reactor import execute as venice_execute

        return venice_execute(
            {
                "action": (
                    "observe"
                    if kind in {"venice_ingest", "venice_observe"}
                    else kind.replace("venice_", "")
                ),
                "features": action.get("features") or action.get("audio") or {},
                "source": action.get("source", "phone-playback"),
                "speak": action.get("speak", True),
                "limit": action.get("limit", 200),
            }
        )

    if kind in FACTORY_ACTIONS:
        from android_phone_factory_tools import execute as factory_execute

        return factory_execute(action)

    if kind in ARMORY_ACTIONS:
        from android_armory_driver import execute as armory_execute

        return armory_execute(action)

    if kind in WINDOW_ACTIONS:
        from android_window_composer import execute as window_execute

        return window_execute(action)

    if kind in STATUS_TTS_ACTIONS:
        from android_phone_status_tts import execute as status_tts_execute

        return status_tts_execute(action)

    if kind in TERMUX_SHELL_ACTIONS:
        return termux_shell_execute(action)

    from android_phone_hands_bridge import act as hands_act

    return hands_act(action)


def execute_action(action):
    kind = action.get("action")

    # This is the Home Center background body lane. It must remain callable when
    # Shizuku is absent, stopped, unpaired, or otherwise broken.
    if kind in TERMUX_SHELL_ACTIONS:
        return termux_shell_execute(action)

    if kind in DIAGNOSTIC_ACTIONS:
        from android_phone_diagnostics import execute as diagnostics_execute

        return diagnostics_execute(action)

    if kind in OVERLAY_ACTIONS:
        from android_operator_overlay import execute as overlay_execute

        return overlay_execute(action)

    # Everything below this line is explicitly interactive Android/UI work.
    # Only this optional lane may consult the Shizuku-backed operator overlay.
    from android_operator_overlay import (
        control_gate as overlay_control_gate,
        screen_activity as overlay_screen_activity,
    )

    gate = overlay_control_gate()
    if kind == "status_say" and gate.get("muted"):
        return {
            "ok": True,
            "action": "status_say",
            "muted": True,
            "skipped": True,
        }

    screen = _screen_profile(action)
    if screen:
        overlay_screen_activity(screen["leaseMs"], screen["yieldMs"])
    return dispatch(action)


def loop(once=False):
    device = ensure_device()
    device_id = device["deviceId"]
    secret = device["deviceToken"]
    print(
        f"Home Center phone relay online: {device_id} "
        "(baseline transport: Termux; Shizuku optional)",
        flush=True,
    )

    while True:
        try:
            pulled = http(
                "/pull",
                {
                    "deviceId": device_id,
                    "deviceToken": secret,
                    "leaseMs": 90000,
                },
            )
            command = pulled.get("command")
            write_heartbeat(
                device_id,
                "poll_ok",
                command.get("commandId") if isinstance(command, dict) else "",
            )

            if command:
                command_id = command["commandId"]
                try:
                    result = execute_action(command.get("action") or {})
                    http(
                        "/complete",
                        {
                            "deviceId": device_id,
                            "deviceToken": secret,
                            "commandId": command_id,
                            "status": "completed",
                            "result": result,
                        },
                    )
                    write_heartbeat(device_id, "command_completed", command_id)
                    print(
                        json.dumps(
                            {"commandId": command_id, "status": "completed"}
                        ),
                        flush=True,
                    )
                except Exception as exc:
                    http(
                        "/complete",
                        {
                            "deviceId": device_id,
                            "deviceToken": secret,
                            "commandId": command_id,
                            "status": "failed",
                            "error": str(exc)[:4000],
                        },
                    )
                    write_heartbeat(device_id, "command_failed", command_id)
                    print(
                        json.dumps(
                            {
                                "commandId": command_id,
                                "status": "failed",
                                "error": str(exc),
                            }
                        ),
                        flush=True,
                    )

            if once:
                return
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print("phone-relay error: " + str(exc), file=sys.stderr, flush=True)
            if once:
                raise

        time.sleep(POLL)


if __name__ == "__main__":
    loop("--once" in sys.argv)
