#!/usr/bin/env python3
"""RED source regression for persistent heartbeat selection doctrine convergence.

Repository-source evidence only. This does not execute Android, exercise TalkBack,
render the overlay, or touch the phone/P0 chain.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BROAD = ROOT / "skills" / "heartbeat-skill-lights" / "SKILL.md"
SELECTION = ROOT / "skills" / "persistent-selection-semantics" / "SKILL.md"
NATIVE = ROOT / "skills" / "heartbeat-native-selection-collection" / "SKILL.md"
SPECIMEN = ROOT / "docs" / "try-forever" / "heartbeat-skill-lights-source-specimen.html"


def main() -> int:
    broad = BROAD.read_text(encoding="utf-8")
    selection = SELECTION.read_text(encoding="utf-8")
    native = NATIVE.read_text(encoding="utf-8")
    specimen = SPECIMEN.read_text(encoding="utf-8")

    stale_permission = (
        "Persistent selection of one light controlling a shared always-present detail surface "
        "uses selection semantics such as `aria-pressed`"
    )
    assert stale_permission not in broad, (
        "broad heartbeat doctrine still permits toggle-shaped aria-pressed semantics for a "
        "persistent one-of-many selection"
    )

    assert "`PERSISTENT ONE-OF-MANY ≠ TOGGLE`" in native
    assert "radio-style contract" in selection
    assert 'role="radiogroup"' in specimen
    assert 'role="radio"' in specimen
    assert 'aria-checked="true"' in specimen
    assert "aria-pressed" not in specimen

    print("Heartbeat persistent-selection doctrine converged on radio semantics: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
