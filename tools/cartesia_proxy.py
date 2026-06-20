#!/usr/bin/env python3
import argparse
import json
import os
import struct
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from cartesia import Cartesia
except Exception as exc:  # pragma: no cover - import checked in --verify
    Cartesia = None
    CARTESIA_IMPORT_ERROR = exc
else:
    CARTESIA_IMPORT_ERROR = None

DEFAULT_MODEL_ID = os.environ.get("CARTESIA_MODEL_ID", "sonic-3.5")
DEFAULT_VOICE_ID = os.environ.get("CARTESIA_VOICE_ID", "f786b574-daa5-4673-aa0c-cbe3e8534c02")
DEFAULT_SAMPLE_RATE = int(os.environ.get("CARTESIA_SAMPLE_RATE", "44100"))
DEFAULT_HOST = os.environ.get("CARTESIA_PROXY_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("CARTESIA_PROXY_PORT", "8787"))


def read_api_key():
    return os.environ.get("CARTESIA_API_KEY", "").strip()


def ensure_ready():
    if CARTESIA_IMPORT_ERROR is not None:
        raise RuntimeError(f"cartesia package is unavailable: {CARTESIA_IMPORT_ERROR}")
    if not read_api_key():
        raise RuntimeError("CARTESIA_API_KEY is missing")


def float32_to_pcm16(data):
    usable = len(data) - (len(data) % 4)
    if usable <= 0:
        return b""
    count = usable // 4
    floats = struct.unpack("<" + "f" * count, data[:usable])
    out = bytearray(count * 2)
    for index, sample in enumerate(floats):
        clipped = max(-1.0, min(1.0, sample))
        value = int(round(clipped * 32767.0))
        if value > 32767:
            value = 32767
        elif value < -32768:
            value = -32768
        struct.pack_into("<h", out, index * 2, value)
    return bytes(out)


def build_client():
    return Cartesia(api_key=read_api_key())


def tts_stream(text, writer, model_id=DEFAULT_MODEL_ID, voice_id=DEFAULT_VOICE_ID):
    client = build_client()
    with client.tts.websocket_connect() as connection:
        ctx = connection.context(
            model_id=model_id,
            voice={"mode": "id", "id": voice_id},
            output_format={"container": "raw", "encoding": "pcm_f32le", "sample_rate": DEFAULT_SAMPLE_RATE},
        )
        ctx.push(text)
        ctx.no_more_inputs()
        for response in ctx.receive():
            if response.type == "chunk" and response.audio:
                chunk = float32_to_pcm16(response.audio)
                if chunk:
                    writer(chunk)
            elif response.type == "done":
                break


def verify():
    ensure_ready()
    return {
        "ok": True,
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "model_id": DEFAULT_MODEL_ID,
        "voice_id": DEFAULT_VOICE_ID,
        "sample_rate": DEFAULT_SAMPLE_RATE,
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path in {"/", "/health"}:
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404, "not found")

    def do_POST(self):
        if self.path != "/tts":
            self.send_error(404, "not found")
            return
        try:
            ensure_ready()
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            payload = json.loads(raw.decode("utf-8"))
            text = str(payload.get("text", "")).strip()
            if not text:
                self.send_error(400, "missing text")
                return
            model_id = str(payload.get("model_id", DEFAULT_MODEL_ID)).strip() or DEFAULT_MODEL_ID
            voice_id = str(payload.get("voice_id", DEFAULT_VOICE_ID)).strip() or DEFAULT_VOICE_ID
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Audio-Format", "pcm_s16le")
            self.send_header("X-Sample-Rate", str(DEFAULT_SAMPLE_RATE))
            self.end_headers()
            self.wfile.flush()
            tts_stream(text, lambda chunk: self._write_chunk(chunk), model_id=model_id, voice_id=voice_id)
        except Exception as exc:
            print(f"cartesia proxy stream error: {exc}")
            return

    def _write_chunk(self, chunk):
        self.wfile.write(chunk)
        self.wfile.flush()


def main():
    parser = argparse.ArgumentParser(description="Local Cartesia speech proxy for Home Center.")
    parser.add_argument("--verify", action="store_true", help="Check configuration and exit.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    if args.verify:
        print(json.dumps(verify(), indent=2, sort_keys=True))
        return 0

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Cartesia proxy listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
