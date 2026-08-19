#!/usr/bin/env python3
"""Regression source for generated-index authority at final report emission."""

from try_forever_generated_index_emission_policy import (
    project_generated_index_at_emission,
)


def test_verified_current_survives_stable_final_custody():
    verdict = project_generated_index_at_emission(
        prior_status="VERIFIED_CURRENT",
        prior_reason="all prior checks matched",
        emission_status="STABLE_CLEAN",
    )
    assert verdict.status == "VERIFIED_CURRENT"
    assert verdict.reason == "all prior checks matched"
    assert verdict.currentness_withheld is False


def test_verified_current_is_withheld_when_final_head_or_cleanliness_is_unstable():
    verdict = project_generated_index_at_emission(
        prior_status="VERIFIED_CURRENT",
        prior_reason="all prior checks matched",
        emission_status="UNSTABLE",
    )
    assert verdict.status == "UNRESOLVED"
    assert verdict.currentness_withheld is True
    assert "currentness is withheld" in verdict.reason


def test_negative_diagnostics_survive_without_becoming_authority():
    stale = project_generated_index_at_emission(
        prior_status="STALE",
        prior_reason="source head mismatch",
        emission_status="UNSTABLE",
    )
    unresolved = project_generated_index_at_emission(
        prior_status="UNRESOLVED",
        prior_reason="timestamp unavailable",
        emission_status="UNSTABLE",
    )
    assert (stale.status, stale.reason, stale.currentness_withheld) == (
        "STALE",
        "source head mismatch",
        False,
    )
    assert (unresolved.status, unresolved.reason, unresolved.currentness_withheld) == (
        "UNRESOLVED",
        "timestamp unavailable",
        False,
    )


def test_failed_final_custody_never_relabels_stale_as_verified():
    verdict = project_generated_index_at_emission(
        prior_status="STALE",
        prior_reason="too old",
        emission_status="UNSTABLE",
    )
    assert verdict.status != "VERIFIED_CURRENT"
