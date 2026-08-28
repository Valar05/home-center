#!/usr/bin/env python3
"""Hostile source fixture for raw descriptor-shadow source/capability integrity.

SOURCE ONLY. This regression has not been observed executing in an authorized lane.
"""

from try_forever_shadow_raw_capability_membrane import (
    OPTIONAL_DENIED_FALSE_FIELDS,
    RAW_SHADOW_SCHEMA,
    REQUIRED_DENIED_FALSE_FIELDS,
    require_raw_shadow_capability_membrane,
)


def valid_raw() -> dict[str, object]:
    return {
        "schema": RAW_SHADOW_SCHEMA,
        **{field: False for field in REQUIRED_DENIED_FALSE_FIELDS},
    }


def expect_rejected(payload: dict[str, object], needle: str) -> None:
    try:
        require_raw_shadow_capability_membrane(payload)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"contradictory raw capability evidence escaped: {payload!r}")


def main() -> int:
    admitted = require_raw_shadow_capability_membrane(valid_raw())
    assert admitted["rawSourceSchema"] == RAW_SHADOW_SCHEMA
    assert admitted["rawCapabilityMembraneValidated"] is True
    for field in REQUIRED_DENIED_FALSE_FIELDS:
        assert admitted[field] is False
    assert admitted["optionalCapabilityFieldsChecked"] == []

    # False-shaped capability fields are not descriptor-shadow evidence without exact source identity.
    for poisoned_schema in (
        None,
        "",
        "try-forever-owner-surgery-descriptor-shadow.v2",
        " try-forever-owner-surgery-descriptor-shadow.v3",
        "TRY-FOREVER-OWNER-SURGERY-DESCRIPTOR-SHADOW.V3",
        3,
    ):
        poisoned = valid_raw()
        if poisoned_schema is None:
            poisoned.pop("schema")
        else:
            poisoned["schema"] = poisoned_schema
        expect_rejected(poisoned, "exact descriptor-shadow v3 source schema")

    # Every descriptor-shadow v3 core capability is explicit. Missing is unknown, not false.
    for field in REQUIRED_DENIED_FALSE_FIELDS:
        missing = valid_raw()
        missing.pop(field)
        expect_rejected(missing, f"{field}=false")

    # Exact boolean false only. Truthy/falsey substitutes are not capability evidence.
    counterfeits = (True, 0, 1, None, "false", [], {})
    for field in REQUIRED_DENIED_FALSE_FIELDS:
        for value in counterfeits:
            poisoned = valid_raw()
            poisoned[field] = value
            expect_rejected(poisoned, f"{field}=false")

    # Later capability fields are additive to the raw schema: absence does not silently widen v3,
    # but presence may never carry a positive/unknown capability through a conservative projector.
    optional = valid_raw()
    for field in OPTIONAL_DENIED_FALSE_FIELDS:
        optional[field] = False
    admitted_optional = require_raw_shadow_capability_membrane(optional)
    assert admitted_optional["optionalCapabilityFieldsChecked"] == list(
        OPTIONAL_DENIED_FALSE_FIELDS
    )

    for field in OPTIONAL_DENIED_FALSE_FIELDS:
        for value in counterfeits:
            poisoned = valid_raw()
            poisoned[field] = value
            expect_rejected(poisoned, f"optional capability {field} must be false")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
