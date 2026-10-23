#!/usr/bin/env python3
"""Conservative read-only silence probe or NEW candidate 24kHz PCM WAV cutter.

No source overwrite, no end clipping, no voice/pitch changes, no phone transport,
no automatic sentence splitting, and no live audio integration. A candidate must
be auditioned before anyone uses it for speech.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import wave

SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2
FRAME_MS = 10
GUARD_MS = 200
MAX_CUT_MS = 800
MIN_CUT_MS = 60
PEAK_LIMIT = 96
RMS_LIMIT = 32
MIN_RETAIN_MS = 500


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pcm_read(path: Path) -> bytes:
    with wave.open(str(path), "rb") as reader:
        fields = (reader.getframerate(), reader.getnchannels(), reader.getsampwidth())
        if fields != (SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH) or reader.getcomptype() != "NONE":
            raise ValueError(f"Unsupported WAV format {fields}; refusing to modify")
        frames = reader.getnframes()
        if frames <= 0:
            raise ValueError("Empty WAV")
        raw = reader.readframes(frames)
        if len(raw) != frames * SAMPLE_WIDTH:
            raise ValueError("Incomplete WAV payload")
        return raw


def pcm_write_new(path: Path, pcm: bytes) -> None:
    # Exclusive-create avoids any overwrite of original or another candidate.
    with path.open("xb") as fd:
        try:
            with wave.open(fd, "wb") as writer:
                writer.setnchannels(CHANNELS)
                writer.setsampwidth(SAMPLE_WIDTH)
                writer.setframerate(SAMPLE_RATE)
                writer.writeframes(pcm)
        except Exception:
            path.unlink(missing_ok=True)
            raise


def decide(pcm: bytes) -> dict:
    if len(pcm) < SAMPLE_RATE * SAMPLE_WIDTH * MIN_RETAIN_MS // 1000:
        return {"leadingQuietMs": 0, "safeCandidateCutMs": 0, "reason": "too_short"}
    if len(pcm) % SAMPLE_WIDTH:
        raise ValueError("PCM byte count is not sample aligned")
    frame_bytes = SAMPLE_RATE * FRAME_MS // 1000 * SAMPLE_WIDTH
    leading_quiet_frames = 0
    found_signal = False
    for pos in range(0, len(pcm), frame_bytes):
        chunk = pcm[pos:pos+frame_bytes]
        values = array("h")
        values.frombytes(chunk)
        if sys.byteorder != "little":
            values.byteswap()
        peak = max((abs(x) for x in values), default=0)
        rms = math.sqrt(sum(int(x)*int(x) for x in values) / max(1, len(values)))
        if peak > PEAK_LIMIT or rms > RMS_LIMIT:
            found_signal = True
            break
        leading_quiet_frames += 1
    quiet_ms = leading_quiet_frames * FRAME_MS
    if not found_signal:
        return {"leadingQuietMs": quiet_ms, "safeCandidateCutMs": 0, "reason": "all_quiet_refuse"}
    cut_ms = max(0, min(MAX_CUT_MS, quiet_ms - GUARD_MS))
    cut_ms = cut_ms // FRAME_MS * FRAME_MS
    total_ms = len(pcm) * 1000 // (SAMPLE_RATE*SAMPLE_WIDTH)
    if cut_ms < MIN_CUT_MS or total_ms - cut_ms < MIN_RETAIN_MS:
        cut_ms = 0
    return {"leadingQuietMs": quiet_ms, "safeCandidateCutMs": cut_ms,
            "reason": "leading_quiet_candidate" if cut_ms else "no_safe_trim"}


def inspect(path: Path) -> dict:
    pcm = pcm_read(path)
    plan = decide(pcm)
    return {"file": path.name, "samples": len(pcm)//2,
            "durationMs": len(pcm)*1000//(SAMPLE_RATE*SAMPLE_WIDTH),
            "sampleRate": SAMPLE_RATE, **plan}


def candidate(source: Path, dest: Path) -> dict:
    if source.resolve() == dest.resolve() or dest.exists():
        raise FileExistsError("Refusing to overwrite original or existing output")
    pcm = pcm_read(source)
    plan = decide(pcm)
    trim_bytes = plan["safeCandidateCutMs"] * SAMPLE_RATE * SAMPLE_WIDTH // 1000
    if trim_bytes <= 0:
        raise ValueError("No conservative leading silence candidate; leaving audio alone")
    data = pcm[trim_bytes:]
    pcm_write_new(dest, data)
    verified = pcm_read(dest)
    if verified != data:
        dest.unlink(missing_ok=True)
        raise RuntimeError("WAV readback mismatch")
    return {"source": str(source), "candidate": str(dest), **plan,
            "unchangedSampleSuffixSha256": digest(data),
            "originalPcmSha256": digest(pcm),
            "preservedTrailingSamples": True, "auditionRequired": True,
            "livePipelineModified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="operation", required=True)
    a = subs.add_parser("inspect", help="read-only WAV boundary probe")
    a.add_argument("wav", nargs="+", type=Path)
    b = subs.add_parser("candidate", help="new WAV; never overwrite; no live delivery")
    b.add_argument("wav", type=Path)
    b.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = [inspect(p) for p in args.wav] if args.operation == "inspect" else candidate(args.wav, args.out)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, wave.Error) as exc:
        print(json.dumps({"status": "REFUSED", "error": str(exc)[:300],
                          "livePipelineModified": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
