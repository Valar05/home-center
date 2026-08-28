#!/usr/bin/env python3
"""Source-only truth fixture for the Adam accessibility Warm Wall.

This fixture checks only repository specimen truth. It does not render a browser, execute Android,
exercise TalkBack, touch Phone/P0, or promote source into TESTED/runtime capability.
"""

from pathlib import Path


WALL = Path("docs/try-forever/adam-mode-accessibility-warm-wall-source.html")


def main() -> int:
    source = WALL.read_text(encoding="utf-8")

    # The wall must not green-paint the known lifecycle-ordering evidence gap.
    assert "SEND ACTION PROBE v10 △ EVIDENCE REVISE REQUIRED / RED SOURCE / UNEXECUTED" in source
    assert "SEND ACTION PROBE v10 △ SOURCE REPAIRED / UNEXECUTED" not in source
    assert "SEND ACTION PROBE v10 — EVIDENCE REVISE REQUIRED / RED SOURCE / UNEXECUTED" in source

    # Automatic changing detail stays explicitly non-live; no implicit status-region chatter.
    assert 'id="detail" role="note" aria-live="off"' in source
    assert 'role="status"' not in source

    # Horizontal 1x5 visual topology stays non-wrapping and scrollable at narrow widths.
    assert "grid-template-columns: repeat(5,minmax(120px,1fr))" in source
    assert "overflow-x: auto" in source
    assert "repeat(auto-fit,minmax(120px,1fr))" not in source

    # Editable naming and invalid-vs-unavailable semantics remain explicit.
    assert '<label for="request">Adam request</label>' in source
    assert 'aria-describedby="inputState"' in source
    assert "requestState === OVER_BUDGET ? 'true' : 'false'" in source

    # Repeat-contact and firewall truth remain visible without claiming runtime evidence.
    assert "REPEAT SEND CONTRACT — SUPPORTING SOURCE WIRED" in source
    assert "PHONE/P0 UNTOUCHED" in source
    assert "RUNTIME TALKBACK ×" in source

    print("Adam Warm Wall source-truth fixture: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
