#!/usr/bin/env python3
"""RED operator-command boundary for raw descriptor-shadow capability overclaims.

SOURCE ONLY. The existing operator receipt command must eventually reject contradictory raw
capability evidence through the existing self-integrity owner before returning a bounded receipt.
"""

from pathlib import Path

import try_forever_owner_surgery_descriptor_shadow_operator_receipt as owner
from test_try_forever_shadow_raw_capability_owner_boundary import raw_match

ROOT = Path("/repo")


def main() -> int:
    original = owner.audit_descriptor_shadow
    try:
        for field in (
            "regressionExecuted",
            "tested",
            "runtimeUi",
            "runtimeTalkBack",
            "phoneDelivered",
        ):
            raw = raw_match()
            raw[field] = True
            owner.audit_descriptor_shadow = lambda **kwargs: raw
            try:
                owner.build_descriptor_shadow_operator_receipt(ROOT)
            except ValueError as exc:
                assert f"{field}=false" in str(exc), str(exc)
            else:
                raise AssertionError(
                    f"operator receipt sanitized contradictory raw capability {field}=true"
                )
    finally:
        owner.audit_descriptor_shadow = original

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
