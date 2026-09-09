#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "fortress.loopscore.v1"


class ScoreError(ValueError):
    pass


def _nonnegative_int(value: Any, label: str, *, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ScoreError(f"{label} must be a non-negative integer")
    if maximum is not None and value > maximum:
        raise ScoreError(f"{label} must be <= {maximum}")
    return value


def _positive_int(value: Any, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise ScoreError(f"{label} must be greater than zero")
    return result


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScoreError(f"{label} must be a non-empty string")
    return value.strip()


def _stable_take_index(seed: str, track_id: str, ordinal: int, take_count: int) -> int:
    payload = f"{seed}\0{track_id}\0{ordinal}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") % take_count


def _canonical_hash(raw: dict[str, Any]) -> str:
    encoded = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_tracks(raw_tracks: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(raw_tracks, dict) or not raw_tracks:
        raise ScoreError("tracks must be a non-empty object")
    tracks: dict[str, list[dict[str, Any]]] = {}
    for track_id, track in raw_tracks.items():
        track_name = _required_text(track_id, "track id")
        if not isinstance(track, dict):
            raise ScoreError(f"track {track_name!r} must be an object")
        takes = track.get("takes")
        if not isinstance(takes, list) or not takes:
            raise ScoreError(f"track {track_name!r} must contain at least one take")
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, take in enumerate(takes):
            if not isinstance(take, dict):
                raise ScoreError(f"track {track_name!r} take {index} must be an object")
            take_id = _required_text(take.get("id"), f"track {track_name!r} take id")
            if take_id in seen:
                raise ScoreError(f"track {track_name!r} repeats take id {take_id!r}")
            seen.add(take_id)
            normalized.append({
                "id": take_id,
                "source": _required_text(take.get("source"), f"track {track_name!r} take {take_id!r} source"),
                "durationMs": _positive_int(take.get("durationMs"), f"track {track_name!r} take {take_id!r} durationMs"),
            })
        tracks[track_name] = normalized
    return tracks


def compile_score(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ScoreError("score root must be an object")
    if raw.get("schema") != SCHEMA:
        raise ScoreError(f"schema must be {SCHEMA!r}")

    score_id = _required_text(raw.get("id"), "id")
    seed = str(raw.get("seed", score_id))
    default_crossfade = _nonnegative_int(raw.get("defaultCrossfadeMs", 24), "defaultCrossfadeMs", maximum=250)
    tracks = _normalize_tracks(raw.get("tracks"))
    segments = raw.get("score")
    if not isinstance(segments, list) or not segments:
        raise ScoreError("score must be a non-empty array")

    events: list[dict[str, Any]] = []
    cursor = 0
    take_ordinals: dict[str, int] = {track_id: 0 for track_id in tracks}
    previous_take: dict[str, str] = {}

    def append_silence(duration_ms: int, *, reason: str) -> None:
        nonlocal cursor
        if duration_ms == 0:
            return
        events.append({
            "kind": "silence",
            "startMs": cursor,
            "durationMs": duration_ms,
            "reason": reason,
        })
        cursor += duration_ms

    def append_track_take(track_id: str, *, crossfade_ms: int) -> None:
        nonlocal cursor
        if track_id not in tracks:
            raise ScoreError(f"unknown track {track_id!r}")
        takes = tracks[track_id]
        ordinal = take_ordinals[track_id]
        index = _stable_take_index(seed, track_id, ordinal, len(takes))
        if len(takes) > 1 and previous_take.get(track_id) == takes[index]["id"]:
            index = (index + 1) % len(takes)
        take = takes[index]
        applied_crossfade = min(crossfade_ms, take["durationMs"] // 2)
        if events and events[-1]["kind"] in {"clip", "speech"} and applied_crossfade:
            cursor = max(0, cursor - applied_crossfade)
        else:
            applied_crossfade = 0
        events.append({
            "kind": "clip",
            "track": track_id,
            "take": take["id"],
            "source": take["source"],
            "startMs": cursor,
            "durationMs": take["durationMs"],
            "crossfadeInMs": applied_crossfade,
            "selectionOrdinal": ordinal,
        })
        cursor += take["durationMs"]
        take_ordinals[track_id] += 1
        previous_take[track_id] = take["id"]

    for segment_index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ScoreError(f"score segment {segment_index} must be an object")
        kind = _required_text(segment.get("kind"), f"score segment {segment_index} kind")
        if kind == "silence":
            append_silence(
                _nonnegative_int(segment.get("durationMs"), f"score segment {segment_index} durationMs"),
                reason=_required_text(segment.get("reason", "negative-space"), f"score segment {segment_index} reason"),
            )
        elif kind == "clip":
            track_id = _required_text(segment.get("track"), f"score segment {segment_index} track")
            crossfade = _nonnegative_int(segment.get("crossfadeMs", default_crossfade), f"score segment {segment_index} crossfadeMs", maximum=250)
            append_track_take(track_id, crossfade_ms=crossfade)
        elif kind == "loop":
            track_id = _required_text(segment.get("track"), f"score segment {segment_index} track")
            repeats = _positive_int(segment.get("repeats"), f"score segment {segment_index} repeats")
            if repeats > 10000:
                raise ScoreError(f"score segment {segment_index} repeats must be <= 10000")
            gap_ms = _nonnegative_int(segment.get("gapMs", 0), f"score segment {segment_index} gapMs")
            crossfade = _nonnegative_int(segment.get("crossfadeMs", default_crossfade), f"score segment {segment_index} crossfadeMs", maximum=250)
            for repeat_index in range(repeats):
                if repeat_index and gap_ms:
                    append_silence(gap_ms, reason="loop-gap")
                    append_track_take(track_id, crossfade_ms=0)
                else:
                    append_track_take(track_id, crossfade_ms=crossfade if repeat_index else 0)
        elif kind == "speech":
            text = _required_text(segment.get("text"), f"score segment {segment_index} text")
            duration_ms = _positive_int(segment.get("durationMs"), f"score segment {segment_index} durationMs")
            forge = _required_text(segment.get("forge", "pocket-tts"), f"score segment {segment_index} forge")
            crossfade = _nonnegative_int(segment.get("crossfadeMs", 0), f"score segment {segment_index} crossfadeMs", maximum=250)
            applied_crossfade = 0
            if events and events[-1]["kind"] in {"clip", "speech"} and crossfade:
                applied_crossfade = min(crossfade, duration_ms // 2)
                cursor = max(0, cursor - applied_crossfade)
            events.append({
                "kind": "speech",
                "id": _required_text(segment.get("id", f"speech-{segment_index + 1}"), f"score segment {segment_index} id"),
                "forge": forge,
                "text": text,
                "startMs": cursor,
                "durationMs": duration_ms,
                "crossfadeInMs": applied_crossfade,
                "rendered": False,
                "played": False,
            })
            cursor += duration_ms
        else:
            raise ScoreError(f"unsupported score segment kind {kind!r}")

    clip_count = sum(event["kind"] == "clip" for event in events)
    speech_count = sum(event["kind"] == "speech" for event in events)
    silence_count = sum(event["kind"] == "silence" for event in events)
    return {
        "schema": "fortress.loopscore.plan.v1",
        "scoreId": score_id,
        "scoreSha256": _canonical_hash(raw),
        "mode": raw.get("mode", "unspecified"),
        "seed": seed,
        "events": events,
        "summary": {
            "durationMs": cursor,
            "clipEvents": clip_count,
            "speechEvents": speech_count,
            "silenceEvents": silence_count,
            "pocketTtsInvoked": False,
            "audioPlayed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile a deterministic LoopScore manifest into a non-playing audio timeline."
    )
    parser.add_argument("score", help="Path to a fortress.loopscore.v1 JSON score")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the compiled plan")
    args = parser.parse_args()

    path = Path(args.score)
    raw = json.loads(path.read_text(encoding="utf-8"))
    plan = compile_score(raw)
    print(json.dumps(plan, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=args.pretty))


if __name__ == "__main__":
    main()
