#!/usr/bin/env python3
"""Ritsu Pocket audio-gap campaign: read-only Android playback forensics.

Owner: Drew. This script never sends speech, changes the receiver, accesses
bearer credentials, or changes the canonical Tailscale 19643 relay.
Runs on Termux through the already-authorized Home Center Phone Hands lane.
The small supervisor returns the operator's shell immediately; worker state,
append-only receipts, and errors survive interruptions.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import statistics
import subprocess
import sys
import time
import traceback
import wave

CAMPAIGN = "ritsu-phone-gap-readonly-v1"
HOME = Path.home()
RECEIVER = HOME / ".ritsu-embodiment"
STATE = RECEIVER / "gap-campaign"
TRACE = RECEIVER / "receiver-v2" / "trace.jsonl"
READY = RECEIVER / "receiver-v2" / "ready"
STATUS = STATE / "state.json"
RECEIPTS = STATE / "receipts.jsonl"
LOG = STATE / "campaign.log"
MAX_TRACE_BYTES = 2_000_000

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def dump_atomic(path, obj):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + str(os.getpid()))
    tmp.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def read_status():
    try:
        return json.loads(STATUS.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"campaign": CAMPAIGN, "phase": "not-started", "accepted": False}

def save_status(**changes):
    record = read_status()
    record.update(changes, campaign=CAMPAIGN, updatedAt=now())
    dump_atomic(STATUS, record)
    return record

def append_receipt(obj):
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with RECEIPTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": now(), "campaign": CAMPAIGN, **obj}, sort_keys=True) + "\n")

def copy_receipt(text):
    # Never copy full logs, secrets or TTS transcripts to clipboard.
    print(text, flush=True)
    exe = shutil.which("termux-clipboard-set")
    if exe:
        try:
            subprocess.run([exe], input=text, text=True, capture_output=True, timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        print("CLIPBOARD_UNAVAILABLE; receipt printed above", flush=True)

def hash_file(path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def events():
    if not TRACE.is_file():
        return [], "TRACE_MISSING"
    size = TRACE.stat().st_size
    # The bound protects operator memory; partial first line is discarded.
    with TRACE.open("rb") as f:
        if size > MAX_TRACE_BYTES:
            f.seek(size - MAX_TRACE_BYTES)
            f.readline()
        rows = f.readlines()
    result = []
    bad = 0
    for raw in rows:
        try:
            row = json.loads(raw)
            if row.get("event") in {"playback_started", "playback_finished", "fetched", "acknowledged"}:
                result.append({"event": row["event"], "seq": int(row["seq"]),
                               "ms": int(row["deviceMonotonicMs"]), "relayId": row.get("relayId")})
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            bad += 1
    health = "PARSE_WARNINGS_" + str(bad) if bad else "OK"
    if size > MAX_TRACE_BYTES:
        health = "TRACE_TRUNCATED_" + health
    return result, health

def trace_report(rows):
    starts, ends = {}, {}
    pairs, gaps, anomalies = [], [], []
    prev_finished = None
    prev_seq = None
    for row in rows:
        seq, ms, kind = row["seq"], row["ms"], row["event"]
        if kind == "playback_started":
            if prev_finished is not None:
                delta = ms - prev_finished
                if delta >= 0 and seq > prev_seq:
                    gaps.append({"from": prev_seq, "to": seq, "gapSeconds": round(delta / 1000, 3)})
                else:
                    anomalies.append("non_monotonic_or_repeated_start_" + str(seq))
            starts[seq] = ms
            prev_finished = None
        elif kind == "playback_finished":
            if seq in starts and ms >= starts[seq]:
                pairs.append({"seq": seq, "playerElapsedSeconds": round((ms-starts[seq])/1000, 3)})
            else:
                anomalies.append("finish_without_valid_start_" + str(seq))
            ends[seq] = ms
            prev_finished, prev_seq = ms, seq
    numbers = [g["gapSeconds"] for g in gaps]
    return {"startedCount": len([r for r in rows if r["event"] == "playback_started"]),
            "finishedCount": len([r for r in rows if r["event"] == "playback_finished"]),
            "completedPairs": len(pairs), "gaps": gaps[-30:], "durations": pairs[-30:],
            "medianGapSeconds": round(statistics.median(numbers), 3) if numbers else None,
            "maxGapSeconds": max(numbers) if numbers else None,
            "anomalies": anomalies[-20:]}

def wav_report():
    found = []
    for p in sorted(READY.glob("*.wav"))[-16:] if READY.is_dir() else []:
        try:
            with wave.open(str(p), "rb") as w:
                sr = w.getframerate()
                channels = w.getnchannels()
                width = w.getsampwidth()
                frames = w.getnframes()
                seconds = round(frames / sr, 3) if sr else None
            found.append({"file": p.name, "seconds": seconds, "sampleRate": sr,
                          "channels": channels, "sampleWidth": width,
                          "sizeBytes": p.stat().st_size})
        except (OSError, EOFError, wave.Error) as exc:
            found.append({"file": p.name, "error": type(exc).__name__})
    return found

def collect():
    try:
        save_status(phase="collecting", startedAt=now(), accepted=False)
        rows, trace_health = events()
        report = {
            "schema": "ritsu.phone-gap.readonly.v1",
            "collectedAt": now(),
            "source": "ANDROID_TERMUX",
            "trace": str(TRACE),
            "traceHealth": trace_health,
            "traceEventCount": len(rows),
            "receiverSourceSha256": hash_file(RECEIVER / "receiver.sh"),
            "installedCandidateSha256": hash_file(RECEIVER / "receiver-v2.sh"),
            "analysis": trace_report(rows),
            "retainedWavs": wav_report(),
            "interpretationLimit": "player API timestamps are not acoustic onset; WAV metadata does not prove spoken-word completeness",
            "changesToAudioPipeline": 0,
        }
        receipt_path = STATE / ("result-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
        dump_atomic(receipt_path, report)
        complete = trace_health == "OK" and report["analysis"]["completedPairs"] > 0
        append_receipt({"kind": "diagnostic-completed" if complete else "diagnostic-incomplete",
                        "path": str(receipt_path),
                        "medianGapSeconds": report["analysis"]["medianGapSeconds"]})
        save_status(phase="inspection-complete" if complete else "inspection-incomplete",
                    report=str(receipt_path), workerPid=None,
                    lastGoodStage="android-trace-audit" if complete else None, accepted=False)
        copy_receipt(("RITSU_GAP_INSPECTION_COMPLETE" if complete else "RITSU_GAP_INSPECTION_INCOMPLETE") + "\n"
                     + "TRACE=" + trace_health + "\n"
                     + "PAIRS=" + str(report["analysis"]["completedPairs"]) + "\n"
                     + "MEDIAN_GAP_SEC=" + str(report["analysis"]["medianGapSeconds"]) + "\n"
                     + "REPORT=" + str(receipt_path) + "\n"
                     + "HEARD=unverified; REPAIR=not-deployed")
    except Exception as exc:
        append_receipt({"kind": "diagnostic-failed", "error": repr(exc)})
        save_status(phase="failed", error=repr(exc), workerPid=None, accepted=False)
        with LOG.open("a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        copy_receipt("RITSU_GAP_INSPECTION_FAILED\nERROR=" + type(exc).__name__
                     + "\nLOG=" + str(LOG) + "\nHEARD=unverified")
        return 1
    return 0 if complete else 4

def worker_alive(record):
    pid = record.get("workerPid")
    if not isinstance(pid, int):
        try:
            pid = int((STATE / "worker.pid").read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return False
    if pid <= 0:
        return False
    try:
        raw = Path("/proc") / str(pid) / "cmdline"
        text = raw.read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
        return Path(__file__).name in text and "_collect" in text and os.getpgid(pid) == pid
    except (OSError, ProcessLookupError):
        return False

def launch():
    existing = read_status()
    if worker_alive(existing):
        copy_receipt("RITSU_GAP_ALREADY_RUNNING\nPID=" + str(existing["workerPid"]))
        return 0
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Parent writes launch state BEFORE spawning, so a fast worker's success
    # cannot be accidentally overwritten by the launcher.
    save_status(phase="launching", workerPid=None, startedAt=now(), accepted=False)
    (STATE / "worker.pid").unlink(missing_ok=True)
    with LOG.open("a", encoding="utf-8") as logfile:
        proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "_collect"],
                                stdin=subprocess.DEVNULL, stdout=logfile, stderr=subprocess.STDOUT,
                                start_new_session=True, cwd=str(HOME), close_fds=True)
    (STATE / "worker.pid").write_text(str(proc.pid) + "\n", encoding="utf-8")
    append_receipt({"kind": "launched", "pid": proc.pid})
    copy_receipt("RITSU_GAP_STARTED\nPID=" + str(proc.pid)
                 + "\nSTATUS=python " + str(Path(__file__).resolve()) + " status"
                 + "\nRECEIPTS=" + str(RECEIPTS))
    return 0

def stop():
    state = read_status()
    if not worker_alive(state):
        copy_receipt("RITSU_GAP_NOT_RUNNING\nNO_OTHER_PROCESSES_TOUCHED")
        return 0
    pid = state.get("workerPid") or int((STATE / "worker.pid").read_text(encoding="utf-8"))
    os.killpg(pid, signal.SIGTERM)
    for _ in range(20):
        if not worker_alive(state):
            break
        time.sleep(.1)
    if worker_alive(state):
        os.killpg(pid, signal.SIGKILL)
    save_status(phase="stopped", workerPid=None, accepted=False)
    append_receipt({"kind": "stopped", "pid": pid})
    copy_receipt("RITSU_GAP_STOPPED\nPID=" + str(pid))
    return 0

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "resume", "status", "receipts", "follow",
                                            "stop", "recover", "_collect"])
    action = parser.parse_args().action
    if action == "_collect":
        return collect()
    if action in {"run", "resume", "recover"}:
        return launch()
    if action == "stop":
        return stop()
    if action == "status":
        s = read_status()
        copy_receipt("RITSU_GAP_STATUS\nPHASE=" + str(s.get("phase"))
                     + "\nWORKER_ALIVE=" + str(worker_alive(s))
                     + "\nREPORT=" + str(s.get("report", "none"))
                     + "\nHEARD=unverified")
        return 0
    if action == "receipts":
        if RECEIPTS.exists():
            print("\n".join(RECEIPTS.read_text(encoding="utf-8").splitlines()[-15:]))
        else:
            print("NO_RECEIPTS_YET")
        return 0
    if action == "follow":
        print("\n".join(LOG.read_text(encoding="utf-8").splitlines()[-35:]) if LOG.exists()
              else "NO_LOG_YET")
        return 0
    return 2

if __name__ == "__main__":
    sys.exit(main())
