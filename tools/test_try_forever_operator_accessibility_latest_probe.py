from try_forever_operator_accessibility_owner_probe import probe


def owner_class(body: str) -> str:
    return "public class OperatorOverlayService extends Service {\n" + body + "\n}\n"


def latest_owner(description_line: str, refresh_description_line: str = "") -> str:
    return owner_class(
        f"""
private void createOverlay() {{
    latest = textView(14f, false);
    latest.setText(OperatorState.latestText(this));
    {description_line}
    latest.setOnClickListener(v -> expandedText = !expandedText);
}}
private void refreshUi() {{
    latest.setText(OperatorState.latestText(this));
    {refresh_description_line}
}}
"""
    )


def test_static_latest_description_is_legacy_owner_semantics() -> None:
    result = probe(latest_owner(
        'latest.setContentDescription("Latest Home Center or Adam message. Tap to expand or collapse text.");'
    ))
    assert result["latestMessageFocus"]["status"] == "LEGACY_OWNER"
    assert result["capabilityBoundary"]["runtimeTalkBack"] is False


def test_native_latest_text_semantics_are_source_wired() -> None:
    result = probe(latest_owner("latest.setContentDescription(null);"))
    assert result["latestMessageFocus"]["status"] == "SOURCE_WIRED"


def test_later_non_null_latest_override_fails_closed() -> None:
    result = probe(latest_owner(
        "latest.setContentDescription(null);",
        'latest.setContentDescription("Newest message");',
    ))
    assert result["latestMessageFocus"]["status"] == "PARTIAL_UNSAFE"


def test_missing_latest_refresh_ownership_is_partial_unsafe() -> None:
    source = owner_class(
        """
private void createOverlay() {
    latest = textView(14f, false);
    latest.setText(OperatorState.latestText(this));
    latest.setContentDescription(null);
    latest.setOnClickListener(v -> expandedText = !expandedText);
}
private void refreshUi() {
    status.setText(state);
}
"""
    )
    result = probe(source)
    assert result["latestMessageFocus"]["status"] == "PARTIAL_UNSAFE"
