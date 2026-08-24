#!/usr/bin/env python3
"""Hostile source fixture for bounded descriptor-shadow operator capability closure.

SOURCE ONLY. This regression has not been observed executing in an authorized lane.
"""

from pathlib import Path

import try_forever_owner_surgery_descriptor_shadow_operator_receipt as owner


ROOT = Path("/evidence/repo")


def main() -> int:
    original_audit = owner.audit_descriptor_shadow
    original_projection = owner.project_shadow_receipt_with_self_integrity

    def fake_audit(**kwargs):
        assert kwargs["root"] == ROOT / owner.PATCH_ROOT
        return {"schema": "raw-test-evidence", "status": "TEST"}

    def clean_projection(repo_root, raw):
        assert repo_root == ROOT
        assert raw["status"] == "TEST"
        return {
            "schema": "bounded-test-receipt",
            "authorityAdmitted": False,
            "ownerMutation": False,
            "regressionExecuted": False,
            "tested": False,
            "runtimeUi": False,
            "runtimeTalkBack": False,
            "phoneDelivered": False,
        }

    try:
        owner.audit_descriptor_shadow = fake_audit
        owner.project_shadow_receipt_with_self_integrity = clean_projection

        receipt = owner.build_descriptor_shadow_operator_receipt(ROOT)
        assert receipt["operatorReceiptSchema"] == owner.SCHEMA
        assert len(receipt["operatorReceiptSha256"]) == 64
        for field in owner.FINAL_DENIED_CAPABILITY_FIELDS:
            assert field in receipt
            assert receipt[field] is False

        # The operator envelope may close an absent later capability to explicit false, but it may
        # never sanitize a contradictory upstream claim merely because the final projector is
        # conservative.
        for field in owner.FINAL_DENIED_CAPABILITY_FIELDS:
            def poisoned_projection(repo_root, raw, field=field):
                receipt = clean_projection(repo_root, raw)
                receipt[field] = True
                return receipt

            owner.project_shadow_receipt_with_self_integrity = poisoned_projection
            try:
                owner.build_descriptor_shadow_operator_receipt(ROOT)
            except ValueError as exc:
                assert field in str(exc)
                assert "cannot sanitize upstream" in str(exc)
            else:
                raise AssertionError(f"operator receipt sanitized upstream {field}=true")

        # Exact false upstream is compatible with explicit final closure.
        def explicit_false_projection(repo_root, raw):
            receipt = clean_projection(repo_root, raw)
            for field in owner.FINAL_DENIED_CAPABILITY_FIELDS:
                receipt[field] = False
            return receipt

        owner.project_shadow_receipt_with_self_integrity = explicit_false_projection
        receipt = owner.build_descriptor_shadow_operator_receipt(ROOT)
        for field in owner.FINAL_DENIED_CAPABILITY_FIELDS:
            assert receipt[field] is False
    finally:
        owner.audit_descriptor_shadow = original_audit
        owner.project_shadow_receipt_with_self_integrity = original_projection

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
