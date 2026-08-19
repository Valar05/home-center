#!/usr/bin/env python3
"""Regression source for final provenance-emission composition.

These fixtures pin preservation-only repository authority and generated-index
currentness. They are source until an authorized runner executes them.
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_provenance_emission_composition import compose_provenance_emission
from try_forever_repository_emission_observation import RepositoryEmissionObservation

SHA_A = "a" * 64
SHA_B = "b" * 64
HEAD = "1" * 40


def observed(*, head: str = HEAD, dirty: bool = False) -> RepositoryEmissionObservation:
    return RepositoryEmissionObservation(
        status="OBSERVED",
        reason="fixture",
        head=head,
        dirty=dirty,
    )


def unavailable() -> RepositoryEmissionObservation:
    return RepositoryEmissionObservation(
        status="UNAVAILABLE",
        reason="fixture unavailable",
        head="stale-head-must-not-be-reused",
        dirty=False,
    )


def compose(**overrides):
    values = dict(
        prior_repository_authoritative=True,
        certified_head=HEAD,
        final_repository_observation=observed(),
        prior_generated_index_status="VERIFIED_CURRENT",
        prior_generated_index_reason="fixture current",
        inspected_generated_index_sha256=SHA_A,
        emission_generated_index_sha256=SHA_A,
        emission_generated_index_readable=True,
    )
    values.update(overrides)
    return compose_provenance_emission(**values)


def test_stable_repository_and_exact_artifact_preserve_authority_and_currentness():
    result = compose()

    assert result.repository_status == "STABLE_CLEAN"
    assert result.repository_authoritative is True
    assert result.generated_index_artifact_status == "STABLE"
    assert result.generated_index_status == "VERIFIED_CURRENT"
    assert result.generated_index_currentness_withheld is False


def test_matching_late_head_cannot_manufacture_missing_prior_authority():
    result = compose(prior_repository_authoritative=False)

    assert result.repository_status == "UNSTABLE"
    assert result.repository_authoritative is False
    assert result.generated_index_status == "UNRESOLVED"
    assert result.generated_index_currentness_withheld is True


def test_unavailable_late_observation_does_not_reuse_embedded_stale_head_fields():
    result = compose(final_repository_observation=unavailable())

    assert result.repository_status == "UNSTABLE"
    assert result.repository_authoritative is False
    assert result.generated_index_status == "UNRESOLVED"
    assert "late report-emission repository custody failed" in result.generated_index_reason


def test_changed_external_artifact_withholds_currentness_even_when_repository_is_stable():
    result = compose(emission_generated_index_sha256=SHA_B)

    assert result.repository_status == "STABLE_CLEAN"
    assert result.repository_authoritative is True
    assert result.generated_index_artifact_status == "CHANGED"
    assert result.generated_index_status == "UNRESOLVED"
    assert result.generated_index_currentness_withheld is True


def test_declared_negative_index_diagnostic_is_never_promoted_by_green_late_gates():
    result = compose(
        prior_generated_index_status="STALE",
        prior_generated_index_reason="fixture stale",
    )

    assert result.repository_status == "STABLE_CLEAN"
    assert result.generated_index_status == "STALE"
    assert result.generated_index_reason == "fixture stale"
    assert result.generated_index_currentness_withheld is False


def test_unknown_prior_index_status_fails_closed_even_with_green_late_gates():
    result = compose(prior_generated_index_status="CURRENTISH")

    assert result.generated_index_status == "UNRESOLVED"
    assert "outside the declared evidence contract" in result.generated_index_reason
