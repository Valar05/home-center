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
        assert admitted["rawMachineEvidenceEmbedded"] is False
        assert admitted["authorityAdmitted"] is False
        assert admitted["tested"] is False
        assert admitted["delivered"] is False

        # A counterfeit can keep final-envelope-looking fields and the same raw digest while lying
        # about bounded operator meaning. Derivation custody must reject the lie itself.
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

        # Final-owner fields are outside this supporting gate; their presence does not become a
        # second finalizer or a reason to weaken exact upstream derivation checks.
        extended = {**receipt, "futureFinalOwnerField": "not-owned-here"}
        assert policy.require_operator_receipt_projection_derivation(ROOT, extended, RAW)[
            "projectionDerivedFromRaw"
        ] is True

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
