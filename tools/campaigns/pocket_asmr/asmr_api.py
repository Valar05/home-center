#!/usr/bin/env python3
"""Small authenticated offline-audio gateway for THECAULDRON.
Uses existing Pocket /v1/speak and /v1/jobs API; never executes shell commands.
Install as an ADDITIONAL private Tailscale endpoint, not a replacement for live relay.
"""
import hashlib, hmac, json, os, re, threading, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPSTREAM = os.environ.get("POCKET_API_LOCAL", "http://127.0.0.1:10205").rstrip("/")
UPSTREAM_TOKEN_FILE = Path(os.environ.get("POCKET_API_TOKEN_FILE", r"C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu-api-token.txt"))
GATEWAY_TOKEN_FILE = Path(os.environ.get("POCKET_ASMR_TOKEN_FILE", str(Path.home() / "PocketASMR" / "gateway-token.txt")))
OUTPUT = Path(os.environ.get("POCKET_API_OUTPUT", r"C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu-api-output"))
HOST = os.environ.get("POCKET_ASMR_BIND", "127.0.0.1")
PORT = int(os.environ.get("POCKET_ASMR_PORT", "10215"))
PROFILES = {"normal", "whisper", "amused", "happy", "somber", "upset"}
ID = re.compile(r"[a-f0-9]{16,80}\Z")
SIZE_LIMIT = 200000
LOCK = threading.Lock()

def query(method, route, obj=None):
    token = UPSTREAM_TOKEN_FILE.read_text(encoding="utf-8").strip()
    payload = json.dumps(obj).encode("utf-8") if obj is not None else None
    req = urllib.request.Request(UPSTREAM + route, data=payload, method=method, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=40) as response:
        return json.load(response)

class Handler(BaseHTTPRequestHandler):
    def answer(self, status, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def auth(self):
        try:
            expected = GATEWAY_TOKEN_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            self.answer(503, {"error": "Gateway token not configured"})
            return False
        given = self.headers.get("Authorization", "")
        if not expected or not hmac.compare_digest(given, "Bearer " + expected):
            self.answer(401, {"error": "Unauthorized"})
            return False
        return True

    def do_POST(self):
        if not self.auth(): return
        if self.path != "/asmr/jobs":
            return self.answer(404, {"error": "Not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > SIZE_LIMIT: return self.answer(413, {"error": "Payload size"})
            item = json.loads(self.rfile.read(length))
            text = item.get("text", "")
            profile = item.get("voice", "whisper")
            if not isinstance(text, str) or not text.strip() or len(text) > 450:
                return self.answer(422, {"error": "A segment must contain 1 to 450 characters"})
            if profile not in PROFILES: return self.answer(422, {"error": "Invalid voice"})
            # One segment per existing Pocket job; complete ASMR episodes need many requests.
            response = query("POST", "/v1/speak", {"text": text, "speaker": profile})
            return self.answer(202, response)
        except Exception as e:
            return self.answer(502, {"error": type(e).__name__, "detail": str(e)[:160]})

    def do_GET(self):
        if not self.auth(): return
        if self.path == "/asmr/health":\n            try: return self.answer(200, {"gateway":"online","upstream":query("GET","/v1/health")})\n            except Exception: return self.answer(503, {"gateway":"online","upstream":"unavailable"})\n        m = re.fullmatch(r"/asmr/jobs/([a-f0-9]{16,80})(/audio)?", self.path)
        if not m: return self.answer(404, {"error": "Not found"})
        job, audio = m.groups()
        try:
            state = query("GET", "/v1/jobs/" + job)
            if not audio: return self.answer(200, state)
            if state.get("state") != "completed": return self.answer(409, {"error": "Not complete"})
            path = OUTPUT / (job + ".wav")
            if not path.is_file(): return self.answer(404, {"error": "Expected WAV not present; verify API output naming"})
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(path.stat().st_size))
            self.end_headers()
            with path.open("rb") as stream:
                while True:
                    chunk = stream.read(65536)
                    if not chunk: break
                    self.wfile.write(chunk)
        except Exception as e:
            return self.answer(502, {"error": type(e).__name__, "detail": str(e)[:160]})

if __name__ == "__main__":
    if not GATEWAY_TOKEN_FILE.is_file():
        raise SystemExit("Create gateway-token.txt privately before starting; no generated credentials in Git")
    print(f"Pocket ASMR API listening at http://{HOST}:{PORT}, no shell execution", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
