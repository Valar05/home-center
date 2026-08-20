from try_forever_operator_accessibility_owner_probe import probe


def complete_deep_detail_wiring() -> str:
    return """
HeartbeatDetailSurfacePolicy.fromDetail(detail);
HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
HeartbeatDetailSurfacePolicy.clampScrollY(oldY, contentHeight, viewportHeight);
heartbeatDetail.setVerticalScrollBarEnabled(presentation.verticallyScrollable);
heartbeatDetail.setMovementMethod(
heartbeatDetail.setFocusable(presentation.keyboardFocusable);
heartbeatDetail.setClickable(presentation.clickable);
heartbeatDetail.setLongClickable(presentation.longClickable);
restoreHeartbeatDetailScrollAfterLayout(
heartbeatDetail.announceForAccessibility(presentation.contentDescription);
"""


def complete_spotify_wiring() -> str:
    return "HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);\n"


def test_current_legacy_shapes_are_classified_without_promoting_runtime():
    source = """
heartbeatDetail.setMaxLines(5);
heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);
String announcement = summary.length() > 160 ? summary.substring(0, 160) : summary;
"""
    result = probe(source)
    assert result["schema"] == "try-forever-operator-accessibility-owner-probe.v3"
    assert result["evidenceClass"] == "JAVA_LEXICAL_CODE_SURFACE"
    assert result["deepDetail"]["status"] == "LEGACY_OWNER"
    assert result["spotifyAnnouncement"]["status"] == "LEGACY_OWNER"
    assert result["capabilityBoundary"] == {
        "sourceInspected": True,
        "controlFlowProven": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivery": False,
        "p0Mutation": False,
    }


def test_complete_existing_organ_markers_classify_source_wired():
    source = complete_deep_detail_wiring() + complete_spotify_wiring()
    result = probe(source)
    assert result["deepDetail"]["status"] == "SOURCE_WIRED"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"


def test_comment_only_owner_markers_must_not_earn_source_wired():
    source = r'''
// HeartbeatDetailSurfacePolicy.fromDetail(detail);
// HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
/*
HeartbeatDetailSurfacePolicy.clampScrollY(oldY, contentHeight, viewportHeight);
heartbeatDetail.setVerticalScrollBarEnabled(presentation.verticallyScrollable);
heartbeatDetail.setMovementMethod(
heartbeatDetail.setFocusable(presentation.keyboardFocusable);
heartbeatDetail.setClickable(presentation.clickable);
heartbeatDetail.setLongClickable(presentation.longClickable);
restoreHeartbeatDetailScrollAfterLayout(
heartbeatDetail.announceForAccessibility(presentation.contentDescription);
HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
*/
String counterfeit = "HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160)";
String deepCounterfeit = "HeartbeatDetailSurfacePolicy.fromDetail";
String textBlock = """
HeartbeatDetailSurfacePolicy.fromDetail(detail);
HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
HeartbeatDetailSurfacePolicy.clampScrollY(oldY, contentHeight, viewportHeight);
heartbeatDetail.setVerticalScrollBarEnabled(presentation.verticallyScrollable);
heartbeatDetail.setMovementMethod(
heartbeatDetail.setFocusable(presentation.keyboardFocusable);
heartbeatDetail.setClickable(presentation.clickable);
heartbeatDetail.setLongClickable(presentation.longClickable);
restoreHeartbeatDetailScrollAfterLayout(
heartbeatDetail.announceForAccessibility(presentation.contentDescription);
HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
""";
'''
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["deepDetail"]["wired_markers"] == ()
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["wired_markers"] == ()


def test_commented_legacy_markers_do_not_poison_real_wiring():
    source = complete_deep_detail_wiring() + complete_spotify_wiring() + """
// heartbeatDetail.setMaxLines(5);
/* heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END); */
String oldSpotifyExample = "summary.substring(0, 160)";
"""
    result = probe(source)
    assert result["deepDetail"]["status"] == "SOURCE_WIRED"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"


def test_detail_policy_without_native_scroll_and_ownership_lifecycle_is_partial_unsafe():
    source = """
HeartbeatDetailSurfacePolicy.fromDetail(detail);
HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
HeartbeatDetailSurfacePolicy.clampScrollY(oldY, contentHeight, viewportHeight);
"""
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"


def test_partial_owner_surgery_fails_closed():
    source = """
heartbeatDetail.setMaxLines(5);
""" + complete_deep_detail_wiring() + complete_spotify_wiring()
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"


def test_spotify_legacy_and_new_budget_markers_together_are_partial_unsafe():
    source = """
summary.substring(0, 160)
HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160)
"""
    result = probe(source)
    assert result["spotifyAnnouncement"]["status"] == "PARTIAL_UNSAFE"
