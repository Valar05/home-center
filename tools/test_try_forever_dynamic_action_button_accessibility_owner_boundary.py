from __future__ import annotations

from pathlib import Path

from tools.try_forever_operator_accessibility_owner_probe import (
    java_lexical_code_surface,
    java_named_class_surface,
    java_private_void_method_surface,
)


OWNER = Path(
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
)


def _top_level_method_body(method_surface: str) -> str:
    """Keep only direct method-body statements; blank nested blocks.

    This is intentionally narrower than Java control-flow proof. It prevents an obvious
    source-evidence counterfeit where expected semantic writes are buried under a nested
    branch that cannot establish the owner's direct refresh contract. Runtime/TalkBack
    behavior remains unproven.
    """
    open_brace = method_surface.find("{")
    if open_brace < 0:
        return ""
    out: list[str] = []
    depth = 0
    for char in method_surface[open_brace + 1 :]:
        if char == "{":
            depth += 1
            out.append(" ")
            continue
        if char == "}":
            if depth == 0:
                break
            depth -= 1
            out.append(" ")
            continue
        if depth == 0:
            out.append(char)
        else:
            out.append("\n" if char == "\n" else " ")
    return "".join(out)


def _refresh_ui_method_surface(source: str | None = None) -> str:
    source_text = OWNER.read_text(encoding="utf-8") if source is None else source
    code_surface = java_lexical_code_surface(source_text)
    owner = java_named_class_surface(code_surface, "OperatorOverlayService")
    assert owner, "missing named OperatorOverlayService class"
    refresh_ui = java_private_void_method_surface(owner, "refreshUi")
    assert refresh_ui, "missing direct owner method: refreshUi"
    return refresh_ui


def _refresh_ui_surface(source: str | None = None) -> str:
    return _top_level_method_body(_refresh_ui_method_surface(source))


def test_full_text_action_buttons_expose_the_exact_current_action() -> None:
    refresh_ui = _refresh_ui_surface()

    assert 'muteButton.setText(muted ? "Unmute speech" : "Mute speech");' in refresh_ui
    assert 'muteButton.setContentDescription(muted ? "Unmute speech" : "Mute speech");' in refresh_ui, (
        "ACCESSIBILITY WOUND: muteButton text changes with the current action while its "
        "semantic description remains generic"
    )

    assert "controlButton.setText(fullControlLabel);" in refresh_ui
    assert "controlButton.setContentDescription(fullControlLabel);" in refresh_ui, (
        "ACCESSIBILITY WOUND: full control action changes among Enable, Disable, and "
        "Confirm disable while its semantic description remains generic"
    )


def test_compact_control_button_exposes_exact_full_current_action() -> None:
    refresh_ui = _refresh_ui_surface()
    full_method = _refresh_ui_method_surface()

    assert "compactControlButton.setText(compactControlLabel);" in refresh_ui
    assert "compactControlButton.setContentDescription(fullControlLabel);" in refresh_ui, (
        "ACCESSIBILITY WOUND: compact STOP/ENABLE/CONFIRM text needs the exact full "
        "current action as its semantic description"
    )
    assert 'fullControlLabel = "Confirm disable";' in full_method, (
        "SAFETY REGRESSION: confirm-disable must remain a distinct action state"
    )


def test_nested_counterfeit_semantic_writes_do_not_satisfy_direct_refresh_evidence() -> None:
    counterfeit = """
public class OperatorOverlayService {
    private void refreshUi() {
        boolean muted = false;
        String fullControlLabel = "Disable control";
        String compactControlLabel = "STOP";
        muteButton.setText(muted ? "Unmute speech" : "Mute speech");
        controlButton.setText(fullControlLabel);
        compactControlButton.setText(compactControlLabel);
        if (muted && !muted) {
            muteButton.setContentDescription(muted ? "Unmute speech" : "Mute speech");
            controlButton.setContentDescription(fullControlLabel);
            compactControlButton.setContentDescription(fullControlLabel);
        }
    }
}
"""
    refresh_ui = _refresh_ui_surface(counterfeit)
    assert "muteButton.setContentDescription" not in refresh_ui
    assert "controlButton.setContentDescription" not in refresh_ui
    assert "compactControlButton.setContentDescription" not in refresh_ui


def test_source_evidence_does_not_claim_runtime_execution() -> None:
    # This fixture intentionally proves only the direct owner source shape. It does not
    # execute Android, inspect TalkBack output, deploy an APK, or touch the phone/P0 chain.
    assert OWNER.as_posix().endswith("OperatorOverlayService.java")
