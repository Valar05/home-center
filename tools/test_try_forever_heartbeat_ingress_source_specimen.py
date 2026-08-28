#!/usr/bin/env python3
"""SOURCE / UNEXECUTED accessibility contract for the existing ingress Warm Wall."""

from pathlib import Path


SPECIMEN = Path("docs/try-forever/heartbeat-ingress-separation-source-specimen.html")


def main() -> int:
    source = SPECIMEN.read_text(encoding="utf-8")

    assert "SOURCE ONLY — NOT OPERATOR-OVERLAY RUNTIME PROOF" in source
    assert "role=\"status\"" in source
    assert "aria-live=\"polite\"" in source
    assert "button { min-height: 56px" in source
    assert "button:focus-visible" in source
    assert "prefers-reduced-motion: reduce" in source
    assert "role=\"img\"" in source
    assert "<title id=\"wire-title\">" in source
    assert "<desc id=\"wire-desc\">" in source
    assert "data-mode=\"sourcework\"" in source
    assert "data-mode=\"preparse\"" in source
    assert "4,096" in source
    assert "320" in source
    assert "PROPOSED_NOT_APPLIED" in source
    assert "Runtime TalkBack remains unproven" in source
    assert "setInterval(" not in source
    assert "animation: infinite" not in source

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
