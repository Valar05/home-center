#!/usr/bin/env python3
"""Hostile source fixture for operator-receipt derivation custody.

SOURCE ONLY. This regression has not been observed executing in an authorized lane.
"""

from pathlib import Path

import try_forever_operator_receipt_derivation_custody as policy


ROOT = Path("/evidence/repo")
RAW = {"schema": policy.RAW_SHADOW_SCHEMA, "counter": 1}
EXPECTED = {
    "schema": "projector.v2",
    "sourceSchema": policy.RAW_SHADOW_SCHEMA,
    "receiptSelfIntegritySchema": "self.v2",
    "status": "SHADOW_MATCH",
    "summary": "bounded truth",
    "artifactSetMatch": True,
}
FINAL_FIELDS = (
    "operatorReceiptSchema",
    "rawMachineEvidenceSha256",
    "operatorReceiptSha256",
)


def expect_reject(callable_, fragment: str) -> None:
    try:
        callable_()
    except policy.OperatorReceiptDerivationError as exc:
        assert fragment in str(exc), str(exc)
    else:
        raise AssertionError(f"expected derivation rejection containing {fragment!r}")


def main() -> int:
    original_projector = policy.project_shadow_receipt_with_self_integrity

    def fake_projector(repo_root, raw_result):
        assert repo_root == ROOT
        assert raw_result == RAW
        return dict(EXPECTED)

    try:
        policy.project_shadow_receipt_with_self_integrity = fake_projector

        receipt = {
            **EXPECTED,
            "operatorReceiptSchema": "final.v4",
            "rawMachineEvidenceSha256": "a" * 64,
            "operatorReceiptSha256": "b" * 64,
        }
        admitted = policy.require_operator_receipt_projection_derivation(ROOT, receipt, RAW)
        assert admitted["projectionFieldsVerified"] == len(EXPECTED)
        assert admitted["projectionDerivedFromRaw"] is True
        assert admitted["receiptFieldsetClosed"] is False
        assert admitted["rawMachineEvidenceEmbedded"] is False
        assert admitted["authorityAdmitted"] is False
        assert admitted["tested"] is False
        assert admitted["delivered"] is False

        # Default supporting mode still owns only upstream derivation; final-owner fields may coexist.
        extended = {**receipt, "futureFinalOwnerField": "not-owned-here"}
        assert policy.require_operator_receipt_projection_derivation(ROOT, extended, RAW)[
            "receiptFieldsetClosed"
        ] is False

        # Final-owner mode closes the complete field namespace. A counterfeit cannot append an
        # undeclared field, re-sign its outer digest, and pass derivation as a subset check.
        exact = policy.require_operator_receipt_projection_derivation(
            ROOT,
            receipt,
            RAW,
            allowed_extra_fields=FINAL_FIELDS,
        )
        assert exact["receiptFieldsetClosed"] is True
        expect_reject(
            lambda: policy.require_operator_receipt_projection_derivation(
                ROOT,
                {**receipt, "futureCapabilityProof": "counterfeit"},
                RAW,
                allowed_extra_fields=FINAL_FIELDS,
            ),
            "undeclared field(s): futureCapabilityProof",
        )
        missing_final = dict(receipt)
        missing_final.pop("operatorReceiptSha256")
        expect_reject(
            lambda: policy.require_operator_receipt_projection_derivation(
                ROOT,
                missing_final,
                RAW,
                allowed_extra_fields=FINAL_FIELDS,
            ),
            "missing declared field(s): operatorReceiptSha256",
        )
        expect_reject(
            lambda: policy.require_operator_receipt_projection_derivation(
                ROOT,
                receipt,
                RAW,
                allowed_extra_fields=("operatorReceiptSchema", "operatorReceiptSchema"),
            ),
            "field names must be unique",
        )

        # Existing value-derivation wounds remain independently enforced.
        expect_reject(
            lambda: policy.require_operator_receipt_projection_derivation(
                ROOT,
                {**receipt, "summary": "counterfeit bounded truth"},
                RAW,
            ),
            "summary does not derive",
        )
        expect_reject(
            lambda: policy.require_operator_receipt_projection_derivation(
                ROOT,
                {**receipt, "status": "SHADOW_DIVERGED"},
                RAW,
            ),
            "status does not derive",
        )

        missing = dict(receipt)
        missing.pop("artifactSetMatch")
        expect_reject(
            lambda: policy.require_operator_receipt_projection_derivation(ROOT, missing, RAW),
            "missing derived upstream field artifactSetMatch",
        )

        expect_reject(
            lambda: policy.require_operator_receipt_projection_derivation(
                ROOT,
                receipt,
                {**RAW, "schema": f"{policy.RAW_SHADOW_SCHEMA}.counterfeit"},
            ),
            "exact descriptor-shadow raw source schema",
        )
    finally:
        policy.project_shadow_receipt_with_self_integrity = original_projector

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
