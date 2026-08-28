#!/usr/bin/env python3
"""Regression source for exact descriptor-shadow temporal status admission.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

from try_forever_shadow_temporal_status_contract import (
    ADMITTED_TEMPORAL_STATUSES,
    admit_temporal_status,
)


def main() -> int:
    for status in sorted(ADMITTED_TEMPORAL_STATUSES):
        assert admit_temporal_status(status) == status

    for invalid in (
        "",
        "TEMPORAL_CONTENT_BOUND ",
        " temporal_content_bound",
        "TEMPORAL_CONTENT_UNKNOWN",
        "SHADOW_MATCH",
        None,
        False,
        0,
        "wound-\udcff",
    ):
        try:
            admit_temporal_status(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unknown temporal status earned admission: {invalid!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
