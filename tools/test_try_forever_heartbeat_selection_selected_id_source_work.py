#!/usr/bin/env python3
"""Source-only regression for direct persistent-selection id source-work custody.

The accessibility collection owner must bound an arbitrary direct selectedId before repeated
case-insensitive comparison against rendered controls. Accepted ids remain exact; over-ceiling
queries become no selection rather than a truncated or normalized identity. SOURCE / UNEXECUTED.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / (
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatSelectionAccessibilityPolicy.java"
)


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")

    assert "MAX_DIRECT_SELECTED_ID_SOURCE_CODE_UNITS" in source
    assert "HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS" in source
    assert "String selected = boundedDirectSelectedId(selectedId);" in source
    assert "selectedId.length() > MAX_DIRECT_SELECTED_ID_SOURCE_CODE_UNITS" in source

    helper = source[source.index("private static String boundedDirectSelectedId") :]
    assert "return \"\";" in helper
    assert "return selectedId;" in helper
    assert ".trim()" not in helper
    assert ".toLowerCase" not in helper

    from_model = source.index("public static CollectionDecision fromModel")
    helper_start = source.index("private static String boundedDirectSelectedId", from_model)
    body = source[from_model:helper_start]
    assert body.index("boundedDirectSelectedId(selectedId)") < body.index("equalsIgnoreCase(selected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
