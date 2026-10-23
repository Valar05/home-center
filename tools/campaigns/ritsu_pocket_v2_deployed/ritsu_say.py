"""Sentence-complete, ordered-lookahead Ritsu Pocket ticket sender.

Only Pocket 10205 and the existing /v1/deliver -> canonical 19643 phone relay.
No parallel synthesis, Qwen fallback, generated speech pitch shift, or unsafe replay.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent
BASE = "http://127.0.0.1:10205"
PROFILES = ("normal", "whisper", "amused", "happy", "delighted", "upset", "somber", "warm")
WINDOW = 4
MAX_SENTENCES = 50
MAX_SENTENCE_CHARS = 450
LOGDIR = pathlib.Path(os.environ.get("LOCALAPPDATA", str(pathlib.Path.home()))) / "RitsuWarmTicketWorker" / "timing"
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def sentence_chunks(text):
    original = text.strip()
    if not original:
        raise ValueError("Empty speech")
    # Split at grammatical endings, retaining all spoken punctuation and words.
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"“(])', original) if p.strip()]
    if len(parts) > MAX_SENTENCES:
        raise ValueError("Too many sentences for one turn")
    for part in parts:
        if len(part) > MAX_SENTENCE_CHARS:
            raise ValueError("Sentence too long: refuse truncation or mid-sentence splitting")
    return parts


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")


class Trace:
    def __init__(self, turn_id):
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{6,160}", turn_id):
            raise ValueError("Bad turn ID")
        self.turn_id = turn_id
        LOGDIR.mkdir(parents=True, exist_ok=True)
        self.file = LOGDIR / (turn_id + ".jsonl")
        if self.file.exists():
            raise FileExistsError("Refuse duplicate trace/possible speech replay")

    def record(self, event, seq=0, **details):
        obj = {"turnId": self.turn_id, "seq": seq, "event": event,
               "utc": timestamp(), "monotonic_ns": time.monotonic_ns(), **details}
        with self.file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, separators=(",", ":")) + "\n")


def get_key():
    return (ROOT / "ritsu-api-token.txt").read_text(encoding="utf-8").strip()


def request(token, method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method=method,
              headers={"Authorization": "Bearer " + token,
                       "Content-Type": "application/json"})
    with HTTP.open(req, timeout=20) as response:
        return json.load(response)


def deliver_ordered(sentences, profile, turn_id, timeout=180, client=None, trace=None):
    if profile not in PROFILES:
        raise ValueError("Unsupported voice profile")
    if not (1 <= len(sentences) <= MAX_SENTENCES):
        raise ValueError("Invalid sentence count")
    client = client or (lambda m, p, b=None: request(get_key(), m, p, b))
    trace = trace or Trace(turn_id)
    active = {}
    queued = 0
    receipts = []
    started = time.monotonic()
    trace.record("turn_start", count=len(sentences), profile=profile,
                 transcript_sha256=hashlib.sha256(" ".join(sentences).encode()).hexdigest())

    def submit_next():
        nonlocal queued
        i = queued + 1
        trace.record("pocket_submit_start", i)
        job = client("POST", "/v1/speak", {"text": sentences[queued], "speaker": profile})
        if job.get("state") != "queued" or not job.get("id"):
            raise RuntimeError("Pocket job acceptance failed at sentence " + str(i))
        active[i] = job["id"]
        queued += 1
        trace.record("pocket_accepted", i, jobId=job["id"])

    for _ in range(min(WINDOW, len(sentences))):
        submit_next()
    for i in range(1, len(sentences) + 1):
        jid = active[i]
        deadline = time.monotonic() + timeout
        while True:
            row = client("GET", "/v1/jobs/" + jid)
            if row.get("state") == "completed":
                trace.record("pocket_completed", i, jobId=jid,
                             generation_seconds=row.get("generation_seconds"),
                             audio_seconds=row.get("audio_seconds"),
                             wav_bytes=row.get("bytes"))
                break
            if row.get("state") == "failed":
                raise RuntimeError("Pocket generation failed at sentence " + str(i))
            if time.monotonic() >= deadline:
                raise TimeoutError("Pocket generation timeout at sentence " + str(i))
            time.sleep(0.20)
        # Keep a constant four-sentence lookahead. CPU synthesis remains serial
        # via the unchanged Pocket ThreadPoolExecutor(max_workers=1).
        if queued < len(sentences):
            submit_next()
        trace.record("relay_deliver_start", i, jobId=jid)
        delivered = client("POST", "/v1/deliver", {"job_id": jid})
        relay = delivered.get("relay_id")
        if delivered.get("state") != "enqueued" or not isinstance(relay, str) or not re.fullmatch(r"[a-f0-9]{16,80}", relay):
            raise RuntimeError("Relay acceptance missing; stop rather than replay")
        receipts.append(relay)
        trace.record("relay_enqueued", i, jobId=jid, relayId=relay)
        del active[i]
        print("ENQUEUED_CHUNK", i, "of", len(sentences), "relay", relay,
              "audio_sec", row.get("audio_seconds"), "gen_sec", row.get("generation_seconds"), flush=True)
    trace.record("turn_enqueued", count=len(receipts), elapsed_s=round(time.monotonic()-started, 3))
    print("ALL_CHUNKS_ENQUEUED_NOT_HEARD", flush=True)
    return receipts


def main(argv=None):
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--text-file")
    ap.add_argument("--profile", choices=PROFILES, default="normal")
    ap.add_argument("--turn-id", default=None)
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args(argv)
    text = args.text if args.text is not None else pathlib.Path(args.text_file).read_text(encoding="utf-8")
    sentences = sentence_chunks(text)
    trace_id = args.turn_id or ("local-" + uuid.uuid4().hex)
    print("SPEECH_CHUNKS", len(sentences), flush=True)
    deliver_ordered(sentences, args.profile, trace_id, args.timeout)


if __name__ == "__main__":
    main()
