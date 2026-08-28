#!/usr/bin/env python3
"""SOURCE-ONLY regression for the witness-parity facade's exact-container public contract.

The downstream integrity owner already requires an exact built-in ``dict`` and snapshots it before
semantic reads. This fixture prevents the supporting facade from drifting back to a broader
callback-capable ``Mapping`` promise. It is regression source only; this file being present is not
execution or TESTED evidence.
"""

from inspect import signature
from typing import get_type_hints

from try_forever_owner_surgery_witness_parity import audit_canonical_witness_parity


def main() -> int:
    hints = get_type_hints(audit_canonical_witness_parity)
    assert hints["result"] == dict[str, object]
    assert signature(audit_canonical_witness_parity).parameters["result"].annotation == "dict[str, object]"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
