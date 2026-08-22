#!/usr/bin/env python3

from try_forever_heartbeat_selection_owner_probe import classify


def wrap(body: str) -> str:
    return "public class OperatorOverlayService {\n" + body + "\n}\n"


def main() -> int:
    selected_only = wrap(
        "private void applyHeartbeatLight(Button light, Object control) { light.setSelected(true); }\n"
        "private void refreshHeartbeatSelection() { child.setSelected(true); }\n"
        "private void rebuildHeartbeatLights(Object model) { }\n"
        "private void applyHeartbeatSelectionAccessibility(Object model) { }"
    )
    result = classify(selected_only)
    seam = result["nativePersistentSelection"]
    assert seam["status"] == "PARTIAL_UNSAFE"
    assert "collection" in seam["reason"]
    assert "row/item" in seam["reason"]

    wired = wrap(
        "private void applyHeartbeatLight(Button light, Object control) {\n"
        "  light.setSelected(true);\n"
        "}\n"
        "private void rebuildHeartbeatLights(Object model) {\n"
        "  createHeartbeatLight(control);\n"
        "  applyHeartbeatSelectionAccessibility(model);\n"
        "}\n"
        "private void refreshHeartbeatSelection() {\n"
        "  child.setSelected(true);\n"
        "  applyHeartbeatSelectionAccessibility(currentHeartbeatModel());\n"
        "}\n"
        "private Object currentHeartbeatModel() { return model; }\n"
        "private void applyHeartbeatSelectionAccessibility(Object model) {\n"
        "  HeartbeatSelectionAccessibilityPolicy.CollectionDecision d = HeartbeatSelectionAccessibilityPolicy.fromModel(model, selectedId);\n"
        "  heartbeatLights.setAccessibilityDelegate(delegate);\n"
        "  AccessibilityNodeInfo.CollectionInfo.obtain(d.rowCount, d.columnCount, false, AccessibilityNodeInfo.CollectionInfo.SELECTION_MODE_SINGLE);\n"
        "  AccessibilityNodeInfo.CollectionItemInfo.obtain(item.rowIndex, 1, item.columnIndex, 1, false, item.selected);\n"
        "  boolean selected = item.selected;\n"
        "}"
    )
    result = classify(wired)
    assert result["nativePersistentSelection"]["status"] == "SOURCE_WIRED"

    # A per-light-only implementation repeatedly rewrites collection semantics while children are
    # being created and does not prove selected item metadata refreshes after a later selection.
    per_light_only = wrap(
        "private void applyHeartbeatLight(Button light, Object control) {\n"
        "  light.setSelected(true);\n"
        "  applyHeartbeatSelectionAccessibility(model);\n"
        "}\n"
        "private void rebuildHeartbeatLights(Object model) { createHeartbeatLight(control); }\n"
        "private void refreshHeartbeatSelection() { child.setSelected(true); }\n"
        "private void applyHeartbeatSelectionAccessibility(Object model) {\n"
        "  HeartbeatSelectionAccessibilityPolicy.CollectionDecision d = HeartbeatSelectionAccessibilityPolicy.fromModel(model, selectedId);\n"
        "  heartbeatLights.setAccessibilityDelegate(delegate);\n"
        "  AccessibilityNodeInfo.CollectionInfo.obtain(d.rowCount, d.columnCount, false, AccessibilityNodeInfo.CollectionInfo.SELECTION_MODE_SINGLE);\n"
        "  AccessibilityNodeInfo.CollectionItemInfo.obtain(item.rowIndex, 1, item.columnIndex, 1, false, item.selected);\n"
        "  boolean selected = item.selected;\n"
        "}"
    )
    result = classify(per_light_only)
    seam = result["nativePersistentSelection"]
    assert seam["status"] == "PARTIAL_UNSAFE"
    assert "per-light side effect" in seam["reason"]
    assert "selection-change collection refresh" in seam["reason"]

    # Counterfeit markers inside comments/literals must not become owner wiring.
    counterfeit = wrap(
        "private void applyHeartbeatLight(Button light, Object control) {\n"
        "  light.setSelected(true);\n"
        "  // applyHeartbeatSelectionAccessibility(model);\n"
        "  String fake = \"HeartbeatSelectionAccessibilityPolicy.fromModel AccessibilityNodeInfo.CollectionInfo.obtain AccessibilityNodeInfo.CollectionItemInfo.obtain rowCount columnCount rowIndex columnIndex selected\";\n"
        "}\n"
        "private void rebuildHeartbeatLights(Object model) { }\n"
        "private void refreshHeartbeatSelection() { child.setSelected(true); }\n"
        "private void applyHeartbeatSelectionAccessibility(Object model) { }"
    )
    result = classify(counterfeit)
    assert result["nativePersistentSelection"]["status"] == "PARTIAL_UNSAFE"

    # A perfect-looking collection implementation in the wrong owner method must not count.
    wrong_method = wrap(
        "private void applyHeartbeatLight(Button light, Object control) { light.setSelected(true); }\n"
        "private void rebuildHeartbeatLights(Object model) { }\n"
        "private void refreshHeartbeatSelection() { child.setSelected(true); }\n"
        "private void applyHeartbeatSelectionAccessibility(Object model) { }\n"
        "private void unrelated() {\n"
        "  HeartbeatSelectionAccessibilityPolicy.CollectionDecision d = HeartbeatSelectionAccessibilityPolicy.fromModel(model, selectedId);\n"
        "  heartbeatLights.setAccessibilityDelegate(delegate);\n"
        "  AccessibilityNodeInfo.CollectionInfo.obtain(d.rowCount, d.columnCount, false, AccessibilityNodeInfo.CollectionInfo.SELECTION_MODE_SINGLE);\n"
        "  AccessibilityNodeInfo.CollectionItemInfo.obtain(item.rowIndex, 1, item.columnIndex, 1, false, item.selected);\n"
        "  boolean selected = item.selected;\n"
        "}"
    )
    result = classify(wrong_method)
    assert result["nativePersistentSelection"]["status"] == "PARTIAL_UNSAFE"

    capability = result["capability"]
    assert result["schema"] == "try-forever-heartbeat-selection-owner-probe.v2"
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

    print("Heartbeat persistent-selection owner lifecycle evidence boundaries: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
