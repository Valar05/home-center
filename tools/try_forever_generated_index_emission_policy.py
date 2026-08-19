#!/usr/bin/env python3
"""Final-emission custody policy for TRY FOREVER generated-index evidence.

A generated index may be verified against a certified clean repository snapshot,
but repository custody is not custody of a separately mutable generated-index
artifact. Positive currentness therefore survives emission only when both the
repository gate and an exact artifact-content revalidation remain stable.

This module is pure policy. It owns no repository I/O, renderer, scheduler,
phone surface, or P0 recovery lane, and it does not claim atomic cross-artifact
binding.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedIndexArtifactCustodyVerdict:
    status: str
    reason: str
    inspected_sha256: str
    emission_sha256: str


@dataclass(frozen=True)
class GeneratedIndexEmissionVerdict:
    status: str
    reason: str
    currentness_withheld: bool


def _is_canonical_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def assess_generated_index_artifact_custody(
    *,
    inspected_sha256: str,
    emission_sha256: str,
    emission_readable: bool = True,
) -> GeneratedIndexArtifactCustodyVerdict:
    """Compare the exact generated-index content identity across emission.

    This is a deterministic content-custody check, not atomic filesystem binding.
    The caller must derive both digests from complete bounded reads of the exact
    artifact. Missing/non-canonical evidence fails closed rather than inventing a
    stable identity.
    """

    if not _is_canonical_sha256(inspected_sha256):
        return GeneratedIndexArtifactCustodyVerdict(
            status="UNRESOLVED",
            reason="generated-index inspection did not bind a canonical whole-artifact SHA-256",
            inspected_sha256="",
            emission_sha256="",
        )
    if not emission_readable:
        return GeneratedIndexArtifactCustodyVerdict(
            status="UNRESOLVED",
            reason="generated-index artifact could not be re-read at report emission",
            inspected_sha256=inspected_sha256,
            emission_sha256="",
        )
    if not _is_canonical_sha256(emission_sha256):
        return GeneratedIndexArtifactCustodyVerdict(
            status="UNRESOLVED",
            reason="generated-index emission revalidation did not produce a canonical whole-artifact SHA-256",
            inspected_sha256=inspected_sha256,
            emission_sha256="",
        )
    if inspected_sha256 != emission_sha256:
        return GeneratedIndexArtifactCustodyVerdict(
            status="CHANGED",
            reason="generated-index content changed after the artifact that earned the prior verdict was inspected",
            inspected_sha256=inspected_sha256,
            emission_sha256=emission_sha256,
        )
    return GeneratedIndexArtifactCustodyVerdict(
        status="STABLE",
        reason="the exact generated-index content digest remained stable through emission revalidation",
        inspected_sha256=inspected_sha256,
        emission_sha256=emission_sha256,
    )


def project_generated_index_at_emission(
    *,
    prior_status: str,
    prior_reason: str,
    emission_status: str,
    artifact_custody_status: str,
) -> GeneratedIndexEmissionVerdict:
    """Project prior index evidence through repository and artifact custody gates.

    A prior VERIFIED_CURRENT claim survives only when the final repository gate is
    STABLE_CLEAN *and* the exact generated-index artifact has a STABLE content
    custody verdict. Negative or already-unresolved diagnostics remain diagnostic
    and are never promoted.
    """

    if prior_status != "VERIFIED_CURRENT":
        return GeneratedIndexEmissionVerdict(
            status=prior_status,
            reason=prior_reason,
            currentness_withheld=False,
        )

    if emission_status != "STABLE_CLEAN":
        return GeneratedIndexEmissionVerdict(
            status="UNRESOLVED",
            reason=(
                "late report-emission repository custody failed; earlier "
                "generated-index currentness is withheld"
            ),
            currentness_withheld=True,
        )

    if artifact_custody_status != "STABLE":
        return GeneratedIndexEmissionVerdict(
            status="UNRESOLVED",
            reason=(
                "generated-index artifact custody was not stable through report emission; "
                "earlier currentness is withheld"
            ),
            currentness_withheld=True,
        )

    return GeneratedIndexEmissionVerdict(
        status=prior_status,
        reason=prior_reason,
        currentness_withheld=False,
    )
