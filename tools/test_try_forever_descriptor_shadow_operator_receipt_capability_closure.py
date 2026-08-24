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

        # Core bounded-receipt capability state is not additive. Every core denial must already be
        # present as exact false before finalization; the operator command may not invent missing
        # source/test/runtime/phone evidence.
        for field in owner.CORE_DENIED_CAPABILITY_FIELDS:
            def missing_core_projection(repo_root, raw, field=field):
                value = clean_projection(repo_root, raw)
                del value[field]
                return value

            owner.project_shadow_receipt_with_self_integrity = missing_core_projection
            try:
                owner.build_descriptor_shadow_operator_receipt(ROOT)
            except ValueError as exc:
                assert field in str(exc)
                assert "must carry explicit upstream" in str(exc)
            else:
                raise AssertionError(f"operator receipt invented missing upstream {field}=false")

            def poisoned_core_projection(repo_root, raw, field=field):
                value = clean_projection(repo_root, raw)
                value[field] = True
                return value

            owner.project_shadow_receipt_with_self_integrity = poisoned_core_projection
            try:
                owner.build_descriptor_shadow_operator_receipt(ROOT)
            except ValueError as exc:
                assert field in str(exc)
                assert "cannot sanitize upstream" in str(exc)
            else:
                raise AssertionError(f"operator receipt sanitized upstream {field}=true")

        # Later capability state remains additive below this final envelope, but any contradictory
        # upstream value must still fail closed rather than being overwritten by final false.
        for field in owner.OPTIONAL_DENIED_FALSE_FIELDS:
            def poisoned_later_projection(repo_root, raw, field=field):
                value = clean_projection(repo_root, raw)
                value[field] = True
                return value

            owner.project_shadow_receipt_with_self_integrity = poisoned_later_projection
            try:
                owner.build_descriptor_shadow_operator_receipt(ROOT)
            except ValueError as exc:
                assert field in str(exc)
                assert "cannot sanitize upstream" in str(exc)
            else:
                raise AssertionError(f"operator receipt sanitized upstream {field}=true")

        # Exact false upstream remains compatible with final closure for both core and additive
        # capability fields.
        def explicit_false_projection(repo_root, raw):
            value = clean_projection(repo_root, raw)
            for field in owner.OPTIONAL_DENIED_FALSE_FIELDS:
                value[field] = False
            return value

        owner.project_shadow_receipt_with_self_integrity = explicit_false_projection
        receipt = owner.build_descriptor_shadow_operator_receipt(ROOT)
        for field in owner.FINAL_DENIED_CAPABILITY_FIELDS:
            assert receipt[field] is False

        # Final-command metadata/digests/architecture declarations are operator-owned namespace.
        # Upstream projection must not pre-populate them and rely on dictionary ordering to hide a
        # contradictory or counterfeit value.
        for field in owner.OPERATOR_OWNED_RECEIPT_FIELDS:
            def colliding_projection(repo_root, raw, field=field):
                value = clean_projection(repo_root, raw)
                value[field] = "counterfeit-upstream-value"
                return value

            owner.project_shadow_receipt_with_self_integrity = colliding_projection
            try:
                owner.build_descriptor_shadow_operator_receipt(ROOT)
            except ValueError as exc:
                assert field in str(exc)
                assert "cannot pre-populate operator-owned field" in str(exc)
            else:
                raise AssertionError(f"operator receipt overwrote upstream operator-owned {field}")
    finally:
        owner.audit_descriptor_shadow = original_audit
        owner.project_shadow_receipt_with_self_integrity = original_projection

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
