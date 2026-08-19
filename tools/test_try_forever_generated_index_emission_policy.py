#!/usr/bin/env python3
"""Regression source for generated-index authority at final report emission."""

import hashlib

from try_forever_generated_index_emission_policy import (
    assess_generated_index_artifact_custody,
    project_generated_index_at_emission,
)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_verified_current_survives_stable_repository_and_artifact_custody():
    stable = assess_generated_index_artifact_custody(
        inspected_sha256=digest(b"content-a"),
        emission_sha256=digest(b"content-a"),
    )
    verdict = project_generated_index_at_emission(
        prior_status="VERIFIED_CURRENT",
        prior_reason="all prior checks matched",
        emission_status="STABLE_CLEAN",
        artifact_custody_status=stable.status,
    )
    assert stable.status == "STABLE"
    assert verdict.status == "VERIFIED_CURRENT"
    assert verdict.reason == "all prior checks matched"
    assert verdict.currentness_withheld is False


def test_verified_current_is_withheld_when_final_repository_custody_is_unstable():
    verdict = project_generated_index_at_emission(
        prior_status="VERIFIED_CURRENT",
        prior_reason="all prior checks matched",
        emission_status="UNSTABLE",
        artifact_custody_status="STABLE",
    )
    assert verdict.status == "UNRESOLVED"
    assert verdict.currentness_withheld is True
    assert "repository custody failed" in verdict.reason


def test_external_generated_index_mutation_after_inspection_must_withhold_currentness():
    custody = assess_generated_index_artifact_custody(
        inspected_sha256=digest(b"external-index-content-a"),
        emission_sha256=digest(b"external-index-content-b"),
    )
    verdict = project_generated_index_at_emission(
        prior_status="VERIFIED_CURRENT",
        prior_reason="content A matched clean HEAD H",
        emission_status="STABLE_CLEAN",
        artifact_custody_status=custody.status,
    )
    assert custody.status == "CHANGED"
    assert verdict.status == "UNRESOLVED"
    assert verdict.currentness_withheld is True
    assert "artifact custody was not stable" in verdict.reason


def test_missing_external_artifact_revalidation_must_withhold_currentness():
    custody = assess_generated_index_artifact_custody(
        inspected_sha256=digest(b"external-index-content-a"),
        emission_sha256="",
        emission_readable=False,
    )
    verdict = project_generated_index_at_emission(
        prior_status="VERIFIED_CURRENT",
        prior_reason="content A matched clean HEAD H",
        emission_status="STABLE_CLEAN",
        artifact_custody_status=custody.status,
    )
    assert custody.status == "UNRESOLVED"
    assert verdict.status == "UNRESOLVED"
    assert verdict.currentness_withheld is True


def test_noncanonical_digest_cannot_be_used_as_artifact_identity():
    custody = assess_generated_index_artifact_custody(
        inspected_sha256="ABC",
        emission_sha256="ABC",
    )
    assert custody.status == "UNRESOLVED"
    assert custody.inspected_sha256 == ""
    assert custody.emission_sha256 == ""


def test_negative_diagnostics_survive_without_becoming_authority():
    stale = project_generated_index_at_emission(
        prior_status="STALE",
        prior_reason="source head mismatch",
        emission_status="UNSTABLE",
        artifact_custody_status="CHANGED",
    )
    unresolved = project_generated_index_at_emission(
        prior_status="UNRESOLVED",
        prior_reason="timestamp unavailable",
        emission_status="STABLE_CLEAN",
        artifact_custody_status="UNRESOLVED",
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


def test_failed_gates_never_relabel_stale_as_verified():
    verdict = project_generated_index_at_emission(
        prior_status="STALE",
        prior_reason="too old",
        emission_status="UNSTABLE",
        artifact_custody_status="CHANGED",
    )
    assert verdict.status != "VERIFIED_CURRENT"
