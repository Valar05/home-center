#!/usr/bin/env python3
"""Ritsu Android v4: one persistent mpv process, exact FIFO input WAVs.

Run only under the canonical Termux receiver's exclusive lock, with its fetch
loop providing atomic ready/*.wav files. Does not fetch, ACK, alter speech,
change voice, or trim PCM. Every uncertain play state leaves a 'playing'
marker and fails closed against automatic replay.
"""
import argparse
import json
import os
from pathlib import Path
import re
import select
import signal
import socket
import subprocess
import sys
import time
import wave

NAME = re.compile(r"^([0-9]{8})_([0-9a-f]{24})\.wav$")
RATE = 24000
MAX_SEC = 90
MAX_QUEUE = 3

def atomic_text(path, val):
    tmp = path.with_name(path.name + ".tmp." + str(os.getpid()))
    with tmp.open("x", encoding="utf8") as f:
        f.write(val)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def atomic_json(path, val):
    atomic_text(path, json.dumps(val, separators=(",", ":")) + "\n")

def inspect(path, seq):
    m = NAME.fullmatch(path.name)
    if not m or int(m.group(1)) != seq:
        raise RuntimeError("non-canonical WAV or FIFO sequence")
    with wave.open(str(path), "rb") as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype()) != (1, 2, RATE, "NONE"):
            raise RuntimeError("WAV format mismatch")
        if not 0 < w.getnframes() <= RATE * MAX_SEC:
            raise RuntimeError("WAV length out of bounds")
    return {"seq": seq, "id": m.group(2), "file": str(path.resolve()), "started": False,
            "entry": None, "submitted": False, "durationSec": round(w.getnframes() / RATE, 3)}

def trace(file, event, item=None, **extras):
    entry = {"event": event, "seq": item["seq"] if item else 0,
             "relayId": item["id"] if item else "", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "deviceMonotonicMs": int(time.monotonic() * 1000), **extras}
    with file.open("a", encoding="utf8") as fd:
        fd.write(json.dumps(entry, separators=(",", ":")) + "\n")
        fd.flush()

