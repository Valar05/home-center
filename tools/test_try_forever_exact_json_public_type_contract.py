#!/usr/bin/env python3
"""Source regression for public typing versus exact-JSON runtime admission.

This fixture is intentionally RED until every public entrypoint that rejects arbitrary Mapping
implementations advertises that same exact built-in-dict boundary. Type hints are developer-facing
evidence: allowing Mapping statically while rejecting it at runtime creates a false capability surface.

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
    # Fingerprint public API is source-wired to the exact built-in dict contract.
    assert _annotation(canonical_result_sha256, "result") == "dict[str, object]"

    # RED owner boundary: snapshot custody already rejects arbitrary Mapping at runtime, but its
    # public annotations still advertise Mapping. These assertions should become green only when the
    # existing snapshot owner narrows its public type contract without changing runtime semantics.
    assert _annotation(snapshot_json_mapping, "value") == "dict[str, object]"
    assert _annotation(snapshot_verification_inputs, "receipt") == "dict[str, object]"
    assert _annotation(snapshot_verification_inputs, "raw_result") == "dict[str, object] | None"

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
