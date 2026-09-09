#!/usr/bin/env python3
"""Deterministic source contract for VANGUARD // OVERLAY RESURRECTION v2.

This gate intentionally fails against the retired legacy overlay. PASS proves only
repository source shape. It never proves compilation, deployment, microphone activity,
transcription quality, battery behavior, accessibility, or human acceptance.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "android" / "operator-overlay" / "app" / "src" / "main"
JAVA = APP / "java" / "com" / "homecenter" / "operatoroverlay"
MANIFEST = APP / "AndroidManifest.xml"
BUILD = ROOT / "android" / "operator-overlay" / "app" / "build.gradle"

checks: list[dict] = []


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def add(check: str, ok: bool, detail: str, path: Path | None = None) -> None:
    checks.append({"check": check, "ok": bool(ok), "detail": detail, "path": rel(path)})


def text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def contains(path: Path, *needles: str) -> bool:
    body = text(path)
    return all(needle in body for needle in needles)


def regex(path: Path, pattern: str) -> bool:
    return re.search(pattern, text(path), flags=re.I | re.S) is not None


manifest = text(MANIFEST)
build = text(BUILD)
overlay = JAVA / "OperatorOverlayService.java"
ring = JAVA / "RollingPcmRing.java"
transcript = JAVA / "RollingTranscriptEngine.java"
keep = JAVA / "ExplicitKeepStore.java"
opinion = JAVA / "OpinionChannel.java"
provider = JAVA / "OperatorStateProvider.java"
state = JAVA / "OperatorState.java"
boot = JAVA / "BootReceiver.java"
main_activity = JAVA / "MainActivity.java"
ambient = JAVA / "AmbientListeningService.java"

overlay_body = text(overlay)
boot_body = text(boot)
provider_body = text(provider)

# ---- Manifest / one-service architecture -----------------------------------
add("manifest_exists", bool(manifest), "Android manifest is readable.", MANIFEST)
add(
    "microphone_fgs_permission",
    "android.permission.FOREGROUND_SERVICE_MICROPHONE" in manifest,
    "Manifest declares FOREGROUND_SERVICE_MICROPHONE for targetSdk 34+ microphone foreground work.",
    MANIFEST,
)
add("record_audio_permission", "android.permission.RECORD_AUDIO" in manifest, "Manifest declares RECORD_AUDIO.", MANIFEST)
add(
    "target_sdk_current_enough",
    bool(re.search(r"targetSdk\s+(3[5-9]|[4-9][0-9])", build)),
    "Target SDK remains at least 35; implementation must obey current foreground-service restrictions.",
    BUILD,
)
operator_service_tag = re.search(r'<service\b(?=[^>]*android:name="\.OperatorOverlayService")[^>]*>', manifest, flags=re.I | re.S)
operator_tag = operator_service_tag.group(0) if operator_service_tag else ""
fgs_match = re.search(r'android:foregroundServiceType="([^"]+)"', operator_tag)
fgs_types = set((fgs_match.group(1) if fgs_match else "").split("|"))
add(
    "single_operator_service_declares_specialuse_microphone",
    bool(operator_tag) and {"specialUse", "microphone"}.issubset(fgs_types) and 'android:exported="false"' in operator_tag,
    "The existing OperatorOverlayService is the one non-exported foreground service and declares specialUse|microphone.",
    MANIFEST,
)
add(
    "no_ambient_listening_service",
    not ambient.exists() and ".AmbientListeningService" not in manifest,
    "No second AmbientListeningService daemon/service exists; microphone capture belongs to OperatorOverlayService.",
    ambient,
)

# ---- Existing service evolves instead of being replaced --------------------
add("operator_service_exists", overlay.exists(), "Existing OperatorOverlayService lineage remains the runtime authority.", overlay)
add(
    "typed_specialuse_startup",
    contains(overlay, "ServiceCompat.startForeground", "FOREGROUND_SERVICE_TYPE_SPECIAL_USE"),
    "OperatorOverlayService uses typed ServiceCompat foreground promotion and can start as specialUse without microphone.",
    overlay,
)
add(
    "visible_arm_contract",
    contains(overlay, "ACTION_ARM_LISTENING", "ACTION_STOP_LISTENING")
    and ("ACTION_ARM_LISTENING" in text(main_activity) or "ACTION_ARM_LISTENING" in overlay_body),
    "Explicit ARM/STOP actions exist and ARM is reachable from a visible app/overlay surface.",
    overlay,
)
add(
    "arm_adds_microphone_type_same_service",
    contains(overlay, "FOREGROUND_SERVICE_TYPE_MICROPHONE", "FOREGROUND_SERVICE_TYPE_SPECIAL_USE")
    and regex(overlay, r"FOREGROUND_SERVICE_TYPE_SPECIAL_USE\s*\|\s*(?:ServiceInfo\.)?FOREGROUND_SERVICE_TYPE_MICROPHONE|FOREGROUND_SERVICE_TYPE_MICROPHONE\s*\|\s*(?:ServiceInfo\.)?FOREGROUND_SERVICE_TYPE_SPECIAL_USE"),
    "Visible ARM upgrades this same foreground service to SPECIAL_USE|MICROPHONE before capture.",
    overlay,
)
add(
    "single_audio_record_owner",
    "AudioRecord" in overlay_body and "RollingPcmRing" in overlay_body and "RollingTranscriptEngine" in overlay_body,
    "One OperatorOverlayService AudioRecord stream fans into rolling raw + transcription pipelines.",
    overlay,
)
add(
    "stop_releases_microphone",
    contains(overlay, "ACTION_STOP_LISTENING", ".release()") and ("audioRecord.stop()" in overlay_body or ".stop();" in overlay_body),
    "STOP path visibly releases the microphone resource instead of only toggling UI state.",
    overlay,
)
add(
    "stop_clears_transient",
    "clearTransient" in overlay_body and "ACTION_STOP_LISTENING" in overlay_body,
    "STOP invokes transient-cache clearing after capture release.",
    overlay,
)
add(
    "mic_truth_not_type_mask",
    "mic_active" in provider_body and ("micActive" in text(state) or "mic_active" in text(state))
    and not regex(provider, r"mic_active.{0,200}FOREGROUND_SERVICE_TYPE_MICROPHONE"),
    "mic_active is explicit runtime state rather than inferred from the foreground-service type mask.",
    provider,
)

# ---- Boot privacy boundary --------------------------------------------------
add(
    "boot_never_arms_microphone",
    "ACTION_ARM_LISTENING" not in boot_body
    and "AudioRecord" not in boot_body
    and "FOREGROUND_SERVICE_TYPE_MICROPHONE" not in boot_body
    and "RollingPcmRing" not in boot_body,
    "BOOT_COMPLETED may restore the control shell but cannot arm/acquire microphone capture.",
    boot,
)
add(
    "boot_resets_listening_truth",
    ("setListeningOff" in boot_body or "resetTransient" in boot_body or "clearTransient" in boot_body or "ACTION_BOOT_DISARM" in boot_body),
    "Boot path explicitly disarms/resets transient listening state instead of restoring stale LISTENING truth.",
    boot,
)

# ---- Bounded raw buffer -----------------------------------------------------
add("ring_exists", ring.exists(), "RollingPcmRing implementation exists.", ring)
ring_body = text(ring)
add(
    "ring_is_fixed_capacity",
    contains(ring, "DEFAULT_RING_SECONDS", "DEFAULT_SAMPLE_RATE_HZ", "BYTES_PER_SAMPLE")
    and regex(ring, r"DEFAULT_RING_SECONDS\s*=\s*600\b")
    and regex(ring, r"DEFAULT_SAMPLE_RATE_HZ\s*=\s*48000\b")
    and regex(ring, r"BYTES_PER_SAMPLE\s*=\s*2\b")
    and ("RandomAccessFile" in ring_body or "FileChannel" in ring_body)
    and ("% capacity" in ring_body or "% capacityBytes" in ring_body or "Math.floorMod" in ring_body),
    "Default raw cache is a 10-minute, 48 kHz target, mono PCM16 fixed-capacity ring with physical wrap.",
    ring,
)
add(
    "ring_logical_positions",
    any(marker in ring_body for marker in ("logicalWrite", "logicalSample", "totalSamples", "totalBytesWritten")),
    "Ring exposes monotonic logical positions distinct from wrapped physical offsets.",
    ring,
)
add(
    "ring_private_storage",
    not regex(ring, r"Environment\.getExternalStorage|MediaStore|DIRECTORY_MUSIC|DIRECTORY_DOWNLOADS"),
    "Unkept rolling raw audio stays in app-private storage.",
    ring,
)
add(
    "ring_transient_clear",
    "clearTransient" in ring_body and any(marker in ring_body for marker in ("setLength", "truncate", "delete", "Arrays.fill")),
    "Ring exposes a real transient clear/reset operation, not only a pointer reset.",
    ring,
)

# ---- Rolling transcription --------------------------------------------------
add("transcript_engine_exists", transcript.exists(), "RollingTranscriptEngine exists.", transcript)
transcript_body = text(transcript)
add(
    "transcript_is_bounded_and_mapped",
    contains(transcript, "MAX_TRANSCRIPT_SEGMENTS", "startSample", "endSample", "text")
    and ("ArrayDeque" in transcript_body or "Deque" in transcript_body),
    "Transcript cache is bounded and maps each text segment to monotonic raw sample positions.",
    transcript,
)
add(
    "speech_recognizer_not_continuous_engine",
    "android.speech.SpeechRecognizer" not in transcript_body and "SpeechRecognizer.create" not in transcript_body,
    "Android SpeechRecognizer is not used as the continuous always-listening engine.",
    transcript,
)
add(
    "on_device_asr_contract",
    any(marker in transcript_body for marker in ("sherpa", "Sherpa", "ON_DEVICE_ASR", "OnDeviceAsr", "onDeviceAsr")),
    "Transcription identifies an on-device ASR implementation/provider path.",
    transcript,
)
add(
    "asr_failure_does_not_own_capture",
    not regex(transcript, r"(?:stopSelf|ACTION_STOP_LISTENING|audioRecord\.stop|audioRecord\.release)"),
    "ASR engine contains no authority to stop/release the deterministic microphone capture service.",
    transcript,
)
add(
    "transcript_transient_clear",
    "clearTransient" in transcript_body,
    "Rolling transcript can be purged on STOP/session reset.",
    transcript,
)

# ---- Explicit durable KEEP --------------------------------------------------
add("explicit_keep_store_exists", keep.exists(), "ExplicitKeepStore exists.", keep)
keep_body = text(keep)
add(
    "explicit_keep_contract",
    contains(keep, "ACTION_KEEP", "keepLastSeconds") and ("60" in keep_body or "DEFAULT_KEEP_SECONDS" in keep_body),
    "KEEP LAST 60s has an explicit store/API seam.",
    keep,
)
add(
    "explicit_keep_only",
    not regex(keep, r"auto.?keep|automatic.?keep|sentiment.*keep|important.*keep"),
    "No automatic durable promotion rule is present in the KEEP store.",
    keep,
)
add(
    "keep_bundle_metadata",
    all(marker in keep_body for marker in ("startSample", "endSample"))
    and any(marker in keep_body for marker in ("sampleRate", "sample_rate"))
    and any(marker in keep_body for marker in ("receipt", "bundleId", "bundle_id")),
    "Durable KEEP bundles retain sample bounds, actual format metadata and a receipt/id.",
    keep,
)

# ---- Opinion intelligence ---------------------------------------------------
add("opinion_channel_exists", opinion.exists(), "One structured OpinionChannel intelligence seam exists.", opinion)
opinion_body = text(opinion)
add(
    "ritsu_default_opinion",
    "Ritsu" in opinion_body and all(marker in opinion_body for marker in ("speaker", "text", "timestamp", "provenance", "provider")),
    "Ritsu is the default speaker and opinions carry structured provenance/provider metadata.",
    opinion,
)
add(
    "opinion_not_capture_dependency",
    "OpinionChannel" in overlay_body
    and not regex(overlay, r"(?s)(AudioRecord|read\s*\().{0,400}(awaitOpinion|requireOpinion|opinionFuture\.get|join\(\))"),
    "Opinion integration is present but the PCM hot path does not synchronously depend on intelligence completion.",
    overlay,
)
add(
    "no_model_network_in_ring",
    not regex(ring, r"OkHttp|HttpURLConnection|URL\(|Socket\(|Retrofit|WebSocket|OpenAI|Anthropic|Gemini"),
    "Raw ring primitive contains no model/network client.",
    ring,
)
add(
    "no_model_network_in_keep",
    not regex(keep, r"OkHttp|HttpURLConnection|URL\(|Socket\(|Retrofit|WebSocket|OpenAI|Anthropic|Gemini"),
    "KEEP primitive contains no model/network dependency.",
    keep,
)

# ---- UI state / liveness ----------------------------------------------------
add(
    "overlay_modes",
    all(marker in overlay_body for marker in ("FULL", "BUBBLE", "HIDDEN")),
    "Overlay exposes full, bubble and hidden presentation modes independently of listening.",
    overlay,
)
add(
    "notification_restore_path",
    "ACTION_RESTORE" in overlay_body and "PendingIntent" in overlay_body and "NOTIFICATION_ID" in overlay_body,
    "The single heartbeat notification can restore the overlay after HIDDEN.",
    overlay,
)
add(
    "hide_does_not_stop_listening",
    not regex(overlay, r"(?s)(hideOverlay|HIDDEN).{0,300}(ACTION_STOP_LISTENING|stopListening|audioRecord\.stop|audioRecord\.release)"),
    "Hiding presentation does not implicitly stop microphone capture.",
    overlay,
)
add(
    "legacy_dashboard_removed",
    "SpotifyShizukuClient" not in overlay_body
    and not any(marker in overlay_body for marker in ('"TERM"', '"CHAT"', '"CONT"', '"VLAD"', '"RADIO"')),
    "Spotify and legacy mode-wall controls are absent from the resurrected primary overlay service.",
    overlay,
)
add(
    "no_200ms_ui_poll",
    not regex(overlay, r"REFRESH_MS\s*=\s*200\b"),
    "The old 200 ms perpetual UI refresh loop is not restored unchanged.",
    overlay,
)

# ---- Machine-readable acceptance state -------------------------------------
required_state_fields = (
    "overlay_mode",
    "listening_state",
    "mic_active",
    "ring_write_bytes",
    "ring_capacity_bytes",
    "transcript_segment_count",
    "last_transcript_at_ms",
    "keep_count",
    "actual_sample_rate_hz",
    "latest_error",
    "opinion_speaker",
    "opinion_provider_state",
)
add(
    "observable_state_provider",
    all(field in provider_body for field in required_state_fields),
    "OperatorStateProvider exposes stable machine-readable fields for physical acceptance and intelligence isolation.",
    provider,
)

# ---- Runtime exclusion / storage regression scars --------------------------
runtime_paths = list(JAVA.glob("*.java")) + [MANIFEST]
adam_hits: list[str] = []
for path in runtime_paths:
    for line_no, line in enumerate(text(path).splitlines(), 1):
        if re.search(r"\badam\b", line, flags=re.I):
            adam_hits.append(f"{rel(path)}:{line_no}")
add(
    "adam_runtime_exclusion",
    not adam_hits,
    "Adam is absent from runtime labels, prompts, routes, fallbacks and recovery code." if not adam_hits else "Runtime Adam references: " + ", ".join(adam_hits[:30]),
)

append_only_raw: list[str] = []
for path in JAVA.glob("*.java"):
    body = text(path)
    if re.search(r"FileOutputStream\s*\([^\n]+,\s*true\s*\)", body):
        append_only_raw.append(rel(path) or str(path))
add(
    "no_append_only_raw_audio",
    not append_only_raw,
    "Runtime source contains no obvious append-only raw-audio FileOutputStream pattern." if not append_only_raw else "Append-only candidates: " + ", ".join(append_only_raw),
)

failed = [row for row in checks if not row["ok"]]
result = {
    "schema": "vanguard-overlay-source-contract-v2-single-service",
    "ok": not failed,
    "scope": "repository-source-only",
    "architecture": "existing OperatorOverlayService; one foreground service; specialUse startup; visible ARM adds microphone; one heartbeat; bounded transient cache; Ritsu OpinionChannel",
    "truthBoundary": "PASS proves source contract shape only; it does not prove compile, deployment, callable phone behavior, microphone privacy indicator, transcript accuracy, accessibility, battery/thermal behavior, or acceptance.",
    "checks": checks,
    "failed": [row["check"] for row in failed],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if not failed else 1)
