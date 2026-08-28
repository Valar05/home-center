#!/usr/bin/env python3
"""Hostile source fixture for descriptor-shadow operator receipt root custody.

SOURCE ONLY. This file has not been observed executing in an authorized regression lane.

The operator receipt's ``repo_root`` is both a machine-evidence custody input and the bounded display
projection root. Raw audit from one root must never be projected as though it came from another.
"""

from pathlib import Path

import try_forever_owner_surgery_descriptor_shadow_operator_receipt as owner


ROOT = Path("/evidence/repo")


def main() -> int:
    original_audit = owner.audit_descriptor_shadow
    original_projection = owner.project_shadow_receipt_with_self_integrity
    captured: list[dict[str, object]] = []

    def fake_audit(**kwargs):
        captured.append(dict(kwargs))
        return {"raw": "machine-evidence"}

    def fake_projection(repo_root, raw):
        assert repo_root == ROOT
        assert raw == {"raw": "machine-evidence"}
        return {
            "schema": "bounded-test-receipt",
            "authorityAdmitted": False,
            "tested": False,
        }

    try:
        owner.audit_descriptor_shadow = fake_audit
        owner.project_shadow_receipt_with_self_integrity = fake_projection

        receipt = owner.build_descriptor_shadow_operator_receipt(
            ROOT,
            max_candidates=17,
            max_entries=23,
        )
        assert len(captured) == 1
        assert captured[0]["root"] == ROOT / owner.PATCH_ROOT
        assert captured[0]["max_candidates"] == 17
        assert captured[0]["max_entries"] == 23
        assert receipt["authorityAdmitted"] is False
        assert receipt["tested"] is False

        # The raw audit root is owned by repo_root. A caller cannot audit one tree while projecting
        # the receipt under another repository root.
        captured.clear()
        try:
            owner.build_descriptor_shadow_operator_receipt(
                ROOT,
                root=Path("/different/repository/patches"),
            )
        except ValueError as exc:
            assert "root is owned by repo_root" in str(exc)
        else:
            raise AssertionError("operator receipt allowed audit-root/display-root evidence split")
        assert captured == []
    finally:
        owner.audit_descriptor_shadow = original_audit
        owner.project_shadow_receipt_with_self_integrity = original_projection

    return 0


if __name__ == "__main__":
    raise SystemExit(main())