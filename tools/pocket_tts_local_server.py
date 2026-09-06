#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = int(os.environ.get("FORTRESS_POCKET_TTS_PORT", "10205"))
REPO = Path(os.environ.get(
    "FORTRESS_HOME_CENTER",
    "/storage/emulated/0/Documents/GodotProjects/home-center",
)).resolve()
READER = REPO / "tools/fortress_read_aloud.py"
MAX_TEXT_CHARS = 12000


def run_reader(args: list[str], timeout: float) -> dict:
    if not READER.is_file():
        return {
            "ok": False,
            "faultCode": "F001_READER_MISSING",
            "detail": f"Missing canonical reader: {READER}",
        }
    proc = subprocess.run(
        [sys.executable, str(READER), *args],
        cwd=str(REPO),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    raw = (proc.stdout or "").strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "faultCode": "F051_READER_NON_JSON",
            "detail": (proc.stderr or raw or f"reader exit {proc.returncode}")[-4000:],
        }
    payload.setdefault("readerExitCode", proc.returncode)
    if proc.returncode and payload.get("ok") is True:
        payload["ok"] = False
    return payload


def doctor_payload() -> dict:
    payload = run_reader(["--doctor"], 45.0)
    payload["service"] = "pocket-tts-local"
    payload["serviceHost"] = HOST
    payload["servicePort"] = PORT
    if payload.get("ok") is True:
        payload.setdefault("faultCode", "OK")
    return payload


class Handler(BaseHTTPRequestHandler):
    server_version = "FortressPocketTTS/1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("pocket_tts_local_server " + (fmt % args) + "\n")

    def send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path not in ("/health", "/doctor"):
            self.send_json(404, {"ok": False, "faultCode": "F404_ROUTE", "detail": self.path})
            return
        payload = doctor_payload()
        self.send_json(200 if payload.get("ok") else 503, payload)

    def do_POST(self) -> None:
        if self.path != "/speak":
            self.send_json(404, {"ok": False, "faultCode": "F404_ROUTE", "detail": self.path})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_TEXT_CHARS * 4:
            self.send_json(400, {"ok": False, "faultCode": "F041_BAD_REQUEST", "detail": "invalid request length"})
            return
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as error:
            self.send_json(400, {"ok": False, "faultCode": "F041_BAD_REQUEST", "detail": str(error)})
            return
        text = " ".join(str(request.get("text", "")).split()).strip()
        if not text or len(text) > MAX_TEXT_CHARS:
            self.send_json(400, {"ok": False, "faultCode": "F041_BAD_REQUEST", "detail": "text is empty or too long"})
            return

        doctor = doctor_payload()
        if doctor.get("ok") is not True:
            doctor.setdefault("faultCode", "F050_DOCTOR_FAILED")
            self.send_json(503, doctor)
            return

        try:
            payload = run_reader([text], 360.0)
        except subprocess.TimeoutExpired:
            self.send_json(504, {"ok": False, "faultCode": "F052_SPEECH_TIMEOUT", "detail": "speech did not complete within 360 seconds"})
            return
        if payload.get("ok") is True and payload.get("playbackVerified") is True:
            payload["faultCode"] = "OK"
            self.send_json(200, payload)
            return
        payload.setdefault("faultCode", "F060_PLAYBACK_UNVERIFIED")
        self.send_json(500, payload)


def main() -> None:
    os.chdir(REPO)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(json.dumps({
        "ok": True,
        "event": "listening",
        "host": HOST,
        "port": PORT,
        "repo": str(REPO),
    }, sort_keys=True), flush=True)
    server.serve_forever(poll_interval=0.25)


if __name__ == "__main__":
    main()
