from try_forever_operator_accessibility_owner_probe import probe


def test_current_legacy_shapes_are_classified_without_promoting_runtime():
    source = """
heartbeatDetail.setMaxLines(5);
heartbeatDetail.setEllipsize(TextUtils.TruncateAt.END);
String announcement = summary.length() > 160 ? summary.substring(0, 160) : summary;
"""
    result = probe(source)
    assert result["deepDetail"]["status"] == "LEGACY_OWNER"
    assert result["spotifyAnnouncement"]["status"] == "LEGACY_OWNER"
    assert result["capabilityBoundary"] == {
        "sourceInspected": True,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivery": False,
        "p0Mutation": False,
    }


def test_complete_existing_organ_markers_classify_source_wired():
    source = """
HeartbeatDetailSurfacePolicy.fromDetail(detail);
HeartbeatDetailSurfacePolicy.maxViewportHeightPx(lineHeight, padding);
HeartbeatDetailSurfacePolicy.clampScrollY(oldY, contentHeight, viewportHeight);
HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
"""
    result = probe(source)
    assert result["deepDetail"]["status"] == "SOURCE_WIRED"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"


def test_partial_owner_surgery_fails_closed():
    source = """
heartbeatDetail.setMaxLines(5);
HeartbeatDetailSurfacePolicy.fromDetail(detail);
HeartbeatPlainTextBudget.boundedWithEllipsis(summary, 160);
"""
    result = probe(source)
    assert result["deepDetail"]["status"] == "PARTIAL_UNSAFE"
    assert result["spotifyAnnouncement"]["status"] == "SOURCE_WIRED"
