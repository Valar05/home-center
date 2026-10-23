#!/usr/bin/env python3
"""One-time, reversible -1 semitone reference preparation, no GPU or generated speech."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

HOME = Path.home()
ROOT = HOME / "workspace" / "ritsu-faster-qwen3-tts"
STAGED = Path(os.environ.get("LOCALAPPDATA", str(HOME))) / "RitsuWarmTicketWorker" / "staged-repertoire"
CATALOG = STAGED / "ritsu_voice_profiles.json"
ORIGINAL = HOME / "workspace" / "ritsu-expresso-auditions"
DESTINATION = ROOT / "ritsu-pitched-references"
MANIFEST = DESTINATION / "bake-manifest.json"
DEFAULT_FFMPEG = (HOME / "Downloads" / "ffmpeg-2025-10-09-git-469aad3897-full_build" /
                  "ffmpeg-2025-10-09-git-469aad3897-full_build" / "bin" / "ffmpeg.exe")
PITCH = math.pow(2, -1 / 12)


def digest(file):
    h = hashlib.sha256()
    with file.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run():
    data = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    names = ("normal", "whisper", "amused", "happy", "upset", "somber")
    profiles = data["profiles"]
    if tuple(sorted(profiles)) != tuple(sorted(names)):
        raise RuntimeError("Catalog is not exactly the six approved Ritsu profiles")
    if any(profiles[name]["pitchSemitones"] != -1 for name in names):
        raise RuntimeError("All profiles must declare exactly -1 semitone")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        ffmpeg = str(DEFAULT_FFMPEG)
    if not Path(ffmpeg).is_file():
        raise RuntimeError("FFmpeg executable unavailable")
    probe = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=20)
    if probe.returncode or "rubberband" not in probe.stdout:
        raise RuntimeError("FFmpeg lacks the formant-preserving rubberband filter")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = {}
    for name in names:
        filename = profiles[name]["referenceFile"]
        if filename != Path(filename).name or not filename.endswith(".wav"):
            raise RuntimeError("Unsafe reference basename")
        src = ORIGINAL / filename
        if not src.is_file():
            raise FileNotFoundError(f"Source recording missing for {name}")
        target = DESTINATION / filename
        tmp = DESTINATION / (filename + ".incomplete.wav")
        if tmp.exists():
            tmp.unlink()
        # This modifies a COPY of the audition sample. Original never touched.
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-i", str(src), "-af", f"rubberband=pitch={PITCH:.12f}:formant=preserved",
               "-c:a", "pcm_s16le", str(tmp)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if p.returncode or not tmp.is_file() or tmp.stat().st_size < 300:
            raise RuntimeError(f"Failed to bake reference {name}: {(p.stderr or '')[-250:]}")
        os.replace(tmp, target)
        records[name] = {
            "source": str(src), "sourceSha256": digest(src),
            "baked": str(target), "bakedSha256": digest(target),
            "pitchSemitonesBaked": -1, "rubberbandFormant": "preserved"
        }
    staging = MANIFEST.with_suffix(".json.tmp")
    staging.write_text(json.dumps({"version": data["version"], "references": records}, indent=2), encoding="utf-8")
    os.replace(staging, MANIFEST)
    print("BAKED_SIX_REFERENCES_OK", len(records))
    print("MANIFEST", MANIFEST)
    print("NO_GENERATED_AUDIO_POSTPROCESSING")


if __name__ == "__main__":
    run()
