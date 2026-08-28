#!/usr/bin/env python3
"""SOURCE / UNEXECUTED behavioral fixture for final-v4 identity field-set custody.

The source-wired final receipt owner must reject an undeclared field even when the attacker recomputes
a mathematically valid final receipt digest. The same rejection must protect raw-linkage reverification.
This is source/regression evidence only; it is not TESTED, runtime, deployment, delivery, or acceptance.
"""

from pathlib import Path

from try_forever_owner_surgery_descriptor_shadow_audit import (
    CANONICAL_SCHEMA,
    SCHEMA as SHADOW_SCHEMA,
    SUPPORTED,
)
from try_forever_owner_surgery_descriptor_shadow_operator_receipt import (
    FINAL_DENIED_CAPABILITY_FIELDS,
    SCHEMA as OPERATOR_SCHEMA,
    _operator_receipt_sha256,
    _raw_machine_evidence_sha256,
    verify_operator_receipt_against_raw_evidence,
    verify_operator_receipt_identity,
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
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
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


def make_final(raw):
    upstream = project_shadow_receipt_with_self_integrity(ROOT, raw)
    payload = {
        **upstream,
        "operatorReceiptSchema": OPERATOR_SCHEMA,
        "rawMachineEvidenceRemainsSeparate": True,
        "rawMachineEvidenceIncluded": False,
        "rawMachineEvidenceBound": True,
        "rawMachineEvidenceSha256": _raw_machine_evidence_sha256(raw),
        "secondReceiptProjectorCreated": False,
        "secondDescriptorAuthorityCreated": False,
        "phoneP0MutationAuthority": False,
        **{field: False for field in FINAL_DENIED_CAPABILITY_FIELDS},
    }
    return {
        **payload,
        "operatorReceiptSha256": _operator_receipt_sha256(payload),
    }


def resign(receipt):
    payload = dict(receipt)
    payload.pop("operatorReceiptSha256", None)
    return {
        **payload,
        "operatorReceiptSha256": _operator_receipt_sha256(payload),
    }


def expect_hitchhiker_reject(call):
    try:
        call()
    except ValueError as exc:
        assert "undeclared final field" in str(exc)
    else:
        raise AssertionError("re-signed undeclared final field was admitted")


def main() -> int:
    raw = raw_match()
    valid = make_final(raw)
    assert verify_operator_receipt_identity(valid) is True
    assert verify_operator_receipt_against_raw_evidence(valid, raw) is True

    hitchhiker = dict(valid)
    hitchhiker["futureCapabilityProof"] = "re-signed but undeclared"
    hitchhiker = resign(hitchhiker)

    expect_hitchhiker_reject(lambda: verify_operator_receipt_identity(hitchhiker))
    expect_hitchhiker_reject(
        lambda: verify_operator_receipt_against_raw_evidence(hitchhiker, raw)
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
