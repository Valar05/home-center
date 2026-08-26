#!/usr/bin/env python3
"""Source-only accessibility regression for the owner-surgery backend Warm Wall.

This fixture validates repository source structure only. It does not prove browser runtime,
TalkBack behavior, Android deployment, phone delivery, or acceptance.
"""

from pathlib import Path


SPECIMEN = Path("docs/try-forever/operator-owner-surgery-backend-selection-source-specimen.html")


def main() -> int:
    html = SPECIMEN.read_text(encoding="utf-8")

    # Native interaction and touch geometry stay first-class rather than simulated div controls.
    assert '<fieldset aria-describedby="detail">' in html
    assert html.count('input type="radio" name="backend"') >= 15
    assert "min-height: 56px" in html
    assert "label:focus-within" in html

    # State changes remain available to assistive technology without relying on color alone.
    assert 'id="detail" role="status" aria-live="polite"' in html
    assert "non-color" in html.lower()
    assert 'role="img" aria-labelledby="diagram-title diagram-desc"' in html
    assert '<title id="diagram-title">' in html
    assert '<desc id="diagram-desc">' in html

    # Machine-control and semantic source throats are inspectable without claiming runtime behavior.
    assert "BOUNDED CONTROL THROATS: SOURCE_WIRED" in html
    assert 'value="bounded-controls"' in html
    assert "finite source ceilings" in html
    assert "Accepted text is preserved exactly" in html
    assert "SEMANTIC RESOURCE THROATS: SOURCE_WIRED" in html
    assert 'value="semantic-throats"' in html
    assert "Content remains capped at one MiB" in html
    assert "SHA length is checked before regex" in html

    # Bounded bytes are not misreported as proof that semantic JSON decoding cannot exhaust nesting.
    assert "DEEP-JSON FAILURE CONTAINMENT: SOURCE_WIRED" in html
    assert 'value="semantic-nesting"' in html
    assert "DEEP JSON → TYPED STOP" in html
    assert "Raw RecursionError is converted into OwnerSurgerySemanticError" in html
    assert "exact evidence is not rewritten" in html.lower()

    # Exact source evidence and human-facing rejection prose remain separate ownership classes.
    assert "SEMANTIC DIAGNOSTIC PROJECTION: SOURCE_WIRED" in html
    assert 'value="diagnostics"' in html
    assert "DIAGNOSTIC PROJECTION ≠ EVIDENCE" in html
    assert "bounded ASCII-safe projection" in html
    assert "projected prose never feeds authority" in html

    # Failure evidence is now source-wired without changing the fail-closed authority law.
    assert "DESCRIPTOR FAILURE-EVIDENCE PARITY: SOURCE_WIRED" in html
    assert 'value="failure-parity"' in html
    assert "CONTACT PRESERVATION: SOURCE_WIRED" in html
    assert "CONTACT PRESERVATION / SOURCE_WIRED" in html
    assert "bounded observed-work counts" in html
    assert "artifact path/kind" in html
    assert "No partial surgery authority survives" in html
    assert "Regression execution: NO" in html
    assert "TESTED: NO" in html

    # Reduced-motion and no-casino constraints remain explicit source laws.
    assert "prefers-reduced-motion: reduce" in html
    assert "animation: none !important" in html
    assert "CHRISTMAS BLINK: NO" in html
    assert "<blink" not in html.lower()
    assert "requestAnimationFrame" not in html
    assert "setInterval" not in html
    assert "autoplay" not in html.lower()

    # Current evidence/capability state must stay visible on the source wall.
    assert "DIRECT DESCRIPTOR ROOT GATE: SOURCE_WIRED" in html
    assert "ROOT PATH-ENCODING CONTAINMENT: SOURCE_WIRED" in html
    assert "REGRESSIONS: UNEXECUTED" in html
    assert "RUNTIME TALKBACK: NO" in html
    assert "PHONE/P0: UNTOUCHED" in html

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
