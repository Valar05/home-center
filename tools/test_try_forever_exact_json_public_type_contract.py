#!/usr/bin/env python3
"""Source regression for public typing versus exact-JSON runtime admission.

Every public entrypoint here rejects arbitrary Mapping implementations at runtime, so its public type
contract must advertise the same exact built-in-dict boundary. Type hints are developer-facing
capability evidence; allowing Mapping statically while rejecting it at runtime is a false surface.

Regression source is not executed-test evidence.
"""

from __future__ import annotations

import inspect

from try_forever_canonical_result_fingerprint import canonical_result_sha256
from try_forever_operator_receipt_snapshot_custody import (
    snapshot_json_mapping,
    snapshot_verification_inputs,
)


def _annotation(callable_object, parameter: str) -> str:
    return str(inspect.signature(callable_object).parameters[parameter].annotation)


def main() -> int:
    assert _annotation(canonical_result_sha256, "result") == "dict[str, object]"
    assert _annotation(snapshot_json_mapping, "value") == "dict[str, object]"
    assert _annotation(snapshot_verification_inputs, "receipt") == "dict[str, object]"
    assert _annotation(snapshot_verification_inputs, "raw_result") == "dict[str, object] | None"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
