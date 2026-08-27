#!/usr/bin/env python3
"""Source-only contract for the existing heartbeat predecode Warm Wall.

This fixture proves repository-source semantics only. It does not launch Android,
exercise TalkBack, deploy an overlay, consume Phone Hands, or touch the P0 chain.
"""

from pathlib import Path


SPECIMEN = Path("docs/try-forever/heartbeat-predecode-throat-source.html")


def main() -> int:
    text = SPECIMEN.read_text(encoding="utf-8")

    required = (
        'min-width: 56px; min-height: 56px;',
        'role="status" aria-live="polite"',
        'role="img" aria-labelledby="diagramTitle diagramDesc"',
        '@media (prefers-reduced-motion: reduce)',
        'DIRECT-STRING THROATS',
        'PARSE',
        'data-case="directString"',
        'data-case="parserPreparse"',
        'SOURCE_WIRED, not TESTED or runtime proof.',
        'RED / PROPOSED_NOT_APPLIED / UNEXECUTED',
        'Phone/P0 remains untouched',
    )
    missing = [needle for needle in required if needle not in text]
    if missing:
        raise AssertionError(f"predecode Warm Wall lost required source semantics: {missing}")

    forbidden = (
        'autoplay',
        'setInterval(',
        'setTimeout(',
        '@keyframes',
    )
    present = [needle for needle in forbidden if needle in text]
    if present:
        raise AssertionError(f"predecode Warm Wall gained forbidden motion/runtime behavior: {present}")

    print("heartbeat predecode Warm Wall source contract: PASS (source only; runtime/TalkBack unproven)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
