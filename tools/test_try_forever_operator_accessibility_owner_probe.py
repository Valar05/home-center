from try_forever_operator_accessibility_owner_probe import probe


def complete_deep_detail_wiring() -> str:
    return """
private long heartbeatDetailPresentationGeneration;

private void createOverlay() {
    int height = HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
    heartbeatDetail.setVerticalScrollBarEnabled(true);
    heartbeatDetail.setMovementMethod(ScrollingMovementMethod.getInstance());
    heartbeatDetail.setFocusable(presentation.keyboardFocusable);
    heartbeatDetail.setClickable(presentation.clickable);
    heartbeatDetail.setLongClickable(presentation.longClickable);
}

private void showHeartbeatDetail(String detail, boolean explicitSelection) {
    HeartbeatDetailSurfacePolicy.Presentation presentation =
            HeartbeatDetailSurfacePolicy.fromDetail(detail);
    if (presentation.verticallyScrollable) {
        heartbeatDetail.setMovementMethod(ScrollingMovementMethod.getInstance());
    }
    heartbeatDetail.setFocusable(presentation.keyboardFocusable);
    heartbeatDetail.setClickable(presentation.clickable);
    heartbeatDetail.setLongClickable(presentation.longClickable);
    if (explicitSelection) {
        heartbeatDetail.scrollTo(0, 0);
        heartbeatDetail.announceForAccessibility(presentation.contentDescription);
    } else {
        restoreHeartbeatDetailScrollAfterLayout(oldY, generation);
    }
}

private void restoreHeartbeatDetailScrollAfterLayout(int oldY, long presentationGeneration) {
    if (presentationGeneration != heartbeatDetailPresentationGeneration) return;
    HeartbeatDetailSurfacePolicy.clampScrollY(oldY, contentHeight, viewportHeight);
}
"""


def complete_spotify_wiring() -> str:
    return """
private void handleSpotifyReceipt(long requestId, String receiptJson) {
    String announcement = HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
    spotifyStatus.announceForAccessibility(announcement);
}
"""


def test_current_legacy_shapes_are_classified_without_promoting_runtime():
    source = """
private void createOverlay() {
    heartbeatDetail.setMaxLines(5);
    heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);
}
private void handleSpotifyReceipt(long requestId, String receiptJson) {
    String announcement = summary.length() > 160 ? summary.substring(0, 160) : summary;
}
"""
    result = probe(source)
    assert result["schema"] == "try-forever-operator-accessibility-owner-probe.v4"
    assert result["evidenceClass"] == "JAVA_METHOD_SCOPED_LEXICAL_CODE_SURFACE"
    assert result["deepDetail"]["status"] == "LEGACY_OWNER"
    assert result["spotifyAnnouncement"]["status"] == "LEGACY_OWNER"
    assert result["capabilityBoundary"] == {
        "sourceInspected": True,
        "lexicalLiteralsExcluded": True,
        "methodScopedSource": True,
        "controlFlowProven": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivery": False,
        "p0Mutation": False,
    }


def test_complete_existing_organ_markers_in_owning_methods_classify_source_wired():
    source = complete_deep_detail_wiring() + complete_spotify_wiring()
    result = probe(source)
    assert result["deepDetail"]["status"] == "SOURCE_WIRED"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"


def test_complete_markers_in_wrong_methods_must_not_earn_source_wired():
    source = """
private void createOverlay() {
    heartbeatDetail.setText("legacy-free but not wired");
}
private void handleSpotifyReceipt(long requestId, String receiptJson) {
    spotifyStatus.setText(summary);
}
private void counterfeitRepair() {
    HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
    heartbeatDetail.setVerticalScrollBarEnabled(true);
    heartbeatDetail.setMovementMethod(ScrollingMovementMethod.getInstance());
    heartbeatDetail.setFocusable(presentation.keyboardFocusable);
    heartbeatDetail.setClickable(presentation.clickable);
    heartbeatDetail.setLongClickable(presentation.longClickable);
    HeartbeatDetailSurfacePolicy.fromDetail(detail);
    presentation.verticallyScrollable.toString();
    presentation.keyboardFocusable.toString();
    presentation.clickable.toString();
    presentation.longClickable.toString();
    restoreHeartbeatDetailScrollAfterLayout(oldY, generation);
    heartbeatDetail.scrollTo(0, 0);
    heartbeatDetail.announceForAccessibility(presentation.contentDescription);
    HeartbeatDetailSurfacePolicy.clampScrollY(oldY, contentHeight, viewportHeight);
    HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
}
private long heartbeatDetailPresentationGeneration;
"""
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"
    assert all(
        not marker.startswith("counterfeitRepair::")
        for marker in result["deepDetail"]["wired_markers"]
    )


def test_comment_and_literal_only_owner_methods_must_not_earn_source_wired():
    source = r'''
// private void createOverlay() {
//   HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
// }
/*
private void showHeartbeatDetail(String detail, boolean explicitSelection) {
    HeartbeatDetailSurfacePolicy.fromDetail(detail);
    restoreHeartbeatDetailScrollAfterLayout(oldY, generation);
}
private void handleSpotifyReceipt(long requestId, String receiptJson) {
    HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
}
*/
String counterfeit = "private void handleSpotifyReceipt() { HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160); }";
String textBlock = """
private void createOverlay() {
    heartbeatDetail.setMovementMethod(ScrollingMovementMethod.getInstance());
}
""";
'''
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["deepDetail"]["wired_markers"] == ()
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["wired_markers"] == ()


def test_legacy_markers_in_unrelated_method_do_not_poison_complete_owner_wiring():
    source = complete_deep_detail_wiring() + complete_spotify_wiring() + """
private void historicalExample() {
    heartbeatDetail.setMaxLines(5);
    heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);
    summary.substring(0, 160);
}
"""
    result = probe(source)
    assert result["deepDetail"]["status"] == "SOURCE_WIRED"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"


def test_detail_policy_without_native_owner_lifecycle_is_partial_unsafe():
    source = """
private long heartbeatDetailPresentationGeneration;
private void createOverlay() {
    HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
}
private void showHeartbeatDetail(String detail, boolean explicitSelection) {
    HeartbeatDetailSurfacePolicy.fromDetail(detail);
}
"""
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"


def test_partial_owner_surgery_fails_closed():
    source = complete_deep_detail_wiring() + complete_spotify_wiring()
    source = source.replace(
        "private void createOverlay() {",
        "private void createOverlay() {\n    heartbeatDetail.setMaxLines(5);",
        1,
    )
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"


def test_spotify_legacy_and_new_budget_markers_together_in_owner_method_are_partial_unsafe():
    source = """
private void handleSpotifyReceipt(long requestId, String receiptJson) {
    String oldValue = summary.substring(0, 160);
    String newValue = HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
}
"""
    result = probe(source)
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"
