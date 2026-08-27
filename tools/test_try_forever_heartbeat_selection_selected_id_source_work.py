#!/usr/bin/env python3
"""Source-only regression for persistent-selection semantic-id source-work custody.

Both collection construction (`selectedId`) and direct `itemById` lookup must bound arbitrary direct
semantic-id text before repeated case-insensitive comparison. Accepted ids remain exact; over-ceiling
queries become no selection/null lookup rather than a truncated or normalized identity.
SOURCE / UNEXECUTED.
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
    assert "String target = boundedDirectSelectedId(semanticId);" in source
    assert "selectedId.length() > MAX_DIRECT_SELECTED_ID_SOURCE_CODE_UNITS" in source

    helper_start = source.index("private static String boundedDirectSelectedId")
    helper = source[helper_start:]
    assert "return \"\";" in helper
    assert "return selectedId;" in helper
    assert ".trim()" not in helper
    assert ".toLowerCase" not in helper

    item_lookup = source.index("public ItemDecision itemById")
    item_lookup_end = source.index("private HeartbeatSelectionAccessibilityPolicy", item_lookup)
    item_body = source[item_lookup:item_lookup_end]
    assert item_body.index("boundedDirectSelectedId(semanticId)") < item_body.index("equalsIgnoreCase(target)")
    assert "equalsIgnoreCase(semanticId)" not in item_body

    from_model = source.index("public static CollectionDecision fromModel")
    body = source[from_model:helper_start]
    assert body.index("boundedDirectSelectedId(selectedId)") < body.index("equalsIgnoreCase(selected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
