#!/usr/bin/env python3
"""Operator-facing display projection for descriptor-shadow receipts.

The descriptor shadow may carry exact repository paths and exception boundaries that are useful for
machine evidence but unsafe or noisy as direct operator/TalkBack text. This source-only projection
keeps the raw shadow result untouched and creates a bounded display receipt instead:

- exact canonical-result identity remains explicit;
- artifact paths use the existing portable provenance path projector;
- raw failure-boundary prose is not echoed; the receipt carries a deterministic digest plus a
  status-specific summary;
- no authority, TESTED, runtime, deployment, phone, or acceptance state is promoted.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path

from try_forever_provenance_report_path import project_report_path


SHADOW_SCHEMA = "try-forever-owner-surgery-descriptor-shadow.v3"
RECEIPT_SCHEMA = "try-forever-owner-surgery-descriptor-shadow-receipt.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

STATUS_SUMMARY = {
    "SHADOW_MATCH": "Descriptor and portable staging agree on compared paths, metrics, and exact content identity.",
    "SHADOW_DIVERGED": "Descriptor and portable staging disagree; stop before owner integration.",
    "CANONICAL_SCHEMA_WOUND": "Canonical custody schema is not the exact shadow-compatible v10 contract.",
    "CANONICAL_WOUND": "Canonical custody is incomplete; shadow staging is not allowed to decorate it as healthy.",
    "PORTABLE_SHADOW_WOUND": "Portable exact-content staging failed before descriptor comparison.",
    "DESCRIPTOR_UNAVAILABLE": "Descriptor primitives are unavailable; canonical portable authority remains unchanged.",
    "CAPABILITY_WOUND": "Descriptor capability evidence is not one admitted platform state.",
    "DESCRIPTOR_WOUND": "Descriptor custody failed inside the non-authoritative shadow.",
}


def _nonnegative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be one non-negative integer")
    return value


def _artifact_projection(repo_root: Path, item: object, *, field: str) -> dict[str, object]:
    if not isinstance(item, Mapping):
        raise ValueError(f"{field} entries must be mappings")
    path_text = item.get("path")
    if not isinstance(path_text, str) or not path_text:
        raise ValueError(f"{field} path must be one non-empty string")
    byte_count = _nonnegative_int(item.get("byteCount"), field=f"{field} byteCount")
    sha256 = item.get("sha256")
    if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None:
        raise ValueError(f"{field} sha256 must be 64 lowercase hexadecimal")

    projected = project_report_path(repo_root, Path(path_text))
    return {
        "path": projected.display_path,
        "pathScope": projected.scope,
        "byteCount": byte_count,
        "sha256": sha256,
    }


def project_shadow_receipt(repo_root: Path, result: Mapping[str, object]) -> dict[str, object]:
    """Create one bounded display receipt without changing the raw shadow evidence."""

    if not isinstance(result, Mapping):
        raise ValueError("shadow result must be one mapping")
    if result.get("schema") != SHADOW_SCHEMA:
        raise ValueError("shadow receipt projection requires exact descriptor-shadow v3 source")

    status = result.get("status")
    if not isinstance(status, str) or status not in STATUS_SUMMARY:
        raise ValueError("shadow status is not one admitted receipt state")

    canonical_result_sha256 = result.get("canonicalResultSha256")
    if (
        not isinstance(canonical_result_sha256, str)
        or SHA256_RE.fullmatch(canonical_result_sha256) is None
    ):
        raise ValueError("canonicalResultSha256 must be 64 lowercase hexadecimal")

    if result.get("descriptorAuthorityAdmitted") is not False:
        raise ValueError("descriptor shadow receipt must never carry descriptor authority")
    if result.get("ownerMutation") is not False:
        raise ValueError("descriptor shadow receipt must never claim owner mutation")

    portable = result.get("portableShadowArtifacts")
    descriptor = result.get("descriptorArtifacts")
    if not isinstance(portable, list) or not isinstance(descriptor, list):
        raise ValueError("shadow artifact evidence must be list-shaped")

    boundary = result.get("boundary")
    if not isinstance(boundary, str) or not boundary:
        raise ValueError("shadow boundary must be one non-empty string")
    boundary_sha256 = hashlib.sha256(
        boundary.encode("utf-8", errors="surrogatepass")
    ).hexdigest()

    return {
        "schema": RECEIPT_SCHEMA,
        "sourceSchema": SHADOW_SCHEMA,
        "status": status,
        "summary": STATUS_SUMMARY[status],
        "canonicalResultSha256": canonical_result_sha256,
        "boundarySha256": boundary_sha256,
        "portableArtifacts": [
            _artifact_projection(repo_root, item, field="portableShadowArtifacts")
            for item in portable
        ],
        "descriptorArtifacts": [
            _artifact_projection(repo_root, item, field="descriptorArtifacts")
            for item in descriptor
        ],
        "artifactSetMatch": result.get("artifactSetMatch"),
        "metricsMatch": result.get("metricsMatch"),
        "contentIdentityMatch": result.get("contentIdentityMatch"),
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
    }
