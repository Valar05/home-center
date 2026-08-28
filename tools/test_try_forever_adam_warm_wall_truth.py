#!/usr/bin/env python3
"""Source-only truth fixture for the Adam accessibility Warm Wall.

This fixture checks only repository specimen truth. It does not render a browser, execute Android,
exercise TalkBack, touch Phone/P0, or promote source into TESTED/runtime capability.
"""

from pathlib import Path


WALL = Path("docs/try-forever/adam-mode-accessibility-warm-wall-source.html")


def main() -> int:
    source = WALL.read_text(encoding="utf-8")

    # The wall must track current probe evidence without stale green labels.
    assert "REQUEST PROBE v11 △ SOURCE REPAIRED / UNEXECUTED" in source
    assert "SEND ACTION PROBE v11 △ EVIDENCE REVISE REQUIRED / RED SOURCE / UNEXECUTED" in source
    assert "SEND ACTION PROBE v11 △ SOURCE REPAIRED / UNEXECUTED" not in source
    assert "local declarations named <code>adamSendButton</code> or <code>adamMode</code>" in source

    # The dynamic Send action must expose current contextual reason without live-region chatter.
    assert '<button id="send" type="button" aria-describedby="inputState">Send</button>' in source
    assert "SEND ACTION CONTEXT — SOURCE WIRED" in source
    assert "send.setAttribute('aria-label', `Send request to Adam using ${label} mode`)" in source
    assert 'id="inputState" aria-live="off"' in source

    # Automatic changing detail stays explicitly non-live; no implicit status-region chatter.
    assert 'id="detail" role="note" aria-live="off"' in source
    assert 'role="status"' not in source

    # Horizontal 1x5 visual topology stays non-wrapping and scrollable at narrow widths.
    assert "grid-template-columns: repeat(5,minmax(120px,1fr))" in source
    assert "overflow-x: auto" in source
    assert "repeat(auto-fit,minmax(120px,1fr))" not in source

    # Editable naming and invalid-vs-unavailable semantics remain explicit.
    assert '<label for="request">Adam request</label>' in source
    assert '<textarea id="request" rows="4" aria-describedby="inputState" aria-invalid="false"' in source
    assert "requestState === OVER_BUDGET ? 'true' : 'false'" in source

    # Repeat-contact and firewall truth remain visible without claiming runtime evidence.
    assert "REPEAT SEND CONTRACT — SUPPORTING SOURCE WIRED" in source
    assert "PHONE/P0 UNTOUCHED" in source
    assert "RUNTIME TALKBACK ×" in source

    print("Adam Warm Wall source-truth fixture v11 RED-send-evidence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
