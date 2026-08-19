#!/usr/bin/env python3
"""Late repository-snapshot revalidation for TRY FOREVER provenance reports.

This pure policy narrows the custody window between direct skill certification
and report emission.  It is intentionally weaker than atomic repository
binding: equal observations do not prove away swap-and-restore, filesystem
identity reuse, or mutation after the final observation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportEmissionSnapshotVerdict:
    status: str
    reason: str
    certified_head: str
    final_head: str
    final_dirty: bool | None


def revalidate_report_emission_snapshot(
    *,
    certified_head: str,
    final_head: str,
    final_dirty: bool | None,
) -> ReportEmissionSnapshotVerdict:
    """Require the certified clean HEAD to still be observed at report emission."""

    if not certified_head:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="no certified repository HEAD exists to revalidate at report emission",
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=final_dirty,
        )
    if not final_head:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="repository HEAD is unavailable at report emission",
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=final_dirty,
        )
    if final_head != certified_head:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="repository HEAD changed after skill certification and before report emission",
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=final_dirty,
        )
    if final_dirty is None:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="repository cleanliness is unavailable at report emission",
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=None,
        )
    if final_dirty:
        return ReportEmissionSnapshotVerdict(
            status="UNSTABLE",
            reason="repository became dirty after skill certification and before report emission",
            certified_head=certified_head,
            final_head=final_head,
            final_dirty=True,
        )
    return ReportEmissionSnapshotVerdict(
        status="STABLE_CLEAN",
        reason="the certified clean HEAD is still observed immediately before report emission",
        certified_head=certified_head,
        final_head=final_head,
        final_dirty=False,
    )
