#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import time
from collections import deque
from pathlib import Path

STATE = Path(os.environ.get("HC_ADAM_AUDIO_STATE", "~/.local/state/home-center/adam-audio")).expanduser()
RING = STATE / "ring"
EVENTS = STATE / "events"
INDEX = STATE / "events.jsonl"
PID = STATE / "daemon.pid"
ENABLED = STATE / "enabled"

SEGMENT_SECONDS = max(2, min(int(os.environ.get("HC_ADAM_AUDIO_SEGMENT_SECONDS", "6")), 30))
RING_SECONDS = max(SEGMENT_SECONDS * 2, min(int(os.environ.get("HC_ADAM_AUDIO_RING_SECONDS", "120")), 900))
SAMPLE_RATE = int(os.environ.get("HC_ADAM_AUDIO_SAMPLE_RATE", "16000"))
MAX_PROMOTED_SECONDS = max(1, min(int(os.environ.get("HC_ADAM_AUDIO_EVENT_SECONDS", "12")), 30))
MAX_EVENTS = max(8, min(int(os.environ.get("HC_ADAM_AUDIO_MAX_EVENTS", "200")), 2000))
INTEREST_THRESHOLD = float(os.environ.get("HC_ADAM_AUDIO_INTEREST_THRESHOLD", "0.68"))


def mkdirs():
    for path in (STATE, RING, EVENTS):
        path.mkdir(parents=True, exist_ok=True)


def set_enabled(value: bool):
    mkdirs(); ENABLED.write_text("1\n" if value else "0\n", encoding="utf-8")


def enabled():
    return not ENABLED.exists() or ENABLED.read_text(encoding="utf-8").strip() not in {"0", "off", "false"}


def run(command, timeout=60, binary=False):
    p = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return p.returncode, p.stdout if binary else p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def capture(path: Path, seconds=SEGMENT_SECONDS):
    if not shutil.which("termux-microphone-record"):
        raise RuntimeError("termux-microphone-record unavailable")
    command = ["termux-microphone-record", "-f", str(path), "-l", str(int(seconds)), "-e", "aac", "-r", str(SAMPLE_RATE), "-c", "1"]
    rc, out, err = run(command, timeout=seconds + 20)
    if rc != 0 or not path.exists() or path.stat().st_size == 0:
        raise RuntimeError((err or out or f"microphone recorder exit {rc}")[-1200:])
    return path


def pcm(path: Path):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg unavailable")
    rc, raw, err = run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"], timeout=30, binary=True)
    if rc != 0:
        raise RuntimeError(err[-1200:])
    count = len(raw) // 2
    return struct.unpack("<" + "h" * count, raw[: count * 2]) if count else ()


