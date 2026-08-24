#!/usr/bin/env python3
"""Fail-closed capability membrane for raw descriptor-shadow evidence.

This supporting organ validates source identity and capability-state fields already emitted by the
existing ``audit_descriptor_shadow`` owner. It does not create descriptor authority, a receipt
projector, a runtime surface, a phone lane, or P0 authority.

A bounded operator projector must not sanitize a contradictory raw capability claim by simply
emitting its own constant ``False`` value. Likewise, a mapping with the right false-shaped fields
must not earn descriptor-shadow admission unless it already carries the exact descriptor-shadow v3
schema identity. If later raw evidence also carries deployment/callability/execution/delivery/
acceptance fields, those optional capability claims must already be exact false; this gate does not
silently widen v3 by requiring fields its owner does not emit.

The generic optional ``callable`` / ``executed`` fields describe the commissioned descriptor-shadow
result capability, not whether this Python source function can be invoked in a source environment.
"""

from __future__ import annotations

from collections.abc import Mapping

from try_forever_owner_surgery_descriptor_shadow_audit import SCHEMA as RAW_SHADOW_SCHEMA


SCHEMA = "try-forever-shadow-raw-capability-membrane.v3"
REQUIRED_DENIED_FALSE_FIELDS = (
    "descriptorAuthorityAdmitted",
    "ownerMutation",
    "regressionExecuted",
    "tested",
    "runtimeUi",
    "runtimeTalkBack",
    "phoneDelivered",
)
OPTIONAL_DENIED_FALSE_FIELDS = (
    "deployed",
    "callable",
    "executed",
    "delivered",
    "accepted",
)


class ShadowRawCapabilityMembraneError(ValueError):
    """Raw descriptor-shadow source/capability evidence contradicts the non-authoritative contract."""


def require_raw_shadow_capability_membrane(result: Mapping[str, object]) -> dict[str, object]:
    """Require exact raw v3 identity/core denial and reject later positive capability claims.

    Missing or wrong source schema is rejected before any capability field can earn admission.
    Missing v3 core fields are rejected as unknown rather than treated as false. Optional later
    capability fields do not become mandatory merely because this supporting membrane knows how to
    reject them; when present, however, they must be exact false. Truthiness is never used.
    """

    if not isinstance(result, Mapping):
        raise ShadowRawCapabilityMembraneError("raw descriptor-shadow evidence must be one mapping")
    if result.get("schema") != RAW_SHADOW_SCHEMA:
        raise ShadowRawCapabilityMembraneError(
            "raw capability admission requires exact descriptor-shadow v3 source schema"
        )

    for field in REQUIRED_DENIED_FALSE_FIELDS:
        if field not in result:
            raise ShadowRawCapabilityMembraneError(
                f"raw descriptor-shadow evidence must carry explicit {field}=false"
            )
        if result.get(field) is not False:
            raise ShadowRawCapabilityMembraneError(
                f"raw descriptor-shadow evidence must carry {field}=false"
            )

    for field in OPTIONAL_DENIED_FALSE_FIELDS:
        if field in result and result.get(field) is not False:
            raise ShadowRawCapabilityMembraneError(
                f"raw descriptor-shadow optional capability {field} must be false when present"
            )

    return {
        "schema": SCHEMA,
        "rawSourceSchema": RAW_SHADOW_SCHEMA,
        "rawCapabilityMembraneValidated": True,
        **{field: False for field in REQUIRED_DENIED_FALSE_FIELDS},
        "optionalCapabilityFieldsChecked": [
            field for field in OPTIONAL_DENIED_FALSE_FIELDS if field in result
        ],
    }
