#!/usr/bin/env python3
"""Regression canaries for consolidated animation-direction doctrine.

This test is structural. It prevents old universal ASCII-first, automatic video-timing,
shovel-lineage, and floating-load-chain mistakes from silently re-entering the active
contracts. It does not claim artistic acceptance.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    p = ROOT / path
    if not p.is_file():
        raise AssertionError(f"missing contract: {path}")
    return p.read_text(encoding="utf-8")


def require(haystack: str, needle: str, where: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"{where}: required canary missing: {needle!r}")


def forbid(haystack: str, needle: str, where: str) -> None:
    if needle in haystack:
        raise AssertionError(f"{where}: superseded doctrine returned: {needle!r}")


core = text("skills/motion-direction/SKILL.md")
ascii_skill = text("skills/ascii-kinesis/SKILL.md")
uapl = text("docs/UAPL_ASCII_POSE_LANGUAGE.md")
spa = text("docs/UAPL_MOTION_SPA.md")
bridge = text("docs/ANIMATION_KINSHIP_BRIDGE.md")
swarm = text("docs/ASCII_KINESIS_SWARM_CONTRACT_V2.md")

# Core source-role / animation-judgment laws.
require(core, "DREW GIVES POSES -> WORKER DIRECTS ANIMATION", "motion-direction")
require(core, "POSE_REFERENCE", "motion-direction")
require(core, "CONTACT_REFERENCE", "motion-direction")
require(core, "TIMING_REFERENCE", "motion-direction")
require(core, "Pose master and direction profile are separate artifacts", "motion-direction")
require(core, "ASCII is a tool, not a religion", "motion-direction")
require(core, "screen-edge/root implication -> upper arm -> elbow -> forearm -> wrist -> hand -> contact", "motion-direction")
require(core, "RECENT CONTEXT != PROP AUTHORITY", "motion-direction")
require(core, "Quarantine is transitive", "motion-direction")

for failure in (
    "VIDEO_TIMING_LEAK",
    "GAME_STYLE_REPAINT_ONLY",
    "LOAD_CHAIN_ERASED",
    "STALE_PROP_CARRYOVER",
    "QUARANTINED_VISUAL_LEAK",
    "PROP_IDENTITY_DRIFT",
    "PLACEHOLDER_STYLE_SUBSTITUTION",
    "ASCII_FORCED_WITHOUT_BENEFIT",
):
    require(core, failure, "motion-direction")

# ASCII/UAPL must now be explicit specializations, not universal intake doctrine.
require(ascii_skill, "not** the general animation doctrine", "ascii-kinesis")
require(ascii_skill, "skills/motion-direction/SKILL.md", "ascii-kinesis")
require(uapl, "not** a universal animation intake requirement", "UAPL")
require(uapl, "POSE_REFERENCE", "UAPL")
require(swarm, "This file owns **campaign/swarm mechanics only**", "swarm")
require(swarm, "POSE_REFERENCE + CONTACT_REFERENCE", "swarm")

# Timestamps may address pose evidence without silently becoming timing authority.
require(bridge, "A timestamp is not timing authority", "kinship bridge")
require(bridge, "POSE_ADDRESS", "kinship bridge")
require(bridge, "timing_authority", "kinship bridge")

# Generic animation delivery must be lineage-neutral. The old shovel shell inheritance is banned.
require(spa, "Generic offline/mobile shell", "UAPL Motion SPA")
require(spa, "zero visual-art inheritance", "UAPL Motion SPA")
forbid(spa, "## Shovel-derived shell", "UAPL Motion SPA")
forbid(spa, "accepted shovel SPA pattern", "UAPL Motion SPA")

# Exact old universal Apprentice sentence must not be reintroduced into active Home Center contracts.
for name, body in {
    "ascii-kinesis": ascii_skill,
    "UAPL": uapl,
    "swarm": swarm,
    "kinship": bridge,
    "spa": spa,
}.items():
    forbid(body, "Animation is understood in ASCII first.", name)

print("MOTION_DIRECTION_CONTRACT_PASS")
