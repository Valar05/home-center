#!/usr/bin/env python3
"""Hostile SOURCE/UNEXECUTED fixture for final-v4 receipt field-set custody."""

from pathlib import Path

from try_forever_operator_receipt_identity_fieldset import (
    OperatorReceiptIdentityFieldsetError,
    SELF_INTEGRITY_RECEIPT_FIELDS,
    require_exact_final_receipt_fieldset,
)
from try_forever_owner_surgery_descriptor_shadow_audit import (
    CANONICAL_SCHEMA,
    SCHEMA as SHADOW_SCHEMA,
    SUPPORTED,
)
from try_forever_owner_surgery_descriptor_shadow_operator_receipt import (
    FINAL_DENIED_CAPABILITY_FIELDS,
    OPERATOR_OWNED_RECEIPT_FIELDS,
)
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    TEMPORAL_BINDING_SCHEMA,
    TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
    project_shadow_receipt_with_self_integrity,
)


ROOT = Path("/repo")
CANONICAL_SHA = "1" * 64
ARTIFACT_SHA = "a" * 64


def artifact():
    return {"path": "patches/a.patch", "byteCount": 10, "sha256": ARTIFACT_SHA}


def raw_match():
    temporal = {
        "schema": TEMPORAL_BINDING_SCHEMA,
        "status": "TEMPORAL_CONTENT_BOUND",
        "canonicalResultSha256": CANONICAL_SHA,
        "shadowCanonicalResultSha256": CANONICAL_SHA,
        "temporalBindingProven": True,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": "bounded temporal evidence",
        "receiptIntegritySchema": TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
        "shadowReceiptContextAdmitted": True,
    }
    return {
        "schema": SHADOW_SCHEMA,
        "status": "SHADOW_MATCH",
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalAuthoritySchema": CANONICAL_SCHEMA,
        "canonicalResultSha256": CANONICAL_SHA,
        "canonicalEvidenceComplete": True,
        "canonicalArtifactDirectoryEntriesObserved": 2,
        "canonicalArtifactCandidatesObserved": 1,
        "descriptorCapabilityStatus": SUPPORTED,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "boundary": "raw boundary",
        "portableShadowArtifacts": [artifact()],
        "descriptorArtifacts": [artifact()],
        "descriptorArtifactDirectoryEntriesObserved": 2,
        "descriptorArtifactCandidatesObserved": 1,
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "temporalContentBinding": temporal,
        "temporalBindingProven": True,
    }


def expect_reject(receipt, text):
    try:
        require_exact_final_receipt_fieldset(
            receipt,
            operator_owned_fields=OPERATOR_OWNED_RECEIPT_FIELDS,
            denied_capability_fields=FINAL_DENIED_CAPABILITY_FIELDS,
        )
    except OperatorReceiptIdentityFieldsetError as exc:
        assert text in str(exc)
    else:
        raise AssertionError("hostile final receipt field set was admitted")


def main() -> int:
    upstream = project_shadow_receipt_with_self_integrity(ROOT, raw_match())
    assert frozenset(upstream) == SELF_INTEGRITY_RECEIPT_FIELDS

    final = dict(upstream)
    for field in OPERATOR_OWNED_RECEIPT_FIELDS:
        final[field] = "placeholder" if field.endswith("Sha256") else False
    final["operatorReceiptSchema"] = "try-forever-owner-surgery-descriptor-shadow-operator-receipt.v4"
    final["rawMachineEvidenceRemainsSeparate"] = True
    final["rawMachineEvidenceIncluded"] = False
    final["rawMachineEvidenceBound"] = True
    final["secondReceiptProjectorCreated"] = False
    final["secondDescriptorAuthorityCreated"] = False
    final["phoneP0MutationAuthority"] = False
    for field in FINAL_DENIED_CAPABILITY_FIELDS:
        final[field] = False

    result = require_exact_final_receipt_fieldset(
        final,
        operator_owned_fields=OPERATOR_OWNED_RECEIPT_FIELDS,
        denied_capability_fields=FINAL_DENIED_CAPABILITY_FIELDS,
    )
    assert result["finalFieldsetExact"] is True
    assert result["regressionExecuted"] is False
    assert result["tested"] is False

    hitchhiker = dict(final)
    hitchhiker["futureCapabilityProof"] = "re-signed but undeclared"
    expect_reject(hitchhiker, "undeclared final field")

    missing = dict(final)
    del missing["summary"]
    expect_reject(missing, "missing declared final field")

    try:
        require_exact_final_receipt_fieldset(
            final,
            operator_owned_fields=("operatorReceiptSchema", "operatorReceiptSchema"),
            denied_capability_fields=FINAL_DENIED_CAPABILITY_FIELDS,
        )
    except OperatorReceiptIdentityFieldsetError as exc:
        assert "must be unique" in str(exc)
    else:
        raise AssertionError("duplicate owner field declaration was admitted")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
