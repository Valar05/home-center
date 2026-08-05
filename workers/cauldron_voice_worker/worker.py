"""Outbound-only Cauldron voice worker.

The worker trusts one configured Home Center HTTPS origin, leases immutable tickets,
renders Kokoro segments, uploads each checkpoint, and completes only after the final
WAV digest is known. It never opens a listening socket or follows URLs from tickets.
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
    return f"https://{parsed.netloc}"


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
            raise ValueError("HOME_CENTER_LOCAL_VOICE_TOKEN is required.")
        self.token = token

    def request(self, method: str, path: str, body: bytes = b"", content_type: str = "application/json") -> dict:
        if not path.startswith("/local-voice-farm/v1/") or ".." in path:
            raise ValueError("Worker protocol path escaped its allowlist.")
        request = urllib.request.Request(
            self.origin + path,
            method=method,
            data=body or None,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": content_type, "X-Home-Center-Worker": WORKER_ID},
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read()
            return json.loads(data.decode("utf-8")) if data else {}

    def lease(self) -> dict:
        payload = json.dumps({"workerId": WORKER_ID, "contractVersion": CONTRACT_VERSION, "capabilities": [ENGINE_ID]}).encode()
        return self.request("POST", "/local-voice-farm/v1/lease", payload)

    def heartbeat(self, ticket_id: str, phase: str, completed: list[int]) -> None:
        payload = json.dumps({"workerId": WORKER_ID, "phase": phase, "completedSegmentIndexes": completed}).encode()
        self.request("POST", f"/local-voice-farm/v1/tickets/{ticket_id}/heartbeat", payload)

    def upload(self, ticket_id: str, name: str, path: pathlib.Path, sha256: str) -> dict:
        safe_name = urllib.parse.quote(name, safe="._-")
        return self.request("PUT", f"/local-voice-farm/v1/tickets/{ticket_id}/artifacts/{safe_name}?sha256={sha256}", path.read_bytes(), "audio/wav")

    def complete(self, ticket_id: str, receipt: dict) -> dict:
        return self.request("POST", f"/local-voice-farm/v1/tickets/{ticket_id}/complete", json.dumps(receipt).encode())


def render_segment(engine, text: str, voice: str, speed: float, output: pathlib.Path) -> dict:
    import soundfile as sf

    started = time.perf_counter()
    samples, sample_rate = engine.create(text, voice=voice, speed=speed, lang="en-us")
    sf.write(output, samples, sample_rate, subtype="PCM_16")
    return {"durationMs": round((time.perf_counter() - started) * 1000), "sampleRate": sample_rate, "byteCount": output.stat().st_size, "sha256": sha256_file(output)}


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


def run_ticket(client: HomeCenterClient, root: pathlib.Path, ticket: dict) -> None:
    request = ticket["request"]
    if request.get("contractVersion") != CONTRACT_VERSION or request.get("provider") != PROVIDER_ID or request.get("engine") != ENGINE_ID:
        raise RuntimeError("Ticket identity does not match the Cauldron worker.")
    if request.get("voice", {}).get("kind") != "fixed":
        raise RuntimeError("Clone profiles are disabled in the fixed-voice pilot.")
    from kokoro_onnx import Kokoro

    manifest = verify_model_manifest(root)
    engine = Kokoro(str(root / "models" / "kokoro-v1.0.onnx"), str(root / "models" / "voices-v1.0.bin"))
    ticket_id = ticket["ticketId"]
    done = set(ticket.get("completedSegmentIndexes") or [])
    checkpoint_paths = []
    checkpoint_receipts = []
    with tempfile.TemporaryDirectory(prefix="home-center-cauldron-") as temp_name:
        temp = pathlib.Path(temp_name)
        for segment in request["splitPlan"]:
            index = int(segment["index"])
            output = temp / f"segment-{index:04d}.wav"
            if index in done:
                raise RuntimeError("Resume requires server-provided checkpoint bytes; replay is forbidden.")
            metrics = render_segment(engine, segment["text"], manifest["initialLane"]["voice"], float(request["speed"]), output)
            upload = client.upload(ticket_id, output.name, output, metrics["sha256"])
            checkpoint_paths.append(output)
            checkpoint_receipts.append({"index": index, "textSha256": segment["textSha256"], **metrics, "artifact": upload})
            done.add(index)
            client.heartbeat(ticket_id, "synthesizing", sorted(done))
        final_path = temp / "final.wav"
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
        client.complete(ticket_id, receipt)


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent
    if "--verify" in sys.argv:
        verify_model_manifest(root)
        print(json.dumps({"ok": True, "workerId": WORKER_ID, "engine": ENGINE_ID, "cloningEnabled": False}))
        return 0
    client = HomeCenterClient(os.environ.get("HOME_CENTER_LOCAL_VOICE_ORIGIN", ""), os.environ.get("HOME_CENTER_LOCAL_VOICE_TOKEN", ""))
    while True:
        try:
            leased = client.lease()
            ticket = leased.get("ticket")
            if ticket:
                run_ticket(client, root, ticket)
            else:
                time.sleep(max(2, min(30, int(leased.get("pollAfterSeconds", 8)))))
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise
            time.sleep(8)


if __name__ == "__main__":
    raise SystemExit(main())
