#!/usr/bin/env python3
"""Late repository-snapshot revalidation for TRY FOREVER provenance reports.

This pure policy narrows the custody window between direct skill certification
and report emission. It may preserve prior authority but may never manufacture
it from a matching HEAD string. It is intentionally weaker than atomic repository
binding: equal observations do not prove away swap-and-restore, filesystem
identity reuse, or mutation after the final observation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportEmissionSnapshotVerdict:
    status: str
    reason: str
    prior_authoritative: bool
    certified_head: str
    final_head: str
    final_dirty: bool | None


def revalidate_report_emission_snapshot(
    *,
    prior_authoritative: bool,
    certified_head: str,
    final_head: str,
    final_dirty: bool | None,
) -> ReportEmissionSnapshotVerdict:
    """Require prior authority and the same certified clean HEAD at emission.

    Late revalidation is preservation-only. A caller must mechanically supply the
    earlier certification result; a non-empty `certified_head` by itself cannot
    turn an earlier unstable/mismatched snapshot into authority. Only literal
    boolean True is authority-bearing; arbitrary truthy values fail closed.
    """

    if prior_authoritative is not True:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="prior repository snapshot was not explicitly authoritative; late revalidation cannot manufacture authority",
            prior_authoritative=False,
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=final_dirty,
        )
    if not certified_head:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="no certified repository HEAD exists to revalidate at report emission",
            prior_authoritative=True,
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=final_dirty,
        )
    if not final_head:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="repository HEAD is unavailable at report emission",
            prior_authoritative=True,
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=final_dirty,
        )
    if final_head != certified_head:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="repository HEAD changed after skill certification and before report emission",
            prior_authoritative=True,
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=final_dirty,
        )
    if final_dirty is None:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="repository cleanliness is unavailable at report emission",
            prior_authoritative=True,
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=None,
        )
    if final_dirty:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="repository became dirty after skill certification and before report emission",
            prior_authoritative=True,
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=True,
        )
    return ReportEmissionSnapshotVerdict(
        status="STABLE_CLEAN",
        reason="prior repository authority remains bound to the same clean HEAD at report emission",
        prior_authoritative=True,
        certified_head=certified_head,
        final_head=final_head,
        final_dirty=False,
    )
