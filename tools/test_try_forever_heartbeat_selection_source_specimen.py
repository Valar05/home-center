#!/usr/bin/env python3

from pathlib import Path


SPECIMEN = Path("docs/try-forever/heartbeat-skill-lights-source-specimen.html")


def main() -> int:
    source = SPECIMEN.read_text(encoding="utf-8")

    assert 'role="radiogroup"' in source
    assert 'role="radio"' in source
    assert 'aria-checked="true"' in source
    assert 'aria-checked="false"' in source
    assert 'tabindex="0"' in source
    assert 'tabindex="-1"' in source
    assert "ArrowRight" in source and "ArrowLeft" in source
    assert "ArrowDown" in source and "ArrowUp" in source
    assert "Home" in source and "End" in source
    assert "textContent" in source
    assert "replaceChildren" in source
    assert "prefers-reduced-motion" in source
    assert "SOURCE ONLY" in source
    assert "PHONE" in source

    # Persistent one-of-many selection must never regress to toggle semantics.
    assert "aria-pressed" not in source
    assert "innerHTML" not in source

    print("Heartbeat source specimen persistent-selection semantics: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
