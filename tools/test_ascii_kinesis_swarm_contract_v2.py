#!/usr/bin/env python3
"""Deterministic contract check for restarted ASCII Kinesis V2 swarm entries.

Historical v1 specimens are intentionally ignored. New directories matching
`v2-*` must expose the commissioned three-tab SPA and the source-first media
contract. This test is structural; it does not claim artistic acceptance.

General source-role and timing-authority law lives in skills/motion-direction.
Legacy OBSERVED/INFERRED provenance remains readable; explicit derived direction
labels are also valid and do not claim source-authentic timing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = ROOT / "experiments" / "ascii-kinesis"

ALLOWED_TIMING_PROVENANCE = {
    "OBSERVED",
    "INFERRED",
    "DERIVED_UAT_OPINION",
    "DERIVED_ONES_TWOS_FOURS",
    "DERIVED_GAMEPLAY_RETIMER",
    "DERIVED_GAME_STYLE_PROFILE",
}


def fail(message: str) -> None:
    raise SystemExit(f"ASCII_KINESIS_V2_CONTRACT_FAIL: {message}")


def check_entry(entry: Path) -> None:
    manifest_path = entry / "manifest.json"
    if not manifest_path.is_file():
        fail(f"{entry.name}: missing manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if int(manifest.get("format_version", 0)) < 2:
        fail(f"{entry.name}: format_version must be >= 2")
    if manifest.get("primary_tabs") != ["ASCII", "JSON", "VIDEO"]:
        fail(f"{entry.name}: primary_tabs must be exactly ASCII, JSON, VIDEO")
    if manifest.get("ascii_literal_text") is not True:
        fail(f"{entry.name}: ascii_literal_text must be true")
    if manifest.get("video_required") is not True:
        fail(f"{entry.name}: video_required must be true")
    if manifest.get("video_source") != "abstract_ascii_rig_only":
        fail(f"{entry.name}: video_source must be abstract_ascii_rig_only")
    if manifest.get("source_art_embedded") is not False:
        fail(f"{entry.name}: source_art_embedded must be false")
    if manifest.get("backward_compatible") is not True:
        fail(f"{entry.name}: backward_compatible must be true")

    html_files = sorted(entry.glob("*.motion.html"))
    if len(html_files) != 1:
        fail(f"{entry.name}: expected exactly one tracked *.motion.html SPA")
    page = html_files[0].read_text(encoding="utf-8")

    tabs = re.findall(r'data-view=["\']([^"\']+)["\']', page)
    if tabs != ["ascii", "json", "video"]:
        fail(f"{entry.name}: SPA data-view order must be ascii,json,video; got {tabs!r}")
    if "<pre" not in page.lower():
        fail(f"{entry.name}: literal ASCII/JSON preformatted surface missing")
    lowered = page.lower().replace(" ", "")
    if "font-variant-ligatures:none" not in lowered:
        fail(f"{entry.name}: monospace ligatures are not explicitly disabled")
    if "white-space:pre" not in lowered:
        fail(f"{entry.name}: whitespace-preserving ASCII layout rule missing")
    if "<video" not in page.lower():
        fail(f"{entry.name}: VIDEO tab has no video element")
    if "data:video/" not in page.lower():
        fail(f"{entry.name}: video is not embedded for network-independent playback")

    motion_path = entry / "motion.json"
    if not motion_path.is_file():
        fail(f"{entry.name}: missing motion.json")
    motion = json.loads(motion_path.read_text(encoding="utf-8"))
    keys = motion.get("keys") or motion.get("poses") or []
    if not keys:
        fail(f"{entry.name}: no decisive keys/poses in motion.json")
    for key in keys:
        kid = key.get("key_id") or key.get("id") or key.get("name") or "<unnamed>"
        if not (key.get("timing_class") or key.get("timing")):
            fail(f"{entry.name}:{kid}: timing class missing")
        provenance = key.get("timing_provenance") or key.get("provenance")
        if provenance not in ALLOWED_TIMING_PROVENANCE:
            fail(
                f"{entry.name}:{kid}: timing provenance {provenance!r} not in "
                f"{sorted(ALLOWED_TIMING_PROVENANCE)!r}"
            )


entries = sorted(p for p in ENTRIES.glob("v2-*") if p.is_dir())
for item in entries:
    check_entry(item)

print(json.dumps({"schema": "ascii-kinesis.swarm-contract-v2-test", "entries_checked": [p.name for p in entries], "ok": True}, sort_keys=True))
