#!/usr/bin/env python3

from try_forever_heartbeat_selection_owner_probe import classify


def wrap(body: str) -> str:
    return "public class OperatorOverlayService {\n" + body + "\n}\n"


def main() -> int:
    selected_only = wrap(
        "private void applyHeartbeatLight(Button light, Object control) { light.setSelected(true); }\n"
        "private void applyHeartbeatSelectionAccessibility(Object model) { }"
    )
    result = classify(selected_only)
    seam = result["nativePersistentSelection"]
    assert seam["status"] == "PARTIAL_UNSAFE"
    assert "collection" in seam["reason"]
    assert "position-in-set" in seam["reason"]

    wired = wrap(
        "private void applyHeartbeatLight(Button light, Object control) {\n"
        "  light.setSelected(true);\n"
        "  applyHeartbeatSelectionAccessibility(model);\n"
        "}\n"
        "private void applyHeartbeatSelectionAccessibility(Object model) {\n"
        "  HeartbeatSelectionAccessibilityPolicy.CollectionDecision d = HeartbeatSelectionAccessibilityPolicy.fromModel(model, selected);\n"
        "  heartbeatLights.setAccessibilityDelegate(delegate);\n"
        "  AccessibilityNodeInfo.CollectionInfo.obtain(1, d.columnCount, false, AccessibilityNodeInfo.CollectionInfo.SELECTION_MODE_SINGLE);\n"
        "  AccessibilityNodeInfo.CollectionItemInfo.obtain(0, 1, item.positionInSet - 1, 1, false, item.selected);\n"
        "  int positionInSet = item.positionInSet; int setSize = item.setSize; boolean selected = item.selected;\n"
        "}"
    )
    result = classify(wired)
    assert result["nativePersistentSelection"]["status"] == "SOURCE_WIRED"

    # Counterfeit markers inside comments/literals must not become owner wiring.
    counterfeit = wrap(
        "private void applyHeartbeatLight(Button light, Object control) {\n"
        "  light.setSelected(true);\n"
        "  // applyHeartbeatSelectionAccessibility(model);\n"
        "  String fake = \"HeartbeatSelectionAccessibilityPolicy.fromModel AccessibilityNodeInfo.CollectionInfo.obtain AccessibilityNodeInfo.CollectionItemInfo.obtain positionInSet setSize selected\";\n"
        "}\n"
        "private void applyHeartbeatSelectionAccessibility(Object model) { }"
    )
    result = classify(counterfeit)
    assert result["nativePersistentSelection"]["status"] == "PARTIAL_UNSAFE"

    # A perfect-looking collection implementation in the wrong owner method must not count.
    wrong_method = wrap(
        "private void applyHeartbeatLight(Button light, Object control) { light.setSelected(true); }\n"
        "private void applyHeartbeatSelectionAccessibility(Object model) { }\n"
        "private void unrelated() {\n"
        "  HeartbeatSelectionAccessibilityPolicy.CollectionDecision d = HeartbeatSelectionAccessibilityPolicy.fromModel(model, selected);\n"
        "  heartbeatLights.setAccessibilityDelegate(delegate);\n"
        "  AccessibilityNodeInfo.CollectionInfo.obtain(1, d.columnCount, false, AccessibilityNodeInfo.CollectionInfo.SELECTION_MODE_SINGLE);\n"
        "  AccessibilityNodeInfo.CollectionItemInfo.obtain(0, 1, item.positionInSet - 1, 1, false, item.selected);\n"
        "  int positionInSet = item.positionInSet; int setSize = item.setSize; boolean selected = item.selected;\n"
        "}"
    )
    result = classify(wrong_method)
    assert result["nativePersistentSelection"]["status"] == "PARTIAL_UNSAFE"

    capability = result["capability"]
    assert result["schema"] == "try-forever-heartbeat-selection-owner-probe.v1"
    assert capability["sourceInspection"] is True
    for key in (
        "regressionExecuted",
        "tested",
        "runtimeUi",
        "runtimeTalkBack",
        "deployed",
        "phoneDelivered",
        "accepted",
    ):
        assert capability[key] is False

    print("Heartbeat persistent-selection owner evidence boundaries: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
