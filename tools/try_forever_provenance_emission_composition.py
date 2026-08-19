#!/usr/bin/env python3
"""Pure final-emission composition for TRY FOREVER provenance evidence.

This helper composes existing repository-emission and generated-index custody
policies. It owns no Git/filesystem I/O, repository traversal, serializer,
renderer, scheduler, phone surface, or P0 recovery lane. The sole provenance
owner remains ``tools/try_forever_skill_provenance_probe.py``.

The goal is to make owner integration small and mechanically reviewable: one
late repository observation plus one exact generated-index artifact observation
feed already-existing preservation-only policies. Supporting source is not owner
wiring, testing, runtime proof, deployment, or delivery.
"""

from __future__ import annotations

from dataclasses import dataclass

from try_forever_generated_index_emission_policy import (
    assess_generated_index_artifact_custody,
    project_generated_index_at_emission,
)
from try_forever_report_emission_snapshot import revalidate_report_emission_snapshot
from try_forever_repository_emission_observation import RepositoryEmissionObservation


@dataclass(frozen=True)
class ProvenanceEmissionComposition:
    repository_status: str
    repository_reason: str
    repository_authoritative: bool
    generated_index_status: str
    generated_index_reason: str
    generated_index_currentness_withheld: bool
    generated_index_artifact_status: str
    generated_index_artifact_reason: str


def compose_provenance_emission(
    *,
    prior_repository_authoritative: bool,
    certified_head: str,
    final_repository_observation: RepositoryEmissionObservation,
    prior_generated_index_status: str,
    prior_generated_index_reason: str,
    inspected_generated_index_sha256: str,
    emission_generated_index_sha256: str,
    emission_generated_index_readable: bool = True,
) -> ProvenanceEmissionComposition:
    """Compose final repository + generated-index custody without manufacturing authority.

    Repository authority is preservation-only: the earlier certification must be
    literal ``True`` and the late one-process repository observation must still be
    the same clean certified HEAD. An unavailable/malformed late observation is
    projected as unavailable evidence rather than reusing stale earlier values.

    Generated-index currentness is independently preservation-only. A prior
    ``VERIFIED_CURRENT`` may survive only when final repository custody is
    ``STABLE_CLEAN`` and the exact complete artifact SHA-256 remains stable.
    Existing negative diagnostics remain negative diagnostics.
    """

    if final_repository_observation.status == "OBSERVED":
        final_head = final_repository_observation.head
        final_dirty = final_repository_observation.dirty
    else:
        final_head = ""
        final_dirty = None

    repository = revalidate_report_emission_snapshot(
        prior_authoritative=prior_repository_authoritative,
        certified_head=certified_head,
        final_head=final_head,
        final_dirty=final_dirty,
    )

    artifact = assess_generated_index_artifact_custody(
        inspected_sha256=inspected_generated_index_sha256,
        emission_sha256=emission_generated_index_sha256,
        emission_readable=emission_generated_index_readable,
    )

    generated_index = project_generated_index_at_emission(
        prior_status=prior_generated_index_status,
        prior_reason=prior_generated_index_reason,
        emission_status=repository.status,
        artifact_custody_status=artifact.status,
    )

    repository_authoritative = (
        prior_repository_authoritative is True
        and repository.status == "STABLE_CLEAN"
    )

    return ProvenanceEmissionComposition(
        repository_status=repository.status,
        repository_reason=repository.reason,
        repository_authoritative=repository_authoritative,
        generated_index_status=generated_index.status,
        generated_index_reason=generated_index.reason,
        generated_index_currentness_withheld=generated_index.currentness_withheld,
        generated_index_artifact_status=artifact.status,
        generated_index_artifact_reason=artifact.reason,
    )
