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


def expect_reject(callable_, fragment):
    try:
        callable_()
    except ValueError as exc:
        assert fragment in str(exc), str(exc)
    else:
        raise AssertionError(f"expected rejection containing {fragment!r}")


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
        assert owner.verify_operator_receipt_against_raw_evidence(first, raw_state) is True
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
        assert owner.verify_operator_receipt_against_raw_evidence(drifted, raw_state) is True

        # Identity verification is intentionally weaker than raw linkage verification. The earlier
        # receipt remains internally valid, but it cannot be rebound to later raw machine evidence.
        assert owner.verify_operator_receipt_identity(first) is True
        expect_reject(
            lambda: owner.verify_operator_receipt_against_raw_evidence(first, raw_state),
            "does not match the supplied raw machine evidence",
        )

        # Final bounded-payload drift with a stale digest must fail verification. The verifier is
        # evidence integrity only; it does not rewrite the digest to make the counterfeit fit.
        tampered = dict(drifted)
        tampered["summary"] = "counterfeit bounded summary"
        expect_reject(
            lambda: owner.verify_operator_receipt_identity(tampered),
            "does not match",
        )

        # A matching digest is not permission to launder capability or final-command invariants.
        # Re-sign the counterfeit payload to prove the verifier checks semantics before equality.
        capability_laundered = resign({**drifted, "tested": True})
        expect_reject(
            lambda: owner.verify_operator_receipt_identity(capability_laundered),
            "cannot carry final tested capability",
        )

        raw_binding_laundered = resign({**drifted, "rawMachineEvidenceBound": False})
        expect_reject(
            lambda: owner.verify_operator_receipt_identity(raw_binding_laundered),
            "requires exact final rawMachineEvidenceBound=true",
        )

        # Upstream composition custody must survive later reverification too. Re-signing a receipt
        # after changing a projector/raw/self-integrity contract cannot turn contract drift into a
        # valid final identity merely because the final digest is self-consistent.
        upstream_counterfeits = (
            ("schema", f"{owner.PROJECTOR_RECEIPT_SCHEMA}.counterfeit"),
            ("sourceSchema", f"{owner.RAW_SHADOW_SCHEMA}.counterfeit"),
            (
                "receiptSelfIntegritySchema",
                f"{owner.SELF_INTEGRITY_SCHEMA}.counterfeit",
            ),
        )
        for field, counterfeit_value in upstream_counterfeits:
            counterfeit = resign({**drifted, field: counterfeit_value})
            expect_reject(
                lambda counterfeit=counterfeit: owner.verify_operator_receipt_identity(counterfeit),
                f"requires exact upstream {field}=",
            )

        # Final schema and digest spelling are exact evidence too; normalization is not identity repair.
        wrong_schema = dict(drifted)
        wrong_schema["operatorReceiptSchema"] = f"{owner.SCHEMA}.counterfeit"
        expect_reject(
            lambda: owner.verify_operator_receipt_identity(wrong_schema),
            "exact v4 schema",
        )

        for counterfeit in ("A" * 64, " " + drifted["operatorReceiptSha256"], "a" * 63):
            bad_digest = dict(drifted)
            bad_digest["operatorReceiptSha256"] = counterfeit
            expect_reject(
                lambda bad_digest=bad_digest: owner.verify_operator_receipt_identity(bad_digest),
                "64 lowercase hexadecimal",
            )
    finally:
        owner.audit_descriptor_shadow = original_audit
        owner.project_shadow_receipt_with_self_integrity = original_projection

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
