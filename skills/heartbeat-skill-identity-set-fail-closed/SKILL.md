# Heartbeat Skill Identity Set Fail Closed

## Purpose

Keep one case-insensitive repository-skill owner key from authorizing more than one candidate path. The current provenance owner already uses case-insensitive identity semantics; therefore a collision is a **set-level ambiguity**, not a contest where arrival order may pick a winner.

## Existing owner

`tools/try_forever_skill_provenance_probe.py` remains the sole provenance owner. `tools/try_forever_skill_identity_set.py` is a pure policy helper only. Do not create a second probe, registry, controller, scheduler, recovery daemon, phone lane, or P0 owner.

## Authority law

1. Candidate traversal/count/topology gates run first.
2. After the existing root gate, derive repository-relative candidate identities.
3. Group them by the existing case-insensitive owner key.
4. If any owner key maps to more than one distinct repository path, reject the **entire direct-skill authority set before title/hash work**.
5. Never use first-wins, last-wins, path order, title quality, hash success, or later per-file failure to select a winner from an ambiguous owner set.
6. Exact duplicate observations of the same repository path are not a second identity.

## Accessibility / operator truth

Operator-facing state should say `IDENTITY SET AMBIGUOUS` / `AUTHORITY BLOCKED`, with non-color semantics. Do not dump every path into routine speech; explicit detail may show bounded related paths. Repository identity bookkeeping earns no focus movement or decorative Christmas motion.

## Evidence membrane

A pure helper, hostile regression source, patch artifact, GitHub commit, or PR review is source evidence only. Preserve `requested → implemented source → owner source wired → tested → runtime → deployed → callable → executed → delivered → accepted` separately.

## P0 / phone firewall

This skill owns no Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance work. P0 remains read-only evidence here.

## Current capability state

- Pure identity-set policy source: **YES**
- Hostile policy regression source: **YES**
- Exact existing-owner patch provenance: **YES / PROPOSED_NOT_APPLIED**
- Existing owner consumes global fail-closed identity-set gate: **NO**
- TESTED: **NO**
- Runtime UI/TalkBack: **NO**
- Deployed/callable/executed/delivered/accepted: **NO**
