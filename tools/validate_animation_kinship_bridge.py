#!/usr/bin/env python3
"""Validate a non-authoritative sibling animation key/timing bridge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "ascii-kinesis-kinship-bridge.v1"


def fail(message: str) -> None:
    raise SystemExit(f"ANIMATION_KINSHIP_BRIDGE_FAIL: {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bridge", type=Path)
    args = parser.parse_args()

    try:
        payload = json.loads(args.bridge.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot read JSON: {exc}")

    if payload.get("schema") != SCHEMA:
        fail(f"expected schema {SCHEMA!r}")

    if not payload.get("source_system"):
        fail("source_system missing")
    if not payload.get("source_specimen_id"):
        fail("source_specimen_id missing")

    timing = payload.get("timing")
    if not isinstance(timing, dict):
        fail("timing object missing")
    if timing.get("authority") != "SOURCE_KEY_LEDGER":
        fail("timing.authority must remain SOURCE_KEY_LEDGER")

    keys = payload.get("keys")
    if not isinstance(keys, list) or not keys:
        fail("keys must be a non-empty list")

    seen = set()
    previous_frame = -1
    previous_time = -1.0
    for index, key in enumerate(keys):
        if not isinstance(key, dict):
            fail(f"keys[{index}] must be an object")
        key_id = key.get("key_id")
        if not key_id or key_id in seen:
            fail(f"invalid/duplicate key_id at index {index}: {key_id!r}")
        seen.add(key_id)

        frame = key.get("source_frame")
        time_s = key.get("source_time_seconds")
        if not isinstance(frame, int) or frame <= previous_frame:
            fail(f"source_frame must strictly increase at {key_id}")
        if not isinstance(time_s, (int, float)) or float(time_s) < previous_time:
            fail(f"source_time_seconds must be monotonic at {key_id}")
        previous_frame = frame
        previous_time = float(time_s)

        for field in ("hold_frames", "hold_seconds", "timing_provenance"):
            if key.get(field) is None:
                fail(f"{key_id} missing {field}")

    forbidden = {"uapl", "uat", "ascii_geometry", "motion_dungeon"}
    if forbidden.intersection(payload):
        fail("bridge contains an authoritative ASCII payload field")

    print(
        json.dumps(
            {
                "schema": "animation-kinship-validation.v1",
                "status": "PASS",
                "bridge_schema": SCHEMA,
                "source_system": payload["source_system"],
                "source_specimen_id": payload["source_specimen_id"],
                "key_count": len(keys),
                "authority": "DIAGNOSTIC_INPUT_ONLY",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