def goertzel(samples, freq):
    if not samples:
        return 0.0
    stride = max(1, len(samples) // 8192)
    data = samples[::stride]
    rate = SAMPLE_RATE / stride
    omega = 2.0 * math.pi * min(freq, rate * 0.45) / rate
    coeff = 2.0 * math.cos(omega)
    q0 = q1 = q2 = 0.0
    for sample in data:
        x = sample / 32768.0
        q0 = coeff * q1 - q2 + x
        q2, q1 = q1, q0
    power = max(0.0, q1 * q1 + q2 * q2 - coeff * q1 * q2)
    return math.sqrt(power) / max(1.0, len(data))


def analyze(samples):
    if not samples:
        return {"silence": True, "rms": 0.0, "peak": 0.0, "zcr": 0.0, "low": 0.0, "mid": 0.0, "high": 0.0, "transient": 0.0, "pulse": 0.0}
    norm = [x / 32768.0 for x in samples]
    rms = math.sqrt(sum(x * x for x in norm) / len(norm))
    peak = max(abs(x) for x in norm)
    zcr = sum(1 for a, b in zip(norm, norm[1:]) if (a < 0 <= b) or (a >= 0 > b)) / max(1, len(norm) - 1)
    low = sum(goertzel(samples, f) for f in (90, 180, 350))
    mid = sum(goertzel(samples, f) for f in (700, 1400, 2800))
    high = sum(goertzel(samples, f) for f in (4200, 6200))
    frame = max(64, SAMPLE_RATE // 50)
    envelope = []
    for i in range(0, len(norm), frame):
        part = norm[i:i + frame]
        if part:
            envelope.append(math.sqrt(sum(x * x for x in part) / len(part)))
    transient = 0.0 if not envelope else min(1.0, max(envelope) / max(0.04, (sum(envelope) / len(envelope)) * 5.0))
    pulse = 0.0
    if len(envelope) >= 20:
        mean = sum(envelope) / len(envelope)
        centered = [x - mean for x in envelope]
        denom = sum(x * x for x in centered) or 1.0
        candidates = []
        for lag in range(5, min(len(centered) // 2, 50)):
            corr = sum(centered[i] * centered[i - lag] for i in range(lag, len(centered))) / denom
            candidates.append(corr)
        pulse = max(0.0, min(1.0, max(candidates, default=0.0)))
    return {
        "silence": rms < 0.012,
        "rms": round(rms, 5), "peak": round(peak, 5), "zcr": round(zcr, 5),
        "low": round(low, 6), "mid": round(mid, 6), "high": round(high, 6),
        "transient": round(transient, 5), "pulse": round(pulse, 5),
    }


def interest(features):
    if features["silence"]:
        return 0.0
    total = max(features["low"] + features["mid"] + features["high"], 1e-6)
    spectral_shape = max(features["low"], features["mid"], features["high"]) / total
    score = 0.28 * min(1.0, features["rms"] * 5.0)
    score += 0.26 * features["transient"]
    score += 0.22 * features["pulse"]
    score += 0.14 * min(1.0, features["zcr"] * 4.0)
    score += 0.10 * spectral_shape
    return round(min(1.0, score), 4)


def graph_from(features):
    total = max(features["low"] + features["mid"] + features["high"], 1e-6)
    bass = features["low"] / total
    bright = features["high"] / total
    nodes = []
    if bass > 0.45:
        nodes.append({"id": "body", "type": "oscillator", "wave": "sine", "frequency": 80 + int(140 * bass)})
    if bright > 0.32 or features["zcr"] > 0.16:
        nodes.append({"id": "texture", "type": "noise", "kind": "white", "gain": round(min(0.8, 0.2 + bright), 3)})
    if not nodes:
        nodes.append({"id": "tone", "type": "oscillator", "wave": "triangle", "frequency": 440})
    nodes.append({"id": "shape", "type": "envelope", "attackMs": 8 if features["transient"] > 0.65 else 80, "decayMs": 220, "sustain": 0.35, "releaseMs": 350})
    if features["pulse"] > 0.5:
        nodes.append({"id": "pulse", "type": "modulator", "shape": "square", "rateHz": round(1.5 + 4.5 * features["pulse"], 2), "depth": 0.55})
    nodes.append({"id": "out", "type": "gain", "gain": round(min(0.9, max(0.12, features["rms"] * 2.0)), 3)})
    return {"schema": "adam-sound-graph-v1", "nodes": nodes, "features": features, "renderTarget": "mono"}


def promote(path: Path, features, score):
    mkdirs()
    stamp = f"{int(time.time() * 1000)}-{hashlib.sha256(path.read_bytes()).hexdigest()[:10]}"
    clip = EVENTS / f"{stamp}{path.suffix}"
    shutil.copy2(path, clip)
    graph = graph_from(features)
    graph_path = EVENTS / f"{stamp}.graph.json"
    graph_path.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    event = {"schema": "adam-audio-event-v1", "id": stamp, "at": time.time(), "interest": score, "features": features, "clip": str(clip), "graph": str(graph_path), "sha256": hashlib.sha256(clip.read_bytes()).hexdigest()}
    with INDEX.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")
    prune_events()
    return event


def prune_ring():
    keep = max(2, math.ceil(RING_SECONDS / SEGMENT_SECONDS))
    chunks = sorted(RING.glob("*.*"), key=lambda p: p.stat().st_mtime)
    for path in chunks[:-keep]:
        path.unlink(missing_ok=True)


def prune_events():
    clips = sorted(EVENTS.glob("*.m4a"), key=lambda p: p.stat().st_mtime)
    for clip in clips[:-MAX_EVENTS]:
        stem = clip.stem
        clip.unlink(missing_ok=True)
        (EVENTS / f"{stem}.graph.json").unlink(missing_ok=True)
    if INDEX.exists():
        rows = INDEX.read_text(encoding="utf-8", errors="replace").splitlines()[-MAX_EVENTS:]
        INDEX.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def one():
    mkdirs()
    path = RING / f"{int(time.time() * 1000)}.m4a"
    capture(path)
    features = analyze(pcm(path))
    score = interest(features)
    event = promote(path, features, score) if score >= INTEREST_THRESHOLD else None
    prune_ring()
    return {"ok": True, "chunk": str(path), "features": features, "interest": score, "promoted": event}


def daemon():
    mkdirs(); PID.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    try:
        while enabled():
            try:
                one()
            except Exception as exc:
                with (STATE / "errors.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"at": time.time(), "error": f"{type(exc).__name__}: {exc}"}) + "\n")
                time.sleep(2)
    finally:
        PID.unlink(missing_ok=True)


def status():
    mkdirs()
    pid = int(PID.read_text().strip()) if PID.exists() and PID.read_text().strip().isdigit() else None
    alive = bool(pid and Path(f"/proc/{pid}").exists())
    return {"ok": True, "enabled": enabled(), "running": alive, "pid": pid, "ringSeconds": RING_SECONDS, "segmentSeconds": SEGMENT_SECONDS, "ringChunks": len(list(RING.glob("*.*"))), "events": len(list(EVENTS.glob("*.m4a"))), "interestThreshold": INTEREST_THRESHOLD, "rawAudioPolicy": "rolling-ring-only; only interesting bounded clips promoted", "speechRecognition": False, "graphSchema": "adam-sound-graph-v1"}


def start():
    mkdirs(); set_enabled(True)
    current = status()
    if current["running"]:
        return current
    log = open(STATE / "daemon.log", "ab", buffering=0)
    process = subprocess.Popen([os.environ.get("PYTHON", "python3"), str(Path(__file__).resolve()), "daemon"], stdout=log, stderr=log, start_new_session=True)
    time.sleep(0.15)
    return {**status(), "startedPid": process.pid}


def stop():
    set_enabled(False)
    return status()


def main():
    parser = argparse.ArgumentParser(prog="adam-audio")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "stop", "status", "once", "daemon"):
        sub.add_parser(name)
    args = parser.parse_args()
    if args.command == "start": result = start()
    elif args.command == "stop": result = stop()
    elif args.command == "status": result = status()
    elif args.command == "once": result = one()
    else:
        daemon(); return 0
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
