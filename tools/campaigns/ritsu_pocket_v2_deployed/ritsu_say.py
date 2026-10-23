"""Single WAV per entire agent-authored Ritsu reply.

No sentence segmentation, text rewriting, silence trimming or chunk concatenation
in this sender. Pocket must render the complete input through one /v1/speak job;
that one WAV is enqueued to the canonical 19643 relay exactly once.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import time
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent
BASE = "http://127.0.0.1:10205"
PROFILES = ("normal", "whisper", "amused", "happy", "delighted", "upset", "somber", "warm")
MAX_TEXT_CHARS = 450  # Match the verified live Pocket /v1/speak limit
LOGDIR = pathlib.Path(os.environ.get("LOCALAPPDATA", str(pathlib.Path.home()))) / "RitsuWarmTicketWorker" / "timing"
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def validate_whole_text(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Empty voice transcript")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError("Full transcript exceeds single Pocket request limit; refusing to split, shorten or omit any text")
    return text


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")


class Trace:
    def __init__(self, turn_id):
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{6,160}", turn_id):
            raise ValueError("Invalid turn ID")
        self.turn_id = turn_id
        LOGDIR.mkdir(parents=True, exist_ok=True)
        self.file = LOGDIR / (turn_id + ".jsonl")
        if self.file.exists():
            raise FileExistsError("Duplicate turn ID: refusing an ambiguous second delivery")

    def record(self, event, **details):
        row = {"turnId": self.turn_id, "seq": 1, "event": event,
               "utc": timestamp(), "monotonic_ns": time.monotonic_ns(), **details}
        with self.file.open("a", encoding="utf-8") as writer:
            writer.write(json.dumps(row, separators=(",", ":")) + "\n")


def request(token, method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method=method,
          headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with HTTP.open(req, timeout=20) as response:
        return json.load(response)


def deliver_whole(text, profile, turn_id, timeout=300, client=None, trace=None):
    text = validate_whole_text(text)
    if profile not in PROFILES:
        raise ValueError("Unsupported voice profile")
    client = client or (lambda m, p, b=None: request((ROOT / "ritsu-api-token.txt").read_text(encoding="utf-8").strip(), m, p, b))
    trace = trace or Trace(turn_id)
    started = time.monotonic()
    trace.record("whole_transcript_start", text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                 text_chars=len(text), expected_wavs=1, profile=profile)
    trace.record("pocket_submit_start")
    job = client("POST", "/v1/speak", {"text": text, "speaker": profile})
    if job.get("state") != "queued" or not job.get("id"):
        raise RuntimeError("Pocket did not accept complete text as one job")
    jid = job["id"]
    trace.record("pocket_accepted", jobId=jid)
    deadline = time.monotonic() + timeout
    while True:
        item = client("GET", "/v1/jobs/" + jid)
        if item.get("state") == "completed":
            trace.record("pocket_completed", jobId=jid,
                         generation_seconds=item.get("generation_seconds"),
                         audio_seconds=item.get("audio_seconds"), wav_bytes=item.get("bytes"))
            break
        if item.get("state") == "failed":
            raise RuntimeError("Pocket failed whole-text render; no partial audio delivered")
        if time.monotonic() >= deadline:
            raise TimeoutError("Pocket whole-text render deadline; do not replay ambiguous job")
        time.sleep(0.2)
    trace.record("relay_deliver_start", jobId=jid)
    delivered = client("POST", "/v1/deliver", {"job_id": jid})
    relay = delivered.get("relay_id")
    if delivered.get("state") != "enqueued" or not isinstance(relay, str) or not re.fullmatch(r"[a-f0-9]{16,80}", relay):
        raise RuntimeError("No canonical relay receipt for whole WAV")
    trace.record("relay_enqueued", jobId=jid, relayId=relay)
    trace.record("turn_one_wav_enqueued", elapsed_seconds=round(time.monotonic()-started, 3))
    print("ENQUEUED_CHUNK 1 of 1 relay", relay, "audio_sec", item.get("audio_seconds"),
          "gen_sec", item.get("generation_seconds"), flush=True)
    print("ALL_CHUNKS_ENQUEUED_NOT_HEARD", flush=True)
    return [relay]


def main(argv=None):
    ap = argparse.ArgumentParser()
    input_group = ap.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--text")
    input_group.add_argument("--text-file")
    ap.add_argument("--profile", choices=PROFILES, default="normal")
    ap.add_argument("--turn-id", default=None)
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args(argv)
    text = args.text if args.text is not None else pathlib.Path(args.text_file).read_text(encoding="utf-8")
    trace_id = args.turn_id or ("whole-" + uuid.uuid4().hex)
    deliver_whole(text, args.profile, trace_id, args.timeout)


if __name__ == "__main__":
    main()
