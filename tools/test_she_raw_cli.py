#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "she_raw_cli.py"
ADAM = ROOT / "tools" / "adam.py"


class Handler(BaseHTTPRequestHandler):
    seen = []
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        payload = json.loads(body)
        self.__class__.seen.append(payload)
        speech = "RAW She Raw bytes — unchanged."
        data = json.dumps({"choices": [{"message": {"content": speech}}]}, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *_args):
        pass


def main():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            private = td / "private.md"
            aliases = td / "aliases.json"
            private.write_text("Drew protects June.\n", encoding="utf-8")
            aliases.write_text(json.dumps({"Drew": "Rowan", "June": "Mara"}), encoding="utf-8")
            env = os.environ.copy()
            env.update({
                "HC_STATE_DIR": str(td / "state"),
                "HC_SHE_RAW_PRIVATE_CONTEXT": str(private),
                "HC_SHE_RAW_ALIASES": str(aliases),
                "HC_SHE_RAW_LLM_URL": f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
                "HC_SHE_RAW_MODEL": "fixture-local",
            })
            raw = "Keep  two spaces; don't rewrite me."
            p = subprocess.run([sys.executable, str(CLI), "--json", raw], cwd=ROOT, env=env, text=True, capture_output=True)
            assert p.returncode == 0, p.stderr
            result = json.loads(p.stdout)
            assert result["speech"] == "RAW She Raw bytes — unchanged."
            assert result["receipt"]["user"]["transformedByCli"] is False
            assert result["receipt"]["speech"]["transformedByCli"] is False
            sent = Handler.seen[-1]["messages"]
            assert sent[-1] == {"role": "user", "content": raw}
            private_system = "\n".join(x["content"] for x in sent if x["role"] == "system")
            assert "Ferociously Invitable" in private_system
            assert result["receipt"]["context"]["judgmentJarSha256"]
            assert "Rowan protects Mara" in private_system
            assert "Drew protects June" not in private_system
            assert result["receipt"]["speech"]["cloudFallback"] is False
            assert Path(result["receiptPath"]).is_file()

            routed = subprocess.run([sys.executable, str(ADAM), "she-raw", "router raw"], cwd=ROOT, env=env, text=True, capture_output=True)
            assert routed.returncode == 0, routed.stderr
            assert routed.stdout == "RAW She Raw bytes — unchanged."
            assert "speech sha256" in routed.stderr

            repl = subprocess.run([sys.executable, str(ADAM), "she-raw"], cwd=ROOT, env=env, input="/quit\n", text=True, capture_output=True, timeout=5)
            assert repl.returncode == 0, repl.stderr
            assert "She Raw local." in repl.stdout

            bad = subprocess.run([sys.executable, str(CLI), "--url", "https://example.com/v1/chat/completions", "hello"], cwd=ROOT, env=env, text=True, capture_output=True)
            assert bad.returncode == 3
            assert "loopback" in bad.stderr
    finally:
        server.shutdown()
    print("Adam She Raw CLI contract: PASS")


if __name__ == "__main__":
    main()
