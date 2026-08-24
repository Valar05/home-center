#!/usr/bin/env python3
"""Hostile source fixture for bounded descriptor-shadow operator receipt identity custody.

SOURCE ONLY. This regression has not been observed executing in an authorized lane.
"""

from pathlib import Path

import try_forever_owner_surgery_descriptor_shadow_operator_receipt as owner


ROOT = Path("/evidence/repo")
HEX_A = "a" * 64


def bounded_projection(repo_root, raw):
    assert repo_root == ROOT
    return {
        "schema": owner.PROJECTOR_RECEIPT_SCHEMA,
        "sourceSchema": owner.RAW_SHADOW_SCHEMA,
        "receiptSelfIntegritySchema": owner.SELF_INTEGRITY_SCHEMA,
        "status": "SHADOW_MATCH",
        "summary": "bounded stable operator projection",
        "canonicalResultSha256": HEX_A,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
    }


def resign(receipt):
    payload = dict(receipt)
    payload.pop("operatorReceiptSha256", None)
    return {**payload, "operatorReceiptSha256": owner._operator_receipt_sha256(payload)}


def main() -> int:
    original_audit = owner.audit_descriptor_shadow
    original_projection = owner.project_shadow_receipt_with_self_integrity
    raw_state = {"schema": "raw-machine-evidence", "status": "RAW", "counter": 1}

    def fake_audit(**kwargs):
        assert kwargs["root"] == ROOT / owner.PATCH_ROOT
        return dict(raw_state)

    try:
        owner.audit_descriptor_shadow = fake_audit
        owner.project_shadow_receipt_with_self_integrity = bounded_projection

        first = owner.build_descriptor_shadow_operator_receipt(ROOT)
        second = owner.build_descriptor_shadow_operator_receipt(ROOT)
        assert first == second
        assert owner.verify_operator_receipt_identity(first) is True
        assert first["rawMachineEvidenceBound"] is True
        assert first["rawMachineEvidenceIncluded"] is False

        # Raw-only evidence drift must survive bounded projection through the raw evidence digest and
        # therefore change the complete operator receipt identity even when visible bounded content
        # is intentionally unchanged.
        raw_state["counter"] = 2
        drifted = owner.build_descriptor_shadow_operator_receipt(ROOT)
        assert drifted["summary"] == first["summary"]
        assert drifted["canonicalResultSha256"] == first["canonicalResultSha256"]
        assert drifted["rawMachineEvidenceSha256"] != first["rawMachineEvidenceSha256"]
        assert drifted["operatorReceiptSha256"] != first["operatorReceiptSha256"]
        assert owner.verify_operator_receipt_identity(drifted) is True

        # Final bounded-payload drift with a stale digest must fail verification. The verifier is
        # evidence integrity only; it does not rewrite the digest to make the counterfeit fit.
        tampered = dict(drifted)
        tampered["summary"] = "counterfeit bounded summary"
        try:
            owner.verify_operator_receipt_identity(tampered)
        except ValueError as exc:
            assert "does not match" in str(exc)
        else:
            raise AssertionError("operator receipt identity accepted tampered bounded payload")

        # A matching digest is not permission to launder capability or final-command invariants.
        # Re-sign the counterfeit payload to prove the verifier checks semantics before equality.
        capability_laundered = resign({**drifted, "tested": True})
        try:
            owner.verify_operator_receipt_identity(capability_laundered)
        except ValueError as exc:
            assert "cannot carry final tested capability" in str(exc)
        else:
            raise AssertionError("self-consistent digest laundered TESTED capability")

        raw_binding_laundered = resign({**drifted, "rawMachineEvidenceBound": False})
        try:
            owner.verify_operator_receipt_identity(raw_binding_laundered)
        except ValueError as exc:
            assert "requires exact final rawMachineEvidenceBound=true" in str(exc)
        else:
            raise AssertionError("self-consistent digest laundered raw evidence binding")

        # Schema and digest spelling are exact evidence too; normalization is not identity repair.
        wrong_schema = dict(drifted)
        wrong_schema["operatorReceiptSchema"] = f"{owner.SCHEMA}.counterfeit"
        try:
            owner.verify_operator_receipt_identity(wrong_schema)
        except ValueError as exc:
            assert "exact v4 schema" in str(exc)
        else:
            raise AssertionError("operator receipt identity accepted wrong schema")

        for counterfeit in ("A" * 64, " " + drifted["operatorReceiptSha256"], "a" * 63):
            bad_digest = dict(drifted)
            bad_digest["operatorReceiptSha256"] = counterfeit
            try:
                owner.verify_operator_receipt_identity(bad_digest)
            except ValueError as exc:
                assert "64 lowercase hexadecimal" in str(exc)
            else:
                raise AssertionError("operator receipt identity normalized counterfeit digest text")
    finally:
        owner.audit_descriptor_shadow = original_audit
        owner.project_shadow_receipt_with_self_integrity = original_projection

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
