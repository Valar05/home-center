#!/usr/bin/env python3
"""Regression source forbidding dormant local semantic-parser ownership in canonical v10.

SOURCE ONLY / RED until the canonical owner removes parser fossils that became dead when
parse_owner_surgery_observation(...) became the sole semantic producer for both backends.
"""

import inspect

import try_forever_owner_surgery_custody_probe as custody


DEAD_LOCAL_PARSER_SYMBOLS = (
    "_promotion_candidate",
    "_reject_duplicate_json_members",
    "_consistent_delta_string",
    "BASE_RE",
    "OWNER_RE",
    "STATE_RE",
    "DELTA_BASE_KEYS",
    "DELTA_STATE_KEYS",
)


def main() -> int:
    patch_source = inspect.getsource(custody.inspect_patch)
    delta_source = inspect.getsource(custody.inspect_delta)

    assert "parse_owner_surgery_observation" in patch_source
    assert "parse_owner_surgery_observation" in delta_source
    assert "json.loads" not in delta_source
    assert "admit_patch_metadata" not in patch_source

    present = [name for name in DEAD_LOCAL_PARSER_SYMBOLS if hasattr(custody, name)]
    assert not present, (
        "canonical v10 retains dormant local semantic-parser ownership after composition: "
        + ", ".join(present)
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
