#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Iterable

REPO = Path(os.environ.get(
    "FORTRESS_HOME_CENTER",
    "/storage/emulated/0/Documents/GodotProjects/home-center",
))
PERFORMANCE_CONFIG = Path(os.environ.get(
    "FORTRESS_POCKET_TTS_PERFORMANCE_CONFIG",
    str(REPO / "config/fortress-pocket-tts-performance.json"),
))
STABLE_CORE = Path.home() / ".local/lib/home-center/embodied-communication/fortress_read_aloud.py"
REPO_CORE = REPO / "tools/fortress_read_aloud.py"


def load_core():
    for path in (STABLE_CORE, REPO_CORE):
        if path.is_file():
            spec = importlib.util.spec_from_file_location("fortress_read_aloud", path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module, path
    raise RuntimeError("fortress-read core unavailable")


def load_performance(persona: str) -> tuple[dict, dict]:
    raw = json.loads(PERFORMANCE_CONFIG.read_text(encoding="utf-8"))
    if raw.get("engineLock") != "pocket-tts-phone":
        raise RuntimeError("performance config violated Pocket TTS engine lock")
    if raw.get("providerLock") != "pocket-home-center":
        raise RuntimeError("performance config violated provider lock")
    if raw.get("playbackLock") != "com.dclar.homecenter/.PocketTtsPlaybackActivity":
        raise RuntimeError("performance config violated playback component lock")
    if raw.get("systemFallbackAllowed") is not False or raw.get("cloudFallbackAllowed") is not False:
        raise RuntimeError("performance config attempted a forbidden fallback")
    selected = raw.get("personas", {}).get(persona)
    if not isinstance(selected, dict):
        raise RuntimeError(f"unknown performance persona: {persona}")
    return raw, selected


def audio_filter(sample_rate: int, tempo: float, pitch_semitones: float) -> str:
    if not (1.0 <= tempo <= 1.5):
        raise RuntimeError("tempo outside bounded Nightcore contract")
    if not (0.0 <= pitch_semitones <= 12.0):
        raise RuntimeError("pitch outside bounded Nightcore contract")
    pitch_factor = 2.0 ** (pitch_semitones / 12.0)
    atempo = tempo / pitch_factor
    if not (0.5 <= atempo <= 100.0):
        raise RuntimeError("derived atempo outside ffmpeg supported range")
    raised_rate = sample_rate * pitch_factor
    return f"asetrate={raised_rate:.6f},aresample={sample_rate},atempo={atempo:.8f}"


def postprocess(path: Path, persona: dict, index: int) -> tuple[Path, dict]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Nightcore status blocked: local ffmpeg unavailable")
    with wave.open(str(path), "rb") as handle:
        sample_rate = int(handle.getframerate())
    tempo = float(persona["tempo"])
    pitch = float(persona["pitchSemitones"])
    filt = audio_filter(sample_rate, tempo, pitch)
    output = path.with_name(f"{path.stem}.nightcore-{index}.wav")
    proc = subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(path),
            "-af", filt,
            "-c:a", "pcm_s16le",
            str(output),
        ],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if proc.returncode or not output.is_file():
        raise RuntimeError((proc.stderr or proc.stdout or "ffmpeg Nightcore transform failed")[-3000:])
    return output, {
        "kind": "ffmpeg-nightcore",
        "tempo": tempo,
        "pitchSemitones": pitch,
        "filter": filt,
        "reversible": True,
        "systemFallbackUsed": False,
        "cloudFallbackUsed": False,
    }


def doctor(persona_name: str) -> dict:
    core, core_path = load_core()
    config, persona = load_performance(persona_name)
    core_doctor = core.doctor()
    ffmpeg = shutil.which("ffmpeg") or ""
    return {
        "ok": bool(core_doctor.get("ok") and ffmpeg),
        "provider": "pocket-home-center",
        "engine": "pocket-tts-phone",
        "transport": "shizuku-rish",
        "outputComponent": "com.dclar.homecenter/.PocketTtsPlaybackActivity",
        "persona": persona_name,
        "performance": persona,
        "performanceSchema": config.get("schema"),
        "corePath": str(core_path),
        "ffmpeg": ffmpeg,
        "coreDoctor": core_doctor,
        "systemFallbackAllowed": False,
        "cloudFallbackAllowed": False,
    }


def speak(text: str, persona_name: str) -> dict:
    core, core_path = load_core()
    _, persona = load_performance(persona_name)
    core_doctor = core.doctor()
    if not core_doctor.get("ok"):
        raise RuntimeError("Pocket Space core blocked: " + str(core_doctor.get("blockedReason", "unknown")))
    if not shutil.which("ffmpeg"):
        raise RuntimeError("Nightcore status blocked: local ffmpeg unavailable")

    normalized = " ".join(text.split()).strip()
    if not normalized:
        raise RuntimeError("empty status transcript")
    max_chars = int(persona.get("utteranceMaxChars", 240))
    if len(normalized) > max_chars:
        raise RuntimeError(
            f"status transcript exceeds persona utteranceMaxChars ({len(normalized)} > {max_chars}); compress before speech"
        )

    selected = core.profile()
    if persona.get("voice"):
        selected["voiceValue"] = str(persona["voice"])

    raw_files: list[Path] = []
    processed_files: list[Path] = []
    playback_receipts: list[dict] = []
    processing_receipts: list[dict] = []
    total_seconds = 0.0
    try:
        chunks = list(core.chunks_from_text(normalized))
        for index, chunk in enumerate(chunks):
            raw = core.synthesize_chunk(chunk, index, selected)
            raw_files.append(raw)
            processed, processing = postprocess(raw, persona, index)
            processed_files.append(processed)
            playback = core.play_home_center(processed)
            processing_receipts.append(processing)
            playback_receipts.append(playback)
            total_seconds += float(playback.get("audioSeconds", 0.0))
        verified = bool(playback_receipts) and all(
            item.get("playStartObserved") and item.get("playCompletedObserved")
            for item in playback_receipts
        )
        return {
            "ok": verified,
            "provider": "pocket-home-center",
            "engine": "pocket-tts-phone",
            "transport": "shizuku-rish",
            "outputComponent": "com.dclar.homecenter/.PocketTtsPlaybackActivity",
            "playbackVerified": verified,
            "persona": persona_name,
            "role": persona.get("role", ""),
            "transcript": normalized,
            "voice": selected.get("voiceValue"),
            "textChunks": len(playback_receipts),
            "characters": len(normalized),
            "audioSeconds": round(total_seconds, 3),
            "processingReceipts": processing_receipts,
            "playbackReceipts": playback_receipts,
            "corePath": str(core_path),
            "systemFallbackUsed": False,
            "cloudFallbackUsed": False,
        }
    finally:
        for path in processed_files + raw_files:
            try:
                path.unlink()
            except OSError:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fortress-status-read",
        description="Pocket Space TTS status speech with bounded local Nightcore ASMR post-processing",
    )
    parser.add_argument("--persona", choices=["orandroid67", "she-ra"], default="orandroid67")
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("text", nargs="*")
    args = parser.parse_args()
    if args.doctor:
        output = doctor(args.persona)
    else:
        output = speak(" ".join(args.text), args.persona)
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
