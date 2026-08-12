#!/data/data/com.termux/files/usr/bin/python
"""Home Center Android Phone Hands bridge.

Runs inside Termux, executes Android-shell operations through Shizuku/rish, and
accepts only authenticated requests arriving from Tailscale address space.

This is intentionally a small transport adapter. Home Center remains the
orchestrator; the phone remains an execution body.
"""
from __future__ import annotations

import base64
import hmac
import ipaddress
import json
import os
import shlex
import shutil
import subprocess
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

HOST = os.environ.get("HC_PHONE_HANDS_BIND", "0.0.0.0")
PORT = int(os.environ.get("HC_PHONE_HANDS_PORT", "8787"))
TOKEN = os.environ.get("HC_PHONE_HANDS_TOKEN", "")
ALLOW_SHELL = os.environ.get("HC_PHONE_HANDS_ALLOW_SHELL", "0") == "1"
ALLOW_NON_TAILNET = os.environ.get("HC_PHONE_HANDS_ALLOW_NON_TAILNET", "0") == "1"
MAX_BODY = int(os.environ.get("HC_PHONE_HANDS_MAX_BODY", str(256 * 1024)))
COMMAND_TIMEOUT = float(os.environ.get("HC_PHONE_HANDS_COMMAND_TIMEOUT", "12"))

TAILNET_V4 = ipaddress.ip_network("100.64.0.0/10")
TAILNET_V6 = ipaddress.ip_network("fd7a:115c:a1e0::/48")


def find_rish() -> str:
    explicit = os.environ.get("RISH")
    candidates = [explicit, shutil.which("rish"), os.path.expanduser("~/bin/rish"), os.path.expanduser("~/rish"), "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish", "/storage/emulated/0/Documents/rish", "/storage/emulated/0/Download/rish"]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate): return candidate
    raise RuntimeError("rish not found; export it from Shizuku into Termux")

RISH = find_rish()

def run_rish(command: str, *, binary: bool = False, timeout: float | None = None) -> bytes | str:
    result = subprocess.run([RISH, "-c", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout or COMMAND_TIMEOUT, check=False)
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", "replace").strip(); out = result.stdout.decode("utf-8", "replace").strip()
        raise RuntimeError(err or out or f"rish command failed ({result.returncode})")
    return result.stdout if binary else result.stdout.decode("utf-8", "replace")

def peer_is_tailnet(value: str) -> bool:
    if ALLOW_NON_TAILNET: return True
    try: addr = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError: return False
    return addr in TAILNET_V4 or addr in TAILNET_V6

def foreground() -> str: return str(run_rish("dumpsys window 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' | head -2")).strip()
def display_size() -> str: return str(run_rish("wm size | tail -1")).strip()
def battery() -> dict[str, str]:
    raw = str(run_rish("dumpsys battery | grep -E 'level:|status:|temperature:|powered:'")); parsed = {}
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.strip().split(":", 1); parsed[key.strip()] = value.strip()
    return parsed

def ui_dump() -> str:
    path = f"/data/local/tmp/home-center-ui-{uuid.uuid4().hex}.xml"; command = f"uiautomator dump {shlex.quote(path)} >/dev/null && cat {shlex.quote(path)}; rm -f {shlex.quote(path)}"
    return str(run_rish(command, timeout=20)).strip()
def screenshot_b64() -> str:
    payload = run_rish("screencap -p", binary=True, timeout=20); assert isinstance(payload, bytes); return base64.b64encode(payload).decode("ascii")

def observe(include_ui: bool, include_screen: bool) -> dict[str, Any]:
    data = {"ok": True,"timestamp": time.time(),"foreground": foreground(),"display": display_size(),"battery": battery(),"capabilities": ["observe.foreground","observe.ui","observe.screenshot","input.tap","input.swipe","input.text","input.keyevent","app.launch","app.open_uri","app.force_stop","nav.home","nav.back","nav.recents"] + (["shell.android"] if ALLOW_SHELL else [])}
    if include_ui: data["ui_xml"] = ui_dump()
    if include_screen: data["screenshot_png_base64"] = screenshot_b64()
    return data

def integer(body: dict[str, Any], key: str) -> int:
    value = body.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)): raise ValueError(f"{key} must be numeric")
    return int(value)

