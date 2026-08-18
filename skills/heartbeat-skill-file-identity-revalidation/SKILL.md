# Heartbeat Skill File Identity Revalidation

## Purpose

Detect persistent candidate-file replacement or mutation between `SKILL.md` admission and per-file repository-skill authority without pretending portable path revalidation is an atomic file binding.

This skill owns source/evidence policy only. It owns no renderer, scheduler, phone lane, Phone Hands surface, P0 recovery chain, skill registry daemon, deployment path, or physical acceptance action.

## Trigger

Use after a named `SKILL.md` has passed the separate no-follow ordinary-file candidate topology gate but before treating title/hash evidence as authority. It lights when one admitted candidate can change identity or material stat observation while discovery is in progress.

## Canonical helper

`tools/try_forever_skill_file_identity.py`

The helper captures one no-follow `SkillFileIdentity` containing:

- device;
- inode/file-index component;
- file type;
- size;
- nanosecond mtime when available;
- symlink/junction redirector classification reused from the existing root-identity organ.

`revalidate_skill_file_identity(before, after)` fails closed unless both observations describe the same ordinary file with a stable nonzero inode/file-index and unchanged size/mtime observation.

## Verdicts

- `STABLE` — the same no-follow device/inode and size/mtime observation bracketed the checked work.
- `REDIRECTOR_BLOCKED` — the admitted candidate observation itself is a symlink/junction redirector.
- `FILE_CHANGED` — file type, redirector state, device/inode identity, size, or mtime changed between observations.
- `IDENTITY_UNAVAILABLE` — the platform observation does not expose a usable inode/file-index token.

Only `STABLE` is eligible to continue toward repository-skill authority.

## Atomicity boundary

`STABLE` is an observation verdict, **not** an atomic file-handle claim.

Portable no-follow stat revalidation can detect persistent replacement and common in-place mutation. It does not prove absence of:

- swap-and-restore races entirely between observations;
- inode/file-index reuse;
- same-size/same-mtime content rewrites;
- replacement after the final observation;
- title/hash reads being bound to one immutable file handle on every platform.

Do not rename `STABLE` to `ATOMIC`, `BOUND`, or `SAFE_TOCTOU` without platform-specific evidence and owner integration that actually earns that claim.

## Composition

The intended authority order is:

`repository-owned skills root -> bounded traversal -> no-follow ordinary SKILL.md candidate -> bounded candidate set -> candidate-file identity observation -> path/collision checks -> bounded title -> exact bounded whole-file SHA -> candidate-file identity revalidation -> stable repository snapshot`

The exact placement may be strengthened by future handle-bound platform code, but no second provenance probe may be created. Compose into the existing `tools/try_forever_skill_provenance_probe.py` owner.

## Regression source

`tools/test_try_forever_skill_file_identity.py` pins:

- stable ordinary-file observation;
- named file-symlink redirector rejection;
- replacement with a new file object;
- in-place size/mtime drift;
- missing inode/file-index fail-closed behavior;
- explicit refusal to describe equal observations as atomic binding.

These are regression **sources** until an authorized runner produces test evidence.

## Owner capability state

At the 2026-08-18 1300 heartbeat:

- helper source: **YES**;
- regression source: **YES**;
- exact GitHub readback: **YES**;
- existing provenance owner consumes helper: **NO**;
- existing static candidate topology patch: **PROPOSED_NOT_APPLIED**;
- probe executed: **NO**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

The static candidate-topology wound and this post-admission revalidation wound are related but not interchangeable. A no-follow directory-entry check does not prove the file stayed the same afterward.

## P0 / phone firewall

Do not consume or mutate Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance. If a P0 issue is discovered incidentally, record one concise finding for the canonical P0 owner and stop.

## Done

This skill lights only when candidate-file identity/revalidation truth materially changes. If owner wiring, atomicity, or test evidence has not changed, do not decorate the heartbeat with it.
