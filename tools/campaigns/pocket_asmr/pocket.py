#!/usr/bin/env python3
"""Pocket ASMR offline job runner. Stdlib only; never touches live phone relay."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
import wave

HOME = Path(os.environ.get("POCKET_ASMR_HOME", str(Path.home() / "PocketASMR"))).expanduser()
JOBS = HOME / "jobs"
CONFIG = HOME / "renderer.json"
VOICES = {"normal", "whisper", "amused", "happy", "somber", "upset"}
JOB_RE = re.compile(r"^[a-zA-Z0-9_-]{8,80}$")

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

def folder(job):
    if not JOB_RE.fullmatch(job):
        raise ValueError("Invalid job id")
    return JOBS / job

def read(job):
    return json.loads((folder(job) / "status.json").read_text(encoding="utf-8"))

def setup():
    HOME.mkdir(parents=True, exist_ok=True)
    if CONFIG.exists():
        print("Already configured:", CONFIG)
        return
    save(CONFIG, {
        "renderer_argv": [],
        "help": "Supply the VERIFIED existing offline renderer as an argument array. Use {text}, {wav}, and {voice} placeholders. NO shell invocation. Example only: [\"C:/path/python.exe\", \"C:/path/render.py\", \"--text-file\", \"{text}\", \"--output\", \"{wav}\", \"--profile\", \"{voice}\"]",
        "notes": "Do not use ritsu_say.py without verifying offline file output; it is the existing LIVE relay sender."
    })
    print("Created:", CONFIG)
    print("Set renderer_argv to a confirmed offline WAV command before running jobs.")

def doctor():
    print("Python:", sys.executable)
    print("Home:", HOME)
    print("Config:", CONFIG, "present" if CONFIG.exists() else "MISSING (run init)")
    if not CONFIG.exists():
        return 2
    conf = json.loads(CONFIG.read_text(encoding="utf-8"))
    args = conf.get("renderer_argv")
    if not isinstance(args, list) or not args or not all(isinstance(x, str) for x in args):
        print("BLOCKED: renderer_argv is not configured. No speculative renderer is invoked.")
        return 2
    exe = Path(args[0])
    if not exe.is_file():
        print("BLOCKED: renderer executable not found:", exe)
        return 2
    print("Renderer configured; actual inference and output remain unverified.")
    return 0

def submit(source, voice):
    if voice not in VOICES:
        raise ValueError("Voice must be one of: " + ", ".join(sorted(VOICES)))
    source = Path(source).expanduser().resolve(strict=True)
    if not source.is_file() or not source.read_text(encoding="utf-8-sig").strip():
        raise ValueError("Transcript must be nonempty UTF-8 file")
    if doctor() != 0:
        return 2
    job = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    target = folder(job)
    target.mkdir(parents=True)
    textfile = target / "transcript.txt"
    textfile.write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8")
    save(target / "status.json", {
        "job": job, "status": "queued", "submitted": now(), "voice": voice,
        "transcriptSha256": sha(textfile), "output": None
    })
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    with (target / "worker.log").open("ab") as log:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "_worker", job],
            cwd=str(target), stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            close_fds=True, creationflags=creationflags, start_new_session=os.name != "nt"
        )
    print("QUEUED", job)
    print("Status: pocket status", job)
    return 0

def worker(job):
    target = folder(job)
    record = read(job)
    if record["status"] not in {"queued", "running"}:
        return 0
    record.update(status="running", started=now(), pid=os.getpid())
    save(target / "status.json", record)
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        args = cfg["renderer_argv"]
        if not args or not isinstance(args, list):
            raise RuntimeError("Renderer not configured")
        variables = {"text": str(target / "transcript.txt"),
                     "wav": str(target / "audio.wav"), "voice": record["voice"]}
        command = [part.format_map(variables) for part in args]
        with (target / "render.log").open("wb") as out:
            proc = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=out,
                                  stderr=subprocess.STDOUT, cwd=str(target), timeout=7200)
        if proc.returncode:
            raise RuntimeError(f"Renderer exit status {proc.returncode}; inspect render.log")
        output = target / "audio.wav"
        if not output.is_file() or output.stat().st_size < 44:
            raise RuntimeError("Renderer reported success but produced no valid WAV")
        with wave.open(str(output), "rb") as wav:
            frames, rate = wav.getnframes(), wav.getframerate()
            duration = frames / rate
        if duration <= 0:
            raise RuntimeError("Output has zero audio duration")
        record.update(status="completed", finished=now(), output=str(output),
                      audioSha256=sha(output), durationSeconds=round(duration, 3),
                      bytes=output.stat().st_size)
    except Exception as e:
        record.update(status="failed", finished=now(), error=str(e))
    save(target / "status.json", record)
    return 0 if record["status"] == "completed" else 1

def latest():
    matches = sorted(JOBS.glob("*/status.json"), reverse=True)
    if not matches:
        raise FileNotFoundError("No jobs found")
    return matches[0].parent.name

def main():
    p = argparse.ArgumentParser(prog="pocket", description="Offline Pocket ASMR queue")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("doctor")
    q = sub.add_parser("asmr")
    q.add_argument("transcript")
    q.add_argument("--voice", choices=sorted(VOICES), default="whisper")
    for name in ("status", "path", "_worker"):
        cmd = sub.add_parser(name)
        cmd.add_argument("job", nargs="?" if name != "_worker" else None)
    a = p.parse_args()
    try:
        if a.command == "init": setup(); return 0
        if a.command == "doctor": return doctor()
        if a.command == "asmr": return submit(a.transcript, a.voice)
        job = a.job or latest()
        if a.command == "_worker": return worker(job)
        row = read(job)
        if a.command == "status":
            print(json.dumps(row, indent=2))
            return 0
        if row["status"] != "completed":
            print("NOT READY:", row["status"], file=sys.stderr)
            return 3
        path = Path(row["output"])
        if not path.is_file() or sha(path) != row["audioSha256"]:
            raise RuntimeError("WAV readback hash mismatch")
        print(path)
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as e:
        print("ERROR:", e, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