def act(body: dict[str, Any]) -> dict[str, Any]:
    action = body.get("action")
    if not isinstance(action, str): raise ValueError("action is required")
    if action == "tap": cmd = f"input tap {integer(body, 'x')} {integer(body, 'y')}"
    elif action == "swipe":
        duration = max(1, min(integer(body, "duration_ms") if "duration_ms" in body else 300, 10000)); cmd = f"input swipe {integer(body, 'x1')} {integer(body, 'y1')} {integer(body, 'x2')} {integer(body, 'y2')} {duration}"
    elif action == "text":
        value = body.get("text")
        if not isinstance(value, str): raise ValueError("text must be a string")
        encoded = value.replace("%", "%25").replace(" ", "%s"); cmd = f"input text {shlex.quote(encoded)}"
    elif action == "keyevent":
        key = body.get("key")
        if not isinstance(key, (str, int)): raise ValueError("key must be a keycode or Android key name")
        cmd = f"input keyevent {shlex.quote(str(key))}"
    elif action == "home": cmd = "input keyevent KEYCODE_HOME"
    elif action == "back": cmd = "input keyevent KEYCODE_BACK"
    elif action == "recents": cmd = "input keyevent KEYCODE_APP_SWITCH"
    elif action == "launch":
        package = body.get("package"); component = body.get("component")
        if component:
            if not isinstance(component, str): raise ValueError("component must be a string")
            cmd = f"am start -n {shlex.quote(component)}"
        elif isinstance(package, str): cmd = f"monkey -p {shlex.quote(package)} -c android.intent.category.LAUNCHER 1 >/dev/null"
        else: raise ValueError("launch requires package or component")
    elif action == "open_uri":
        uri = body.get("uri"); package = body.get("package")
        if not isinstance(uri, str) or not uri.strip(): raise ValueError("open_uri requires uri")
        if len(uri) > 4096: raise ValueError("uri too long")
        cmd = f"am start -a android.intent.action.VIEW -d {shlex.quote(uri)}"
        if package is not None:
            if not isinstance(package, str) or not package.strip(): raise ValueError("package must be non-empty string")
            cmd += f" -p {shlex.quote(package)}"
    elif action == "force_stop":
        package = body.get("package")
        if not isinstance(package, str): raise ValueError("package must be a string")
        cmd = f"am force-stop {shlex.quote(package)}"
    elif action == "shell":
        if not ALLOW_SHELL: raise PermissionError("shell action disabled; set HC_PHONE_HANDS_ALLOW_SHELL=1 explicitly")
        command = body.get("command")
        if not isinstance(command, str) or not command.strip(): raise ValueError("command must be a non-empty string")
        cmd = command
    else: raise ValueError(f"unsupported action: {action}")
    output = str(run_rish(cmd)).strip()
    return {"ok": True,"action": action,"output": output,"foreground": foreground(),"timestamp": time.time()}

class Handler(BaseHTTPRequestHandler):
    server_version = "HomeCenterPhoneHands/1"
    def log_message(self, fmt: str, *args: Any) -> None: print(f"{self.client_address[0]} {fmt % args}")
    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"); self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(raw)
    def authorized(self) -> bool:
        if not peer_is_tailnet(self.client_address[0]): self.send_json(403, {"ok": False, "error": "request did not arrive from Tailscale address space"}); return False
        if not TOKEN: self.send_json(503, {"ok": False, "error": "HC_PHONE_HANDS_TOKEN is not configured"}); return False
        supplied = self.headers.get("Authorization", ""); expected = f"Bearer {TOKEN}"
        if not hmac.compare_digest(supplied, expected): self.send_json(401, {"ok": False, "error": "unauthorized"}); return False
        return True
    def do_GET(self) -> None:
        if not self.authorized(): return
        try:
            if self.path == "/v1/health": self.send_json(200, {"ok": True,"service": "android-phone-hands","rish": RISH,"shizuku_probe": str(run_rish("id; pm path moe.shizuku.privileged.api | head -1")).strip(),"shell_enabled": ALLOW_SHELL}); return
            if self.path.startswith("/v1/observe"): self.send_json(200, observe("ui=1" in self.path, "screen=1" in self.path)); return
            self.send_json(404, {"ok": False, "error": "not found"})
        except Exception as exc: self.send_json(500, {"ok": False, "error": str(exc)})
    def do_POST(self) -> None:
        if not self.authorized(): return
        if self.path != "/v1/act": self.send_json(404, {"ok": False, "error": "not found"}); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY: raise ValueError("invalid request body size")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict): raise ValueError("JSON body must be an object")
            self.send_json(200, act(body))
        except PermissionError as exc: self.send_json(403, {"ok": False, "error": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc: self.send_json(400, {"ok": False, "error": str(exc)})
        except Exception as exc: self.send_json(500, {"ok": False, "error": str(exc)})

def main() -> None:
    if not TOKEN: raise SystemExit("Refusing to start without HC_PHONE_HANDS_TOKEN")
    print(f"Home Center Android Phone Hands listening on {HOST}:{PORT}"); print("Ingress policy: Tailscale CGNAT/ULA only" if not ALLOW_NON_TAILNET else "WARNING: non-tailnet ingress explicitly enabled"); print(f"rish: {RISH}; shell action: {'enabled' if ALLOW_SHELL else 'disabled'}"); ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
if __name__ == "__main__": main()
