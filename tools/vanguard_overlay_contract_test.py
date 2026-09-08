#!/usr/bin/env python3
"""Deterministic source-contract gate for VANGUARD // OVERLAY RESURRECTION.

This gate intentionally fails against the retired legacy overlay. It becomes green only
when the commissioned native Android architecture exists. It proves source shape only;
it never proves APK build, phone deployment, microphone activity, transcription quality,
or human acceptance.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "android" / "operator-overlay" / "app" / "src" / "main"
JAVA = APP / "java" / "com" / "homecenter" / "operatoroverlay"
MANIFEST = APP / "AndroidManifest.xml"
BUILD = ROOT / "android" / "operator-overlay" / "app" / "build.gradle"

checks: list[dict] = []


def add(check: str, ok: bool, detail: str, path: Path | None = None) -> None:
    checks.append({
        "check": check,
        "ok": bool(ok),
        "detail": detail,
        "path": str(path.relative_to(ROOT)) if path and path.exists() else (str(path.relative_to(ROOT)) if path else None),
    })


def text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def contains(path: Path, *needles: str) -> bool:
    body = text(path)
    return all(n in body for n in needles)


def regex(path: Path, pattern: str) -> bool:
    return re.search(pattern, text(path), flags=re.I | re.S) is not None


manifest = text(MANIFEST)
build = text(BUILD)
ambient = JAVA / "AmbientListeningService.java"
ring = JAVA / "RollingPcmRing.java"
transcript = JAVA / "RollingTranscriptEngine.java"
keep = JAVA / "ExplicitKeepStore.java"
overlay = JAVA / "OperatorOverlayService.java"
provider = JAVA / "OperatorStateProvider.java"
boot = JAVA / "BootReceiver.java"
main_activity = JAVA / "MainActivity.java"

add("manifest_exists", bool(manifest), "Android manifest is readable.", MANIFEST)
add(
    "microphone_fgs_permission",
    "android.permission.FOREGROUND_SERVICE_MICROPHONE" in manifest,
    "Manifest declares FOREGROUND_SERVICE_MICROPHONE for Android 14+ microphone FGS.",
    MANIFEST,
)
add(
    "ambient_listening_service_declared",
    regex(MANIFEST, r'<service[^>]+android:name="\.AmbientListeningService"[^>]+android:foregroundServiceType="[^"]*microphone[^"]*"'),
    "AmbientListeningService is a non-boot microphone foreground service.",
    MANIFEST,
)
add(
    "record_audio_permission",
    "android.permission.RECORD_AUDIO" in manifest,
    "Manifest keeps RECORD_AUDIO runtime permission.",
    MANIFEST,
)
add(
    "target_sdk_current_enough",
    bool(re.search(r"targetSdk\s+(3[5-9]|[4-9][0-9])", build)),
    "Target SDK remains at least 35; campaign handles Android 14+ while-in-use microphone rules.",
    BUILD,
)

add("ambient_service_exists", ambient.exists(), "Native ambient microphone service exists.", ambient)
add(
    "ambient_service_contract",
    contains(ambient, "ACTION_ARM_LISTENING", "ACTION_STOP_LISTENING", "AudioRecord", "RollingPcmRing", "RollingTranscriptEngine"),
    "Ambient service exposes explicit arm/stop actions and fans one AudioRecord stream into ring + transcription.",
    ambient,
)
add(
    "ambient_service_foreground",
    regex(ambient, r"startForeground\s*\(|ServiceCompat\.startForeground\s*\("),
    "Ambient microphone capture promotes itself to a foreground service.",
    ambient,
)
add(
    "ambient_service_no_boot_arm",
    "AmbientListeningService" not in text(boot) and "ACTION_ARM_LISTENING" not in text(boot),
    "BOOT_COMPLETED never arms microphone capture; reboot is intentionally disarmed.",
    boot,
)
add(
    "visible_user_arm_path",
    contains(main_activity, "ACTION_ARM_LISTENING") or contains(overlay, "ACTION_ARM_LISTENING"),
    "A visible app/overlay action can explicitly arm listening after runtime permission is available.",
    main_activity if "ACTION_ARM_LISTENING" in text(main_activity) else overlay,
)

add("ring_exists", ring.exists(), "Fixed-capacity PCM ring implementation exists.", ring)
add(
    "ring_is_fixed_capacity",
    contains(ring, "DEFAULT_RING_SECONDS", "DEFAULT_SAMPLE_RATE_HZ", "BYTES_PER_SAMPLE")
    and regex(ring, r"DEFAULT_RING_SECONDS\s*=\s*600\b")
    and regex(ring, r"DEFAULT_SAMPLE_RATE_HZ\s*=\s*48000\b")
    and regex(ring, r"BYTES_PER_SAMPLE\s*=\s*2\b")
    and ("RandomAccessFile" in text(ring) or "FileChannel" in text(ring))
    and ("% capacity" in text(ring) or "% capacityBytes" in text(ring) or "Math.floorMod" in text(ring)),
    "Default raw cache is a 10-minute, 48 kHz mono PCM16 bounded ring rather than append-only recording.",
    ring,
)
add(
    "ring_private_storage",
    not regex(ring, r"Environment\.getExternalStorage|MediaStore|DIRECTORY_MUSIC|DIRECTORY_DOWNLOADS"),
    "Rolling raw audio stays in app-private storage until explicit KEEP promotion.",
    ring,
)

add("transcript_engine_exists", transcript.exists(), "Rolling transcription engine exists.", transcript)
add(
    "transcript_is_rolling",
    contains(transcript, "MAX_TRANSCRIPT_SEGMENTS", "startSample", "endSample", "text")
    and ("ArrayDeque" in text(transcript) or "Deque" in text(transcript)),
    "Transcript cache is bounded and each segment maps text back to raw-audio sample offsets.",
    transcript,
)
add(
    "speech_recognizer_not_continuous_engine",
    "android.speech.SpeechRecognizer" not in text(transcript) and "SpeechRecognizer.create" not in text(transcript),
    "Android SpeechRecognizer is not used as the continuous always-listening engine.",
    transcript,
)
add(
    "on_device_asr_contract",
    any(marker in text(transcript) for marker in ("sherpa", "Sherpa", "ON_DEVICE_ASR", "OnDeviceAsr")),
    "Transcription implementation identifies an on-device ASR path; cloud speech is not the primary capture loop.",
    transcript,
)

add("explicit_keep_store_exists", keep.exists(), "Explicit KEEP promotion store exists.", keep)
add(
    "explicit_keep_only",
    contains(keep, "ACTION_KEEP", "keep") and not regex(keep, r"auto.?keep|automatic.?keep"),
    "Durable audio/text promotion is explicit; ordinary rolling cache does not self-archive.",
    keep,
)

add(
    "overlay_modes",
    all(marker in text(overlay) for marker in ("FULL", "BUBBLE", "HIDDEN")),
    "Overlay exposes full, bubble, and hidden presentation modes independently of listening state.",
    overlay,
)
add(
    "overlay_restore_notification_path",
    "ACTION_RESTORE" in text(overlay) and ("PendingIntent" in text(overlay) or "setContentIntent" in text(overlay)),
    "Heartbeat notification can restore the overlay after it is fully hidden.",
    overlay,
)
add(
    "hide_does_not_disable_listening",
    not regex(overlay, r"(?s)(hide|HIDDEN).{0,260}(ACTION_STOP_LISTENING|stopListening|stopSelf\s*\()"),
    "Hiding presentation does not implicitly stop microphone capture.",
    overlay,
)

provider_body = text(provider)
required_state_fields = (
    "overlay_mode",
    "listening_state",
    "mic_active",
    "ring_write_bytes",
    "ring_capacity_bytes",
    "transcript_segment_count",
    "last_transcript_at_ms",
    "keep_count",
)
add(
    "observable_state_provider",
    all(field in provider_body for field in required_state_fields),
    "State provider exposes enough machine-readable phone evidence for campaign verification.",
    provider,
)

runtime_paths = list(JAVA.glob("*.java")) + [MANIFEST]
adam_hits = []
for path in runtime_paths:
    for line_no, line in enumerate(text(path).splitlines(), 1):
        if re.search(r"\badam\b", line, flags=re.I):
            adam_hits.append(f"{path.relative_to(ROOT)}:{line_no}")
add(
    "adam_runtime_exclusion",
    not adam_hits,
    "Adam is absent from runtime labels, prompts, routes, fallbacks, and recovery code." if not adam_hits else "Runtime Adam references: " + ", ".join(adam_hits[:20]),
)

forbidden_raw_patterns = []
for path in JAVA.glob("*.java"):
    body = text(path)
    if re.search(r"FileOutputStream\s*\([^\n]+,\s*true\s*\)", body):
        forbidden_raw_patterns.append(str(path.relative_to(ROOT)))
add(
    "no_append_only_raw_audio",
    not forbidden_raw_patterns,
    "Runtime source contains no obvious append-only raw-audio FileOutputStream pattern."
    if not forbidden_raw_patterns else "Append-only patterns: " + ", ".join(forbidden_raw_patterns),
)

failed = [row for row in checks if not row["ok"]]
result = {
    "schema": "vanguard-overlay-source-contract-v1",
    "ok": not failed,
    "scope": "repository-source-only",
    "truthBoundary": "PASS proves source contract shape only; it does not prove build, deployment, callable phone behavior, transcript accuracy, battery behavior, or acceptance.",
    "checks": checks,
    "failed": [row["check"] for row in failed],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if not failed else 1)
