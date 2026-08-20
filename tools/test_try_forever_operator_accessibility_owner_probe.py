from try_forever_operator_accessibility_owner_probe import probe


def owner_class(body: str) -> str:
    return "public class OperatorOverlayService extends Service {\n" + body + "\n}\n"


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
    long presentationGeneration = ++heartbeatDetailPresentationGeneration;
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
private void createOverlay() {
    String currentSpotifySummary = OperatorState.spotifySummary(this);
    spotifyStatus.setText(currentSpotifySummary);
    spotifyStatus.setContentDescription(
            HeartbeatPlainTextBudget.boundedWithEllipsis(currentSpotifySummary, 160));
}

private void handleSpotifyReceipt(long requestId, String receiptJson) {
    spotifyStatus.setContentDescription(
            HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160));
    String announcement = HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
    spotifyStatus.announceForAccessibility(announcement);
}
"""


def test_current_legacy_shapes_are_classified_without_promoting_runtime():
    source = owner_class("""
private void createOverlay() {
    heartbeatDetail.setMaxLines(5);
    heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);
    spotifyStatus.setContentDescription("Current Spotify playback status");
}
private void handleSpotifyReceipt(long requestId, String receiptJson) {
    String announcement = summary.length() > 160 ? summary.substring(0, 160) : summary;
}
""")
    result = probe(source)
    assert result["schema"] == "try-forever-operator-accessibility-owner-probe.v5"
    assert result["evidenceClass"] == "JAVA_DIRECT_OWNER_METHOD_SCOPED_LEXICAL_CODE_SURFACE"
    assert result["ownerClassFound"] is True
    assert result["deepDetail"]["status"] == "LEGACY_OWNER"
    assert result["spotifyAnnouncement"]["status"] == "LEGACY_OWNER"
    assert result["spotifyStatusFocus"]["status"] == "LEGACY_OWNER"
    assert result["capabilityBoundary"] == {
        "sourceInspected": True,
        "lexicalLiteralsExcluded": True,
        "ownerClassScoped": True,
        "directMethodScopedSource": True,
        "controlFlowProven": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivery": False,
        "p0Mutation": False,
    }


def test_complete_existing_organ_markers_in_direct_owner_methods_classify_source_wired():
    source = owner_class(complete_deep_detail_wiring() + complete_spotify_wiring())
    result = probe(source)
    assert result["deepDetail"]["status"] == "SOURCE_WIRED"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"
    assert result["spotifyStatusFocus"]["status"] == "SOURCE_WIRED"


def test_complete_markers_in_wrong_methods_must_not_earn_source_wired():
    source = owner_class("""
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
    long presentationGeneration = ++heartbeatDetailPresentationGeneration;
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
    spotifyStatus.setContentDescription("counterfeit");
}
private long heartbeatDetailPresentationGeneration;
""")
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyStatusFocus"]["status"] == "PARTIAL_UNSAFE"


def test_nested_class_owner_method_counterfeit_must_not_earn_source_wired():
    source = owner_class("""
private void createOverlay() {
    heartbeatDetail.setText("direct owner still unwired");
}
private void handleSpotifyReceipt(long requestId, String receiptJson) {
    spotifyStatus.setText(summary);
}

private static final class CounterfeitOwner {
    private void createOverlay() {
        HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
        heartbeatDetail.setVerticalScrollBarEnabled(true);
        heartbeatDetail.setMovementMethod(ScrollingMovementMethod.getInstance());
        heartbeatDetail.setFocusable(presentation.keyboardFocusable);
        heartbeatDetail.setClickable(presentation.clickable);
        heartbeatDetail.setLongClickable(presentation.longClickable);
        String currentSpotifySummary = OperatorState.spotifySummary(this);
        spotifyStatus.setContentDescription(
                HeartbeatPlainTextBudget.boundedWithEllipsis(currentSpotifySummary, 160));
    }
    private void showHeartbeatDetail(String detail, boolean explicitSelection) {
        long presentationGeneration = ++heartbeatDetailPresentationGeneration;
        HeartbeatDetailSurfacePolicy.fromDetail(detail);
        presentation.verticallyScrollable.toString();
        presentation.keyboardFocusable.toString();
        presentation.clickable.toString();
        presentation.longClickable.toString();
        restoreHeartbeatDetailScrollAfterLayout(oldY, generation);
        heartbeatDetail.scrollTo(0, 0);
        heartbeatDetail.announceForAccessibility(presentation.contentDescription);
    }
    private void restoreHeartbeatDetailScrollAfterLayout(int oldY, long presentationGeneration) {
        if (presentationGeneration != heartbeatDetailPresentationGeneration) return;
        HeartbeatDetailSurfacePolicy.clampScrollY(oldY, contentHeight, viewportHeight);
    }
    private void handleSpotifyReceipt(long requestId, String receiptJson) {
        spotifyStatus.setContentDescription(
                HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160));
        HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
    }
}
""")
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyStatusFocus"]["status"] == "PARTIAL_UNSAFE"
    assert result["deepDetail"]["wired_markers"] == ()


def test_comment_and_literal_only_owner_methods_must_not_earn_source_wired():
    source = owner_class(r'''
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
''')
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["deepDetail"]["wired_markers"] == ()
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["wired_markers"] == ()
    assert result["spotifyStatusFocus"]["status"] == "PARTIAL_UNSAFE"


def test_legacy_markers_in_unrelated_method_do_not_poison_complete_owner_wiring():
    source = owner_class(complete_deep_detail_wiring() + complete_spotify_wiring() + """
private void historicalExample() {
    heartbeatDetail.setMaxLines(5);
    heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);
    summary.substring(0, 160);
    spotifyStatus.setContentDescription("Current Spotify playback status");
}
""")
    result = probe(source)
    assert result["deepDetail"]["status"] == "SOURCE_WIRED"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"
    assert result["spotifyStatusFocus"]["status"] == "SOURCE_WIRED"


def test_detail_policy_without_native_owner_lifecycle_is_partial_unsafe():
    source = owner_class("""
private long heartbeatDetailPresentationGeneration;
private void createOverlay() {
    HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
}
private void showHeartbeatDetail(String detail, boolean explicitSelection) {
    HeartbeatDetailSurfacePolicy.fromDetail(detail);
}
""")
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"


def test_partial_owner_surgery_fails_closed():
    body = complete_deep_detail_wiring() + complete_spotify_wiring()
    body = body.replace(
        "private void createOverlay() {",
        "private void createOverlay() {\n    heartbeatDetail.setMaxLines(5);",
        1,
    )
    result = probe(owner_class(body))
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"


def test_spotify_legacy_and_new_budget_markers_together_in_owner_method_are_partial_unsafe():
    source = owner_class("""
private void handleSpotifyReceipt(long requestId, String receiptJson) {
    String oldValue = summary.substring(0, 160);
    String newValue = HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
}
""")
    result = probe(source)
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"


def test_static_spotify_status_description_with_dynamic_announcement_is_still_focus_legacy():
    source = owner_class("""
private void createOverlay() {
    spotifyStatus.setContentDescription("Current Spotify playback status");
}
private void handleSpotifyReceipt(long requestId, String receiptJson) {
    HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
}
""")
    result = probe(source)
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"
    assert result["spotifyStatusFocus"]["status"] == "LEGACY_OWNER"


def test_missing_named_owner_class_fails_closed():
    result = probe("public class Counterfeit { private void createOverlay() {} }")
    assert result["ownerClassFound"] is False
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyStatusFocus"]["status"] == "PARTIAL_UNSAFE"
