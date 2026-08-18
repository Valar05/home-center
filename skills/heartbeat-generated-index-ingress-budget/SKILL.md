# Heartbeat Generated Index Ingress Budget

## Purpose

Keep generated skill-index evidence bounded and non-authoritative at ingress. Generated indexes are discovery aids; malformed or oversized input must not abort the repository provenance probe or consume unbounded read/JSON work before becoming an `UNRESOLVED` verdict.

## Existing owner

`tools/try_forever_skill_provenance_probe.py::inspect_generated_index` remains the sole owner. Do not create another provenance probe, index daemon, registry, controller, scheduler, phone lane, or P0 owner.

## Required ingress contract

1. Open the supplied generated index as bytes.
2. Read no more than the declared byte budget plus one sentinel byte.
3. If max+1 is observed, return `UNRESOLVED` before UTF-8 decode or JSON authority.
4. Decode UTF-8 strictly. `UnicodeDecodeError` becomes bounded `UNRESOLVED` evidence, not an uncaught probe failure.
5. Parse JSON only after the byte + UTF-8 gates.
6. Preserve the existing freshness/HEAD/clean-tree verdict semantics for valid small input.

## Evidence law

Generated index content never substitutes for direct current-tree `skills/**/SKILL.md` existence, even when `VERIFIED_CURRENT`. A byte-budget pass means only “small enough to inspect”; it is not freshness, authority, test, runtime, or delivery evidence.

Do not truncate oversized index bytes into a plausible JSON prefix. Reject the whole generated-index observation.

## Accessibility / operator truth

Operator diagnostics should distinguish `INDEX OVERSIZED`, `INDEX UTF-8 INVALID`, and ordinary stale/unresolved evidence without relying on color. Routine speech should remain compact; raw hostile bytes are never spoken.

## P0 / phone firewall

This skill owns no Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance chain.

## Current capability state

- Doctrine/source: **YES**
- Exact existing-owner patch provenance: **YES / PROPOSED_NOT_APPLIED**
- Red hostile regression source: **YES**
- Existing owner consumes bounded byte/UTF-8 ingress: **NO**
- TESTED: **NO**
- Runtime/deployed/callable/executed/delivered/accepted: **NO**
