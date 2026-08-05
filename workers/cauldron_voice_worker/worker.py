"""Outbound-only THECAULDRON voice worker for Helm Center.

The worker leases immutable owner-scoped tickets, renders Kokoro checkpoints, uploads
verified WAV bytes, and can recover any completed checkpoint from Helm Center after
a process or machine restart. It opens no inbound port and permits no cloud fallback.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import wave

CONTRACT_VERSION = "home-center.local-voice-farm.v1"
ENGINE_ID = "kokoro-onnx"
PROVIDER_ID = "local_cauldron"
WORKER_ID = os.environ.get("HOME_CENTER_LOCAL_VOICE_WORKER_ID", "cauldron-voice-01")


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_origin(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("HOME_CENTER_LOCAL_VOICE_ORIGIN must be one HTTPS origin.")
    return f"https://{parsed.netloc}" + parsed.path.rstrip("/")


def load_token(root: pathlib.Path) -> str:
    environment = os.environ.get("HOME_CENTER_LOCAL_VOICE_TOKEN", "").strip()
    if environment:
        return environment
    token_file = root / ".worker-token"
    if token_file.is_file():
        return token_file.read_text(encoding="utf-8").strip()
    raise ValueError("HOME_CENTER_LOCAL_VOICE_TOKEN or .worker-token is required.")


def verify_model_manifest(root: pathlib.Path) -> dict:
    manifest = json.loads((root / "model-manifest.json").read_text(encoding="utf-8"))
    if manifest["engine"]["name"] != ENGINE_ID or manifest["initialLane"]["cloningEnabled"] is not False:
        raise RuntimeError("Model manifest violates the fixed-voice pilot contract.")
    for item in manifest["model"]["files"]:
        target = root / "models" / item["name"]
        if not target.is_file() or sha256_file(target) != item["sha256"]:
            raise RuntimeError(f"Model verification failed: {item['name']}")
    return manifest


class HomeCenterClient:
    def __init__(self, origin: str, token: str):
        self.origin = checked_origin(origin)
        if not token:
            raise ValueError("Helm Center worker token is required.")
        self.token = token

    def _request(self, method: str, path: str, body: bytes = b"", content_type: str = "application/json") -> tuple[bytes, dict]:
        if not path.startswith("/local-voice-farm/v1/") or ".." in path:
            raise ValueError("Worker protocol path escaped its allowlist.")
        request = urllib.request.Request(
            self.origin + path,
            method=method,
            data=body or None,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": content_type,
                "X-Home-Center-Worker": WORKER_ID,
            },
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read(), dict(response.headers.items())

    def request_json(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload).encode() if payload is not None else b""
        data, _ = self._request(method, path, body)
        return json.loads(data.decode("utf-8")) if data else {}

    def lease(self) -> dict:
        return self.request_json("POST", "/local-voice-farm/v1/lease", {
            "workerId": WORKER_ID,
            "contractVersion": CONTRACT_VERSION,
            "capabilities": [ENGINE_ID],
        })

    def heartbeat(self, ticket_id: str, phase: str, completed: list[int]) -> None:
        safe_ticket = urllib.parse.quote(ticket_id, safe="._-")
        self.request_json("POST", f"/local-voice-farm/v1/tickets/{safe_ticket}/heartbeat", {
            "workerId": WORKER_ID,
            "phase": phase,
            "completedSegmentIndexes": completed,
        })

    def upload(self, ticket_id: str, name: str, path: pathlib.Path, sha256: str) -> dict:
        safe_ticket = urllib.parse.quote(ticket_id, safe="._-")
        safe_name = urllib.parse.quote(name, safe="._-")
        data, _ = self._request(
            "PUT",
            f"/local-voice-farm/v1/tickets/{safe_ticket}/artifacts/{safe_name}?sha256={sha256}",
            path.read_bytes(),
            "audio/wav",
        )
        return json.loads(data.decode("utf-8")) if data else {}

    def download(self, ticket_id: str, name: str, output: pathlib.Path, expected_sha256: str = "") -> dict:
        safe_ticket = urllib.parse.quote(ticket_id, safe="._-")
        safe_name = urllib.parse.quote(name, safe="._-")
        data, headers = self._request("GET", f"/local-voice-farm/v1/tickets/{safe_ticket}/artifacts/{safe_name}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as temp:
            temp.write(data)
            temp_path = pathlib.Path(temp.name)
        actual = sha256_file(temp_path)
        provider_sha = headers.get("X-Content-SHA256", headers.get("x-content-sha256", ""))
        if expected_sha256 and actual != expected_sha256:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError(f"Checkpoint SHA mismatch for {name}.")
        if provider_sha and actual != provider_sha:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError(f"Helm Center checkpoint header mismatch for {name}.")
        temp_path.replace(output)
        return {"byteCount": len(data), "sha256": actual, "recovered": True}

    def complete(self, ticket_id: str, receipt: dict) -> dict:
        safe_ticket = urllib.parse.quote(ticket_id, safe="._-")
        return self.request_json("POST", f"/local-voice-farm/v1/tickets/{safe_ticket}/complete", receipt)


def render_segment(engine, text: str, voice: str, speed: float, output: pathlib.Path) -> dict:
    import soundfile as sf

    started = time.perf_counter()
    samples, sample_rate = engine.create(text, voice=voice, speed=speed, lang="en-us")
    sf.write(output, samples, sample_rate, subtype="PCM_16")
    return {
        "durationMs": round((time.perf_counter() - started) * 1000),
        "sampleRate": sample_rate,
        "byteCount": output.stat().st_size,
        "sha256": sha256_file(output),
    }


def wav_metrics(path: pathlib.Path) -> dict:
    with wave.open(str(path), "rb") as source:
        if source.getcomptype() != "NONE" or source.getsampwidth() != 2:
            raise RuntimeError("Only PCM16 WAV checkpoints are accepted.")
        return {
            "sampleRate": source.getframerate(),
            "channels": source.getnchannels(),
            "byteCount": path.stat().st_size,
            "sha256": sha256_file(path),
        }


def stitch_pcm16(paths: list[pathlib.Path], output: pathlib.Path) -> None:
    params = None
    with wave.open(str(output), "wb") as destination:
        for path in paths:
            with wave.open(str(path), "rb") as source:
                current = (source.getnchannels(), source.getsampwidth(), source.getframerate())
                if source.getcomptype() != "NONE" or source.getsampwidth() != 2:
                    raise RuntimeError("Only PCM16 WAV checkpoints may be stitched.")
                if params is None:
                    params = current
                    destination.setnchannels(current[0])
                    destination.setsampwidth(current[1])
                    destination.setframerate(current[2])
                elif current != params:
                    raise RuntimeError("Checkpoint WAV parameters differ.")
                destination.writeframes(source.readframes(source.getnframes()))


def run_ticket(client: HomeCenterClient, root: pathlib.Path, ticket: dict) -> dict:
    request = ticket["request"]
    if request.get("contractVersion") != CONTRACT_VERSION or request.get("provider") != PROVIDER_ID or request.get("engine") != ENGINE_ID:
        raise RuntimeError("Ticket identity does not match THECAULDRON worker.")
    if request.get("voice", {}).get("kind") != "fixed":
        raise RuntimeError("Clone profiles are disabled in the fixed-voice pilot.")

    from kokoro_onnx import Kokoro

    manifest = verify_model_manifest(root)
    engine = Kokoro(str(root / "models" / "kokoro-v1.0.onnx"), str(root / "models" / "voices-v1.0.bin"))
    ticket_id = ticket["ticketId"]
    done = set(int(item) for item in (ticket.get("completedSegmentIndexes") or []))
    cache = root / "cache" / ticket_id
    cache.mkdir(parents=True, exist_ok=True)
    checkpoint_paths: list[pathlib.Path] = []
    checkpoint_receipts: list[dict] = []

    for segment in request["splitPlan"]:
        index = int(segment["index"])
        name = f"segment-{index:04d}.wav"
        output = cache / name
        recovered = False

        if index in done:
            if not output.is_file():
                client.download(ticket_id, name, output)
                recovered = True
            metrics = wav_metrics(output)
        else:
            if output.is_file():
                metrics = wav_metrics(output)
            else:
                metrics = render_segment(engine, segment["text"], manifest["initialLane"]["voice"], float(request["speed"]), output)
            upload = client.upload(ticket_id, name, output, metrics["sha256"])
            metrics = {**metrics, "artifact": upload}
            done.add(index)
            client.heartbeat(ticket_id, "synthesizing", sorted(done))

        checkpoint_paths.append(output)
        checkpoint_receipts.append({
            "index": index,
            "textSha256": segment["textSha256"],
            **metrics,
            "recovered": recovered,
        })

    final_path = cache / "final.wav"
    stitch_pcm16(checkpoint_paths, final_path)
    final_sha = sha256_file(final_path)
    final_upload = client.upload(ticket_id, "final.wav", final_path, final_sha)
    receipt = {
        "contractVersion": CONTRACT_VERSION,
        "provider": PROVIDER_ID,
        "engine": ENGINE_ID,
        "modelRevision": request["modelRevision"],
        "voiceProfileId": request["voice"]["profileId"],
        "inputSha256": request["inputSha256"],
        "textSha256": request["textSha256"],
        "segmentCheckpoints": checkpoint_receipts,
        "byteCount": final_path.stat().st_size,
        "sha256": final_sha,
        "cloudSpeechSynthesisUsed": False,
        "humanAcceptance": "unreviewed",
        "artifact": final_upload,
    }
    return client.complete(ticket_id, receipt)


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent
    if "--verify" in sys.argv:
        verify_model_manifest(root)
        print(json.dumps({"ok": True, "workerId": WORKER_ID, "engine": ENGINE_ID, "cloningEnabled": False}))
        return 0

    origin = os.environ.get("HOME_CENTER_LOCAL_VOICE_ORIGIN", "")
    client = HomeCenterClient(origin, load_token(root))
    once = "--once" in sys.argv
    deadline = time.monotonic() + 10 * 60 if once else None

    while True:
        try:
            leased = client.lease()
            ticket = leased.get("ticket")
            if ticket:
                result = run_ticket(client, root, ticket)
                print(json.dumps(result))
                if once:
                    return 0
            elif once and time.monotonic() >= deadline:
                raise RuntimeError("No Helm Center local voice ticket arrived within ten minutes.")
            else:
                time.sleep(max(2, min(30, int(leased.get("pollAfterSeconds", 5)))))
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise
            if once and deadline and time.monotonic() >= deadline:
                raise
            time.sleep(8)


if __name__ == "__main__":
    raise SystemExit(main())
