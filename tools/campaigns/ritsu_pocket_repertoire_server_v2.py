"""Local Pocket TTS repertoire service. Runs only on 127.0.0.1:10205.

Preserves the existing Ritsu relay protocol and cloud-ticket sender contract.
No Qwen speech generation and no post-generation pitch shifting.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import os
import shutil
import threading
import time
import urllib.request
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from pocket_tts import TTSModel

ROOT = Path.home() / "Documents" / "Codex" / "Venice" / "PocketTTS"
CAND = ROOT / "voice-candidates"
QWEN_COMPAT_AUTH = Path.home() / "workspace" / "ritsu-faster-qwen3-tts" / "ritsu-api-token.txt"
RELAY = ROOT / "embodiment_campaign"
RELAY_OUTPUT = Path.home() / "workspace" / "ritsu-chatterbox-turbo" / "generated"
OUTPUT = ROOT / "ritsu-pocket-repertoire-output"
ALIASES = {"normal": "normal", "warm": "normal", "delighted": "delighted",
           "happy": "delighted", "amused": "amused", "somber": "somber",
           "upset": "somber", "whisper": "whisper"}
STATES = {
    "normal": (CAND / "fullset-20261023" / "warm-minus1.safetensors",
               "043D61FCA49B175C88A41734D1A659ED9655D39BDE8BD5FA2038AFC35D7FBB36"),
    "delighted": (CAND / "fullset-20261023" / "delighted-minus1.safetensors",
                  "050A501F67F83A3876183BEFD649806265B844BFC13BB21D967FC37C0456427A"),
    "amused": (CAND / "fullset-20261023" / "amused-minus1.safetensors",
               "6F878B05D4227E10B43BB0AA8A87C6CBDF909B9CCA0F4A845E28C6541F17D9FE"),
    "somber": (CAND / "fullset-20261023" / "somber-minus1.safetensors",
               "51C7B4F55361082ED23ABB56E1F7E9878D4CA26DA5740349858BDBDF2A4CA0BD"),
    "whisper": (CAND / "ritsu-whisper-approved-minus1-20261023.safetensors",
                "B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5"),
}
VERSION = "ritsu-pocket-repertoire-v2-20261023"
STARTED = time.time()
LOCK = threading.RLock()
JOBS: dict[str, dict] = {}
EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ritsu-pocket")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def filehash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest().upper()


def check_states() -> None:
    if not QWEN_COMPAT_AUTH.is_file():
        raise RuntimeError("Existing private Ritsu API token missing")
    for key, (path, expected) in STATES.items():
        if not path.is_file() or filehash(path) != expected:
            raise RuntimeError("Missing or changed approved Pocket state: " + key)
    if not (RELAY / "relay-token.txt").is_file():
        raise RuntimeError("Canonical phone relay credentials missing")


def canonical(profile: str) -> str:
    value = ALIASES.get(profile)
    if value is None:
        raise HTTPException(status_code=400, detail="Unknown registered Ritsu voice profile")
    return value


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    profile: str = "normal"


class JobRequest(BaseModel):
    text: str = Field(min_length=1, max_length=450)
    speaker: str = "normal"


class Delivery(BaseModel):
    job_id: str = Field(min_length=16, max_length=64)


def make_app(model: TTSModel, states: dict) -> FastAPI:
    app = FastAPI(title="Ritsu Pocket repertoire", version=VERSION)
    auth_token = QWEN_COMPAT_AUTH.read_text(encoding="utf-8").strip()
    model_lock = threading.Lock()
    samplerate = int(model.config.mimi.sample_rate)

    def require_auth(header: str | None) -> None:
        if not header or not hmac.compare_digest(header, "Bearer " + auth_token):
            raise HTTPException(status_code=401, detail="Unauthorized")

    def render(text: str, profile: str) -> bytes:
        which = canonical(profile)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty speech")
        with model_lock:
            signal = model.generate_audio(model_state=states[which], text_to_generate=text.strip())
        pcm = np.asarray(signal.detach().cpu().float().numpy(), dtype=np.float32).reshape(-1)
        if not len(pcm) or not np.isfinite(pcm).all() or np.max(np.abs(pcm)) >= 2:
            raise RuntimeError("Generated audio failed sample validation")
        result = np.rint(np.clip(pcm, -1, 1 - 1/32768) * 32768).astype("<i2")
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(samplerate)
            output.writeframes(result.tobytes())
        return buffer.getvalue()

    @app.get("/health")
    def health():
        return {"status": "ready", "engine": "pocket-tts", "model": "loaded",
                "version": VERSION, "default": "normal", "profiles": ALIASES,
                "stateSha256": {name: row[1] for name, row in STATES.items()},
                "sampleRate": samplerate, "pid": os.getpid(),
                "uptimeSeconds": round(time.time() - STARTED, 2)}

    @app.post("/tts")
    def tts(request: Speech):
        wav = render(request.text, request.profile)
        return Response(content=wav, media_type="audio/wav",
                        headers={"X-TTS-Engine": "pocket-tts",
                                 "X-Ritsu-Profile": canonical(request.profile),
                                 "X-Ritsu-Voice-SHA256": STATES[canonical(request.profile)][1]})

    @app.get("/v1/health")
    def api_health(authorization: str | None = Header(default=None)):
        require_auth(authorization)
        return {"ok": True, "model": "loaded", "engine": "pocket-tts",
                "error": None, "queue": sum(x["state"] in ("queued", "generating") for x in JOBS.values()),
                "version": VERSION}

    @app.get("/v1/voices")
    def voices(authorization: str | None = Header(default=None)):
        require_auth(authorization)
        return {"default": "normal", "speakers": list(ALIASES), "aliases": ALIASES,
                "engine": "pocket-tts", "version": VERSION}

    def generate_job(jid: str, text: str, speaker: str):
        with LOCK:
            JOBS[jid]["state"] = "generating"
        started = time.monotonic()
        try:
            audio = render(text, speaker)
            OUTPUT.mkdir(parents=True, exist_ok=True)
            path = OUTPUT / (jid + ".wav")
            with path.open("xb") as writer:
                writer.write(audio)
            with wave.open(io.BytesIO(audio), "rb") as w:
                sec = w.getnframes() / w.getframerate()
            with LOCK:
                JOBS[jid].update(state="completed", generation_seconds=round(time.monotonic()-started, 2),
                                  audio_seconds=round(sec, 2), bytes=len(audio))
        except Exception:
            with LOCK:
                JOBS[jid].update(state="failed", error="Pocket synthesis failure")

    @app.post("/v1/speak")
    def speak(request: JobRequest, authorization: str | None = Header(default=None)):
        require_auth(authorization)
        canonical(request.speaker)
        with LOCK:
            active = sum(row["state"] in ("queued", "generating") for row in JOBS.values())
            if active >= 12:
                raise HTTPException(status_code=429, detail="Voice queue full")
            jid = uuid.uuid4().hex
            JOBS[jid] = {"id": jid, "state": "queued", "text": request.text,
                         "speaker": request.speaker, "delivery": None}
            output = dict(JOBS[jid])
        EXECUTOR.submit(generate_job, jid, request.text, request.speaker)
        return Response(content=json.dumps(output), status_code=202, media_type="application/json")

    @app.get("/v1/jobs/{jid}")
    def get_job(jid: str, authorization: str | None = Header(default=None)):
        require_auth(authorization)
        with LOCK:
            row = JOBS.get(jid)
            if not row: raise HTTPException(status_code=404, detail="Unknown job")
            return dict(row)

    @app.post("/v1/deliver")
    def deliver(request: Delivery, authorization: str | None = Header(default=None)):
        require_auth(authorization)
        with LOCK:
            job = JOBS.get(request.job_id)
            if not job or job["state"] != "completed":
                raise HTTPException(status_code=400, detail="Job not completed")
            if job.get("delivery"):
                return job["delivery"]
        path = OUTPUT / (request.job_id + ".wav")
        if not path.is_file():
            raise HTTPException(status_code=500, detail="Generated WAV absent")
        RELAY_OUTPUT.mkdir(parents=True, exist_ok=True)
        name = "ritsu-pocket-" + request.job_id + ".wav"
        shutil.copyfile(path, RELAY_OUTPUT / name)
        # Reuses the established file-backed relay path; no Qwen/Turbo synthesis.
        token = (RELAY / "relay-token.txt").read_text(encoding="utf-8").strip()
        payload = json.dumps({"text": "__TURBO_WAV__:" + name, "character": "ritsu"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:19643/enqueue",
              data=payload, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with OPENER.open(req, timeout=15) as response:
            receipt = json.load(response)
        if not receipt.get("id"):
            raise HTTPException(status_code=502, detail="Relay receipt missing")
        result = {"state": "enqueued", "relay_id": receipt["id"]}
        with LOCK:
            JOBS[request.job_id]["delivery"] = result
        return result

    return app


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=10205)
    args = p.parse_args()
    if args.host != "127.0.0.1":
        p.error("Pocket repertoire is loopback only")
    check_states()
    model = TTSModel.load_model(language="english")
    model.to("cpu")
    states = {name: model.get_state_for_audio_prompt(path) for name, (path, _) in STATES.items()}
    uvicorn.run(make_app(model, states), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
