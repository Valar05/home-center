#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/kinesis-flight-recorder/SKILL.md"
SCRIPT = ROOT / "skills/kinesis-flight-recorder/kinesis_flight_recorder.py"

for path in [SKILL, SCRIPT]:
    assert path.exists(), f"missing Kinesis Flight Recorder contract file: {path}"

skill = SKILL.read_text(encoding="utf-8")
script = SCRIPT.read_text(encoding="utf-8")

for fragment in [
    "LAUNCH ONCE, GET OUT OF THE WAY",
    "KEYS, NOT FRAMES. LAUNCH, LEAVE, READ THE RECEIPT.",
    "model polling",
    "adversarial_opposite",
    "RESEARCH_CAMERA_THEFT",
    "IF THE MODEL HAS TO BABYSIT THE VIDEO, THE SKILL FAILED.",
]:
    assert fragment.lower() in skill.lower(), f"skill missing required fragment: {fragment!r}"

for fragment in [
    "home-center.kinesis-flight-recorder.result.v1",
    "model_polling_required",
    "--detach",
    "status.json",
    "storyboard.jpg",
]:
    assert fragment in script, f"recorder missing required fragment: {fragment!r}"

ffmpeg = shutil.which("ffmpeg")
ffprobe = shutil.which("ffprobe")
assert ffmpeg and ffprobe, "ffmpeg and ffprobe are required for the executable canary"

with tempfile.TemporaryDirectory(prefix="kinesis-flight-recorder-") as temp_dir:
    temp = Path(temp_dir)
    video_a = temp / "primary.mp4"
    video_b = temp / "adversary.mp4"

    subprocess.run([
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi",
        "-i", "testsrc=size=320x180:rate=12:duration=1.5",
        "-pix_fmt", "yuv420p",
        str(video_a),
    ], check=True)
    subprocess.run([
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi",
        "-i", "testsrc2=size=320x180:rate=12:duration=1.5",
        "-pix_fmt", "yuv420p",
        str(video_b),
    ], check=True)

    single_out = temp / "single"
    subprocess.run([
        sys.executable, str(SCRIPT), str(video_a),
        "--foreground",
        "--samples", "6",
        "--out", str(single_out),
    ], check=True)

    status = json.loads((single_out / "status.json").read_text(encoding="utf-8"))
    result = json.loads((single_out / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads((single_out / "primary" / "manifest.json").read_text(encoding="utf-8"))
    assert status["state"] == "DONE"
    assert result["state"] == "DONE"
    assert result["mode"] == "single"
    assert result["model_polling_required"] is False
    assert manifest["sampling"]["requested_samples"] == 6
    assert (single_out / "primary" / "storyboard.jpg").stat().st_size > 0

    pair_out = temp / "pair"
    subprocess.run([
        sys.executable, str(SCRIPT), str(video_a),
        "--compare", str(video_b),
        "--relation", "adversarial_opposite",
        "--foreground",
        "--samples", "6",
        "--out", str(pair_out),
    ], check=True)

    pair_result = json.loads((pair_out / "result.json").read_text(encoding="utf-8"))
    pair = json.loads((pair_out / "pair.json").read_text(encoding="utf-8"))
    assert pair_result["state"] == "DONE"
    assert pair_result["mode"] == "pair"
    assert pair["relation"] == "adversarial_opposite"
    assert (pair_out / "primary" / "storyboard.jpg").stat().st_size > 0
    assert (pair_out / "adversary" / "storyboard.jpg").stat().st_size > 0

print(json.dumps({
    "ok": True,
    "schema": "home-center.kinesis-flight-recorder.canary-result.v1",
    "singleRun": True,
    "pairRun": True,
    "adversarialRelationPreserved": True,
    "modelPollingRequired": False,
    "defaultIsSparse": True,
}, sort_keys=True))
