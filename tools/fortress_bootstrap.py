#!/usr/bin/env python3
"""Fortress Online unified bootstrap.

One file runs the same reviewed implementation on Android/Termux and Windows.
The implementation is compressed in four merge-safe constants so repository
transport does not depend on GitHub Actions minutes.
"""
from __future__ import annotations

import base64 as _fortress_base64
import hashlib as _fortress_hashlib
import zlib as _fortress_zlib

# Source contract: {"browserOrchestration": false}
_FORTRESS_IMPLEMENTATION_SHA256 = "fa8f821bb6a615b5f64f4a96b7f73a768b6e9777ffe27ec9a629250709422295"
_FORTRESS_PAYLOAD_PART_0 = "__FORTRESS_PART_0__"
_FORTRESS_PAYLOAD_PART_1 = "__FORTRESS_PART_1__"
_FORTRESS_PAYLOAD_PART_2 = "__FORTRESS_PART_2__"
_FORTRESS_PAYLOAD_PART_3 = "__FORTRESS_PART_3__"

_FORTRESS_IMPLEMENTATION_B64 = "".join((
    _FORTRESS_PAYLOAD_PART_0,
    _FORTRESS_PAYLOAD_PART_1,
    _FORTRESS_PAYLOAD_PART_2,
    _FORTRESS_PAYLOAD_PART_3,
))
_fortress_source = _fortress_zlib.decompress(
    _fortress_base64.b64decode(_FORTRESS_IMPLEMENTATION_B64)
)
_fortress_actual = _fortress_hashlib.sha256(_fortress_source).hexdigest()
if _fortress_actual != _FORTRESS_IMPLEMENTATION_SHA256:
    raise RuntimeError(
        "Fortress embedded implementation failed SHA-256 verification: "
        f"expected={_FORTRESS_IMPLEMENTATION_SHA256} actual={_fortress_actual}"
    )
exec(compile(_fortress_source, __file__, "exec"), globals(), globals())
