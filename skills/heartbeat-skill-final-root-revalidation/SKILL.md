# Heartbeat Skill Final Root Revalidation

## Purpose

Keep direct repository-skill authority bound to the same repository-owned `skills` root through the end of all per-file title/hash/file-identity work. Candidate-enumeration revalidation is necessary but not sufficient if later per-file work can outlive that root observation.

## Existing owner

`tools/try_forever_skill_provenance_probe.py` remains the sole provenance owner. Do not create a second probe, registry, controller, scheduler, recovery daemon, phone lane, or P0 owner.

## Required authority sequence

1. Capture the no-follow `skills` root identity before traversal.
2. Perform bounded traversal/candidate admission.
3. Revalidate the original root after enumeration before per-file authority work.
4. Reject any case-insensitive identity-set ambiguity before title/hash work.
5. For each candidate, keep the existing no-follow file-identity bracket around bounded title + exact bounded whole-file SHA.
6. **Before returning any gathered `SkillRecord`, capture and revalidate the original `skills` root one final time.**
7. If the final observation is unavailable or not `STABLE`, return zero `SkillRecord`s. Partial authority is forbidden.

## Evidence semantics

The final root gate detects observable persistent late replacement/type/redirector drift. It does **not** prove atomic cross-platform root binding, exclude swap-and-restore entirely between observations, or defeat identity-token reuse. Those remain separate open platform wounds.

Owner composition commit `8603d51710d5147a5a7163dce05d9a998cf88557` produced owner blob `51e6efdbcec03d044ab89f37213659252514856a`. A GitHub source write/readback is not TESTED/runtime/deployed/callable/executed/delivered/accepted evidence.

## Regression contract

Hostile source fixtures require three root observations for successful discovery: initial, after enumeration, and final after per-file authority work. Persistent late replacement or final identity-capture failure must reject all gathered records.

## Accessibility / operator truth

Operator-facing state should distinguish `FINAL ROOT STABLE` from `FINAL ROOT BLOCKED` without relying on color alone. Repository provenance bookkeeping does not earn automatic speech, focus movement, or decorative Christmas motion.

## P0 / phone firewall

This skill owns no Phone Hands, primary-phone execution, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance work. Any P0 finding is read-only evidence for the canonical P0 conductor.

## Current capability state

- Doctrine/source: **YES**
- Exact existing-owner patch provenance: **YES / APPLIED_SOURCE**
- Red hostile regression source: **YES**
- Existing owner consumes final root gate: **YES / SOURCE_WIRED**
- Exact authenticated owner readback: **YES**
- TESTED: **NO**
- Runtime UI/TalkBack: **NO**
- Deployed/callable/executed/delivered/accepted: **NO**
