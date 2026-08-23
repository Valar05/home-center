#!/usr/bin/env python3
"""Bounded operator receipt command for the existing descriptor-shadow organs.

This is a thin composition surface, not a second descriptor authority and not a second receipt
projector. ``audit_descriptor_shadow`` remains the raw machine-evidence producer. The operator path
always routes that raw result through the existing self-integrity gate, which in turn delegates to
the existing bounded display projector.

Raw evidence is never rewritten into authority, TESTED, runtime, deployment, phone delivery, or
acceptance. P0 and primary-phone surfaces are outside this command.
"""

from __future__ import annotations

import json
from pathlib import Path

from try_forever_owner_surgery_descriptor_shadow_audit import audit_descriptor_shadow
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    project_shadow_receipt_with_self_integrity,
)


SCHEMA = "try-forever-owner-surgery-descriptor-shadow-operator-receipt.v1"


def build_descriptor_shadow_operator_receipt(
    repo_root: Path = Path("."),
    **audit_kwargs,
) -> dict[str, object]:
    """Produce one self-audited operator receipt from the existing raw shadow owner."""

    raw_result = audit_descriptor_shadow(**audit_kwargs)
    receipt = project_shadow_receipt_with_self_integrity(repo_root, raw_result)
    return {
        **receipt,
        "operatorReceiptSchema": SCHEMA,
        "rawMachineEvidencePreserved": True,
        "secondReceiptProjectorCreated": False,
        "secondDescriptorAuthorityCreated": False,
        "phoneP0Consumed": False,
    }


if __name__ == "__main__":
    print(json.dumps(build_descriptor_shadow_operator_receipt(), indent=2, sort_keys=True))