class Driver:
    def __init__(self, root, audio_output="opensles", mpv="mpv"):
        self.root = Path(root)
        self.ready = self.root / "ready"
        self.marker = self.root / "playing"
        self.play_seq = self.root / "play.seq"
        self.stop = self.root / "stop.request"
        self.trace_file = self.root / "trace.jsonl"
        self.sock_path = self.root / "ritsu-mpv.sock"
        self.log_path = self.root / "ritsu-mpv-stderr.log"
        self.mpv = mpv
        self.ao = audio_output
        self.proc = None
        self.sock = None
        self.buf = b""
        self.inflight = {}
        self.next_request = 1
        self.pending = []
        self.next_enqueue = None
        self.stopping = False
        self.started_count = 0
        self.finished_count = 0

    def journal(self):
        if self.pending:
            atomic_json(self.marker, {"version": 4, "pending": self.pending})
        else:
            self.marker.unlink(missing_ok=True)

    def start(self):
        if self.marker.exists() or self.sock_path.exists():
            raise RuntimeError("uncertain playback marker/socket; do not replay")
        if self.stop.exists():
            raise RuntimeError("stop requested")
        if not self.ready.is_dir() or not self.play_seq.is_file():
            raise RuntimeError("missing canonical receiver state")
        self.next_enqueue = int(self.play_seq.read_text().strip())
        log = self.log_path.open("ab")
        # --no-config avoids untrusted config, AO pinned to Termux OpenSL ES.
        cmd = [self.mpv, "--no-config", "--no-terminal", "--no-video",
               "--idle=yes", "--keep-open=no", "--gapless-audio=yes",
               "--audio-display=no", "--ao=" + self.ao,
               "--input-ipc-server=" + str(self.sock_path)]
        try:
            self.proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                         start_new_session=True)
        finally:
            log.close()
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("mpv exited during startup")
            if self.sock_path.exists():
                try:
                    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    self.sock.connect(str(self.sock_path))
                    self.sock.setblocking(False)
                    trace(self.trace_file, "mpv_persistent_ready")
                    return
                except OSError:
                    if self.sock:
                        self.sock.close()
                    self.sock = None
            time.sleep(.06)
        raise RuntimeError("mpv IPC socket not ready")

    def send(self, cmd, item):
        req = self.next_request
        self.next_request += 1
        self.inflight[req] = item
        msg = json.dumps({"command": cmd, "request_id": req}, separators=(",", ":")) + "\n"
        self.sock.sendall(msg.encode("utf8"))
        return req

    def handle(self, msg):
        if "request_id" in msg and msg.get("request_id") in self.inflight:
            item = self.inflight.pop(msg["request_id"])
            if msg.get("error") != "success":
                raise RuntimeError("mpv loadfile refused: " + str(msg.get("error")))
            item["submitted"] = True
            self.journal()
        ev = msg.get("event")
        if ev == "start-file":
            nxt = next((x for x in self.pending if not x["started"]), None)
            if nxt is None:
                raise RuntimeError("unexpected mpv file start")
            eid = msg.get("playlist_entry_id")
            if not isinstance(eid, int):
                raise RuntimeError("missing playlist entry id")
            nxt["entry"] = eid
            nxt["started"] = True
            self.journal()
            self.started_count += 1
            trace(self.trace_file, "mpv_track_started", nxt, playlistEntryId=eid)
        elif ev == "end-file":
            if not self.pending:
                raise RuntimeError("unexpected mpv file completion")
            item = self.pending[0]
            if not item["started"] or msg.get("playlist_entry_id") != item["entry"]:
                raise RuntimeError("mpv completion FIFO mismatch")
            if msg.get("reason") != "eof":
                raise RuntimeError("mpv file did not reach EOF: " + str(msg.get("reason")))
            # Advance only on actual end-file EOF, never on relay fetch/ACK.
            trace(self.trace_file, "mpv_track_finished", item, playlistEntryId=item["entry"])
            atomic_text(self.play_seq, str(item["seq"] + 1) + "\n")
            self.pending.pop(0)
            self.journal()
            self.finished_count += 1
            old_seq = item["seq"] - 8
            if old_seq >= 0:
                for old in self.ready.glob(f"{old_seq:08d}_*.wav"):
                    old.unlink(missing_ok=True)
        elif ev == "shutdown" and not self.stopping:
            raise RuntimeError("unexpected mpv shutdown")

    def poll(self, timeout=0.075):
        if self.proc.poll() is not None:
            raise RuntimeError("mpv process exited unexpectedly")
        readable, _, _ = select.select([self.sock], [], [], timeout)
        if not readable:
            return
        raw = self.sock.recv(65536)
        if not raw:
            raise RuntimeError("mpv IPC disconnected")
        self.buf += raw
        if len(self.buf) > 262144:
            raise RuntimeError("mpv IPC response oversized")
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            if not line.strip():
                continue
            self.handle(json.loads(line.decode("utf-8", "replace")))

    def offer(self):
        if self.stop.exists():
            self.stopping = True
        if self.stopping or self.inflight or len(self.pending) >= MAX_QUEUE:
            return
        seq = self.next_enqueue
        matches = list(self.ready.glob(f"{seq:08d}_*.wav"))
        if not matches:
            return
        if len(matches) != 1:
            raise RuntimeError("duplicate ready FIFO slots")
        item = inspect(matches[0], seq)
        if self.pending and item["seq"] != self.pending[-1]["seq"] + 1:
            raise RuntimeError("non-consecutive enqueue")
        # Record intent BEFORE sending IPC so ambiguous response fails closed.
        self.pending.append(item)
        self.journal()
        self.next_enqueue += 1
        self.send(["loadfile", item["file"], "append-play"], item)
        trace(self.trace_file, "mpv_track_offered", item)

    def run(self, test_timeout=None):
        self.start()
        deadline = time.monotonic() + test_timeout if test_timeout else None
        while True:
            if deadline and time.monotonic() > deadline:
                if self.pending:
                    raise RuntimeError("test timed out with unplayed source")
                return
            self.offer()
            self.poll()
            if self.stopping and not self.pending and not self.inflight:
                return

    def close(self, failure=False):
        if self.sock:
            self.sock.close()
        if self.proc:
            try:
                if self.proc.poll() is None:
                    self.proc.terminate()
                    self.proc.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()
        # A crash or uncertain playback MUST preserve marker for manual review.
        if not failure and not self.pending and not self.inflight:
            self.marker.unlink(missing_ok=True)
        # mpv socket owned by THIS process only, do not remove an alien socket.
        if self.proc:
            self.sock_path.unlink(missing_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--ao", default="opensles", choices=("opensles", "null"))
    ap.add_argument("--test-timeout", type=float, default=0)
    args = ap.parse_args()
    d = Driver(args.state, audio_output=args.ao)
    failed = True
    try:
        d.run(test_timeout=args.test_timeout or None)
        failed = False
        return 0
    except (RuntimeError, OSError, ValueError, wave.Error, json.JSONDecodeError) as e:
        trace(d.trace_file, "mpv_driver_refused", error=type(e).__name__, details=str(e)[:140])
        print("RITSU_MPV_DRIVER_REFUSED " + type(e).__name__ + ": " + str(e)[:160], file=sys.stderr)
        return 2
    finally:
        d.close(failure=failed)

if __name__ == "__main__":
    sys.exit(main())
