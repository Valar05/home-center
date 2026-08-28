#!/usr/bin/env python3
"""Regression source for descriptor-shadow receipt comparison semantics.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.

The receipt must distinguish a completed comparison that disagrees from a comparison that never
completed. ``False`` is evidence of divergence; ``None`` is evidence that the comparison is
unavailable. Wound/unavailable states must not masquerade as completed negative comparisons.
"""

from pathlib import Path

from try_forever_owner_surgery_shadow_receipt_projection import project_shadow_receipt


ROOT = Path(".")
SHA = "a" * 64


def base(status: str) -> dict[str, object]:
    return {
        "schema": "try-forever-owner-surgery-descriptor-shadow.v3",
        "status": status,
        "canonicalResultSha256": SHA,
        "boundary": f"{status} boundary",
        "portableShadowArtifacts": [],
        "descriptorArtifacts": [],
        "artifactSetMatch": None,
        "metricsMatch": None,
        "contentIdentityMatch": None,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
    }


def expect_rejected(payload: dict[str, object], needle: str) -> None:
    try:
        project_shadow_receipt(ROOT, payload)
    except ValueError as exc:
        assert needle in str(exc), str(exc)
    else:
        raise AssertionError(f"payload unexpectedly admitted: {payload!r}")


def main() -> int:
    matched = base("SHADOW_MATCH")
    matched.update(
        artifactSetMatch=True,
        metricsMatch=True,
        contentIdentityMatch=True,
    )
    assert project_shadow_receipt(ROOT, matched)["status"] == "SHADOW_MATCH"

    diverged = base("SHADOW_DIVERGED")
    diverged.update(
        artifactSetMatch=True,
        metricsMatch=False,
        contentIdentityMatch=True,
    )
    projected = project_shadow_receipt(ROOT, diverged)
    assert projected["metricsMatch"] is False

    incomplete_divergence = base("SHADOW_DIVERGED")
    incomplete_divergence.update(
        artifactSetMatch=True,
        metricsMatch=True,
        contentIdentityMatch=None,
    )
    expect_rejected(incomplete_divergence, "null means comparison unavailable")

    false_match = base("SHADOW_MATCH")
    false_match.update(
        artifactSetMatch=True,
        metricsMatch=False,
        contentIdentityMatch=True,
    )
    expect_rejected(false_match, "all three exact comparison booleans true")

    descriptor_wound = base("DESCRIPTOR_WOUND")
    assert project_shadow_receipt(ROOT, descriptor_wound)["artifactSetMatch"] is None

    legacy_descriptor_wound = base("DESCRIPTOR_WOUND")
    legacy_descriptor_wound.update(
        artifactSetMatch=False,
        metricsMatch=False,
        contentIdentityMatch=False,
    )
    expect_rejected(legacy_descriptor_wound, "comparison was not completed")

    for status in (
        "CANONICAL_SCHEMA_WOUND",
        "CANONICAL_WOUND",
        "PORTABLE_SHADOW_WOUND",
        "DESCRIPTOR_UNAVAILABLE",
        "CAPABILITY_WOUND",
    ):
        projected = project_shadow_receipt(ROOT, base(status))
        assert projected["artifactSetMatch"] is None
        assert projected["metricsMatch"] is None
        assert projected["contentIdentityMatch"] is None

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
