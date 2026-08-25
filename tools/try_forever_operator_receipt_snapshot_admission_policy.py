#!/usr/bin/env python3
"""Supporting admission policy for bounded operator-receipt snapshot custody.

The existing snapshot organ claims bounded exact-JSON custody, but arbitrary Python ``Mapping``
implementations can execute caller-owned code from ``items()`` before node/text budgets can constrain
that work. Exact JSON object evidence therefore admits only the built-in ``dict`` container. This is
container admission only; the existing snapshot organ remains the owner of recursive JSON shape,
resource budgets, detachment, diagnostics, and capability state.

Diagnostic root context is evidence about an error surface, not canonical receipt identity. It gets a
small pre-projection source ceiling so JSON escaping itself cannot become an unbounded diagnostic
work channel. Accepted diagnostic context is preserved exactly; this policy does not strip, case-fold,
or otherwise normalize it.
"""

from __future__ import annotations


SCHEMA = "try-forever-operator-receipt-snapshot-admission-policy.v1"
MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS = 4_096


class SnapshotAdmissionPolicyError(ValueError):
    """Snapshot input cannot enter the bounded exact-container/diagnostic-context contract."""


def is_exact_json_object(value: object) -> bool:
    """Return true only for the built-in JSON-object container used by Python's JSON decoder."""

    return type(value) is dict


def admit_diagnostic_context(value: object) -> str:
    """Admit one exact bounded diagnostic root label without normalization."""

    if type(value) is not str or not value:
        raise SnapshotAdmissionPolicyError("diagnostic context must be one non-empty exact string")
    if len(value) > MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS:
        raise SnapshotAdmissionPolicyError(
            "diagnostic context exceeds source ceiling "
            f"{MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS} code points"
        )
    return value


def source_capabilities() -> dict[str, object]:
    """Report only capability owned by this supporting policy."""

    return {
        "schema": SCHEMA,
        "exactBuiltinObjectAdmission": True,
        "boundedDiagnosticContextAdmission": True,
        "ownerWired": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "deployed": False,
        "callable": False,
        "executed": False,
        "delivered": False,
        "accepted": False,
        "phoneP0MutationAuthority": False,
    }
