#!/usr/bin/env python3
"""Fail-closed capability membrane for raw descriptor-shadow evidence.

This supporting organ validates capability-state fields already emitted by the existing
``audit_descriptor_shadow`` owner. It does not create descriptor authority, a receipt projector,
a runtime surface, a phone lane, or P0 authority.

A bounded operator projector must not sanitize a contradictory raw capability claim by simply
emitting its own constant ``False`` value. Raw evidence that claims authority, mutation, regression
execution, TESTED, runtime UI/TalkBack, deployment, callability, execution, delivery, acceptance,
or phone delivery is a contradictory source payload and must fail closed before operator projection.

The generic ``callable`` / ``executed`` fields describe the commissioned descriptor-shadow result
capability, not whether this Python source function can be invoked in a source environment.
"""

from __future__ import annotations

from collections.abc import Mapping


SCHEMA = "try-forever-shadow-raw-capability-membrane.v2"
DENIED_FALSE_FIELDS = (
    "descriptorAuthorityAdmitted",
    "ownerMutation",
    "regressionExecuted",
    "tested",
    "runtimeUi",
    "runtimeTalkBack",
    "deployed",
    "callable",
    "executed",
    "delivered",
    "accepted",
    "phoneDelivered",
)


class ShadowRawCapabilityMembraneError(ValueError):
    """Raw descriptor-shadow capability evidence contradicts the non-authoritative contract."""


def require_raw_shadow_capability_membrane(result: Mapping[str, object]) -> dict[str, object]:
    """Require every known raw capability state to be present and exactly ``False``.

    Missing fields are rejected as unknown rather than treated as false. Truthiness is never used.
    The returned object is a source-only audit receipt for composition by the existing receipt
    self-integrity owner; it grants no capability.
    """

    if not isinstance(result, Mapping):
        raise ShadowRawCapabilityMembraneError("raw descriptor-shadow evidence must be one mapping")

    for field in DENIED_FALSE_FIELDS:
        if field not in result:
            raise ShadowRawCapabilityMembraneError(
                f"raw descriptor-shadow evidence must carry explicit {field}=false"
            )
        if result.get(field) is not False:
            raise ShadowRawCapabilityMembraneError(
                f"raw descriptor-shadow evidence must carry {field}=false"
            )

    return {
        "schema": SCHEMA,
        "rawCapabilityMembraneValidated": True,
        **{field: False for field in DENIED_FALSE_FIELDS},
    }
