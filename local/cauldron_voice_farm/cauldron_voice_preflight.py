#!/usr/bin/env python3
"""Reversible local voice-render preflight for THECAULDRON."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any

SCHEMA_VERSION = "home-center.cauldron-voice-preflight-receipt.v1"
CONSENT_SCHEMA_VERSION = "home-center.voice-consent.v1"
SUPPORTED_ENGINES = {"kokoro", "chatterbox-nano", "chatterbox-turbo"}


class PreflightError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_text(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text)).strip()
    if not value:
        raise PreflightError("EMPTY_TEXT")
    return value


def split_text(text: str, max_chars: int = 320) -> dict[str, Any]:
    if max_chars < 32:
        raise PreflightError("SEGMENT_LIMIT_TOO_SMALL")
    normalized = canonical_text(text)
    words = normalized.split(" ")
    segments: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            if current:
                segments.append(current)
                current = ""
            segments.extend(word[i : i + max_chars] for i in range(0, len(word), max_chars))
            continue
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            segments.append(current)
            current = word
    if current:
        segments.append(current)
    if not segments or " ".join(segments) != normalized:
        raise PreflightError("SPLIT_PLAN_ORDER_MISMATCH")
    return {
        "schemaVersion": "home-center.voice-split-plan.v1",
        "automatic": True,
        "separateSplitOperation": False,
        "maxSegmentChars": max_chars,
        "normalizedText": normalized,
        "normalizedTextSha256": sha256_bytes(normalized.encode()),
        "segments": [
            {"index": index, "text": segment, "sha256": sha256_bytes(segment.encode())}
            for index, segment in enumerate(segments)
        ],
    }


def validate_consent(reference: Path, consent_path: Path) -> dict[str, Any]:
    if not reference.is_file():
        raise PreflightError("REFERENCE_AUDIO_MISSING")
    if not consent_path.is_file():
        raise PreflightError("CONSENT_RECORD_MISSING")
    try:
        consent = json.loads(consent_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError("CONSENT_RECORD_INVALID") from exc
    if consent.get("schemaVersion") != CONSENT_SCHEMA_VERSION:
        raise PreflightError("CONSENT_SCHEMA_UNSUPPORTED")
    if "local_tts_clone" not in consent.get("permittedUses", []):
        raise PreflightError("CONSENT_USE_NOT_PERMITTED")
    if not str(consent.get("speakerOwner", "")).strip() or not str(consent.get("consentAuthority", "")).strip():
        raise PreflightError("CONSENT_AUTHORITY_MISSING")
    digest = sha256_file(reference)
    if str(consent.get("referenceSha256", "")).lower() != digest:
        raise PreflightError("REFERENCE_HASH_MISMATCH")
    return {**consent, "referenceSha256": digest}


def request_identity(engine: str, text: str, voice: str, reference_sha256: str, max_chars: int) -> tuple[str, dict[str, Any]]:
    if engine not in SUPPORTED_ENGINES:
        raise PreflightError("ENGINE_UNSUPPORTED")
    payload = {
        "engine": engine,
        "text": canonical_text(text),
        "voice": voice,
        "referenceSha256": reference_sha256,
        "maxSegmentChars": max_chars,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(encoded), payload


def inventory_tree(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    return [
        {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    ]


def distributions() -> list[dict[str, str]]:
    rows = []
    for dist in importlib.metadata.distributions():
        name = str(dist.metadata.get("Name", "")).strip()
        if name:
            rows.append({"name": name, "version": dist.version})
    return sorted(rows, key=lambda item: item["name"].lower())


def render_segment(engine: str, text: str, output: Path, args: argparse.Namespace) -> None:
    if engine == "kokoro":
        try:
            import soundfile as sf
            from kokoro_onnx import Kokoro
        except ImportError as exc:
            raise PreflightError("KOKORO_ENVIRONMENT_INCOMPLETE") from exc
        model = args.model_dir / "kokoro-v1.0.onnx"
        voices = args.model_dir / "voices-v1.0.bin"
        if not model.is_file() or not voices.is_file():
            raise PreflightError("KOKORO_MODEL_FILES_MISSING")
        samples, rate = Kokoro(str(model), str(voices)).create(text, voice=args.voice, speed=1.0, lang="en-us")
        sf.write(str(output), samples, rate, subtype="PCM_16")
        return
    try:
        import torchaudio as ta
        from chatterbox.tts_turbo import ChatterboxTurboTTS
    except ImportError as exc:
        raise PreflightError("CHATTERBOX_ENVIRONMENT_INCOMPLETE") from exc
    model = ChatterboxTurboTTS.from_pretrained(device=args.device, nano=engine == "chatterbox-nano")
    audio = model.generate(text, audio_prompt_path=str(args.reference))
    ta.save(str(output), audio, model.sr)


def join_wav(paths: list[Path], output: Path, pause_ms: int) -> dict[str, Any]:
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise PreflightError("AUDIO_JOIN_ENVIRONMENT_INCOMPLETE") from exc
    clips, rate, channels = [], 0, 0
    for index, path in enumerate(paths):
        audio, found_rate = sf.read(str(path), dtype="float32", always_2d=True)
        if not len(audio):
            raise PreflightError("EMPTY_AUDIO")
        if not rate:
            rate, channels = int(found_rate), int(audio.shape[1])
        if int(found_rate) != rate or int(audio.shape[1]) != channels:
            raise PreflightError("SEGMENT_AUDIO_FORMAT_MISMATCH")
        clips.append(audio)
        if index < len(paths) - 1 and pause_ms:
            clips.append(np.zeros((round(rate * pause_ms / 1000), channels), dtype=np.float32))
    joined = np.concatenate(clips, axis=0)
    peak = float(np.max(np.abs(joined)))
    if not peak > 0.0001 or math.isnan(peak):
        raise PreflightError("OUTPUT_SILENT")
    sf.write(str(output), joined, rate, subtype="PCM_16")
    return {
        "sampleRate": rate,
        "channels": channels,
        "frames": int(joined.shape[0]),
        "durationSeconds": float(joined.shape[0] / rate),
        "peak": peak,
        "nonSilent": True,
    }


def render(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    if (root / "state" / "paused").exists():
        raise PreflightError("FARM_PAUSED")
    reference_sha, consent = "", None
    if args.engine.startswith("chatterbox"):
        if not args.reference or not args.consent:
            raise PreflightError("CONSENTED_REFERENCE_REQUIRED")
        consent = validate_consent(args.reference.resolve(), args.consent.resolve())
        reference_sha = consent["referenceSha256"]
    plan = split_text(args.text, args.max_segment_chars)
    input_sha, canonical = request_identity(args.engine, args.text, args.voice, reference_sha, args.max_segment_chars)
    receipt_path = root / "receipts" / f"{args.request_id}.json"
    if receipt_path.exists():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("inputSha256") != input_sha:
            raise PreflightError("IDEMPOTENCY_CONFLICT")
        return existing
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="cauldron-voice-") as temp:
        segment_paths, results = [], []
        for segment in plan["segments"]:
            path = Path(temp) / f"segment-{segment['index']:03d}.wav"
            segment_started = time.perf_counter()
            render_segment(args.engine, segment["text"], path, args)
            segment_paths.append(path)
            results.append({
                "index": segment["index"],
                "elapsedSeconds": time.perf_counter() - segment_started,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
        metrics = join_wav(segment_paths, args.output.resolve(), args.pause_ms)
    receipt = {
        "schemaVersion": SCHEMA_VERSION,
        "requestId": args.request_id,
        "inputSha256": input_sha,
        "canonicalRequest": canonical,
        "engine": args.engine,
        "device": args.device,
        "voice": args.voice,
        "consent": consent,
        "splitPlan": plan,
        "segmentResults": results,
        "output": {
            "path": str(args.output.resolve()),
            "bytes": args.output.stat().st_size,
            "sha256": sha256_file(args.output),
            **metrics,
        },
        "elapsedSeconds": time.perf_counter() - started,
        "installedDistributions": distributions(),
        "modelCacheFiles": inventory_tree(root / "cache" / "huggingface"),
        "capabilityState": "local_preflight_rendered",
        "humanAcceptance": "unreviewed",
    }
    encoded = json.dumps(receipt, indent=2) + "\n"
    receipt_path.write_text(encoded, encoding="utf-8")
    args.output.with_suffix(args.output.suffix + ".receipt.json").write_text(encoded, encoding="utf-8")
    return receipt


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=sorted(SUPPORTED_ENGINES), required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, default=Path("models/kokoro"))
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--consent", type=Path)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--max-segment-chars", type=int, default=320)
    parser.add_argument("--pause-ms", type=int, default=80)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        print(json.dumps(render(parse_args(argv or sys.argv[1:])), indent=2))
        return 0
    except PreflightError as exc:
        print(json.dumps({"ok": False, "errorCode": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
