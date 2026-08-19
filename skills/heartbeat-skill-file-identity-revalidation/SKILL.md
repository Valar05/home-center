# Heartbeat Skill File Identity Revalidation

## Purpose

Detect persistent candidate-file replacement or mutation between `SKILL.md` admission and per-file repository-skill authority without pretending portable path revalidation is an atomic file binding.

This skill owns source/evidence policy only. It owns no renderer, scheduler, phone lane, Phone Hands surface, P0 recovery chain, skill registry daemon, deployment path, or physical acceptance action.

## Trigger

Use after a named `SKILL.md` has passed the no-follow ordinary-file candidate topology gate but before treating title/hash evidence as authority. It lights when one admitted candidate can change identity or material stat observation while discovery is in progress.

## Canonical owner and helper

Existing owner: `tools/try_forever_skill_provenance_probe.py`

Helper: `tools/try_forever_skill_file_identity.py`

The helper captures one no-follow `SkillFileIdentity` containing device, inode/file-index component, file type, size, nanosecond mtime when available, and redirector classification reused from the existing root-identity organ.

`revalidate_skill_file_identity(before, after)` fails closed unless both observations describe the same ordinary file with a stable nonzero inode/file-index and unchanged size/mtime observation.

## Owner composition

The existing provenance owner now composes the policy directly:

`repository-owned skills root -> bounded traversal -> no-follow ordinary SKILL.md candidate -> bounded candidate set -> candidate-file identity observation -> path/collision checks -> bounded title -> exact bounded whole-file SHA -> candidate-file identity revalidation -> stable repository snapshot`

The candidate topology gate fails the whole discovery before title/hash authority if a named `SKILL.md` is a symlink/redirector or non-ordinary file at enumeration time. Post-admission identity failure rejects that candidate record with an explicit discovery error; it never appends the observed title/hash as repository-skill authority.

No second provenance probe, registry, controller, scheduler, phone path, or recovery owner is created.

## Verdicts

- `STABLE` — the same no-follow device/inode and size/mtime observation bracketed the checked work.
- `REDIRECTOR_BLOCKED` — the admitted candidate observation itself is a symlink/junction redirector.
- `FILE_CHANGED` — file type, redirector state, device/inode identity, size, or mtime changed between observations.
- `IDENTITY_UNAVAILABLE` — the platform observation does not expose a usable inode/file-index token.

Only `STABLE` is eligible to become a `SkillRecord`.

## Pre-I/O topology wound

The current owner still has a narrower degraded-operation gap between the initial no-follow identity observation and authority-facing content I/O:

1. capture candidate identity;
2. run containment logic;
3. open the named path in `markdown_title(...)` with ordinary path I/O;
4. open it again in `sha256_file(...)` with ordinary path I/O;
5. only then capture/revalidate identity again.

A candidate replaced after the first observation but before title/hash I/O can therefore be *rejected eventually* while the content I/O has already followed or waited on the replacement topology. That is insufficient for an authority lane whose finite-work contract must fail before reading a redirector/special file.

`tools/test_try_forever_skill_file_identity_integration.py` now contains the intentionally RED fixture `test_redirector_replacement_before_title_io_must_be_revalidated_before_any_content_open`. It replaces an admitted ordinary candidate with a symlink at the last existing pre-I/O seam and requires the owner to reject on identity/topology **before `markdown_title` or `sha256_file` is called**.

This fixture does not prescribe a second probe or a shadow reader. The repair belongs in the existing owner/file-identity path, for example by revalidating no-follow topology immediately before authority-facing content I/O or by later composing one handle-bound finite artifact observation. Any stronger handle-bound design must retain the declared atomicity boundary rather than claim universal filesystem immunity.

## Atomicity boundary

`STABLE` is an observation verdict, **not** an atomic file-handle claim.

Portable no-follow stat revalidation can detect persistent replacement and common in-place mutation. It does not prove absence of swap-and-restore races entirely between observations, inode/file-index reuse, same-size/same-mtime content rewrites, replacement after the final observation, or title/hash reads being bound to one immutable file handle on every platform.

The new pre-I/O RED fixture narrows one concrete work-admission wound; even after that fixture is repaired, do not rename `STABLE` to `ATOMIC`, `BOUND`, or `SAFE_TOCTOU` without platform-specific evidence and owner integration that actually earns that claim.

## Regression source

`tools/test_try_forever_skill_file_identity.py` pins the pure helper.

`tools/test_try_forever_skill_file_identity_integration.py` pins existing-owner source behavior for:

- stable ordinary candidate authority;
- named `SKILL.md` non-file topology rejection before title/hash work;
- file-symlink rejection without following the target when the platform supports symlinks;
- **RED / UNEXECUTED:** redirector replacement after initial identity admission must be rejected before any title/hash content I/O;
- replacement after hashing rejected before `SkillRecord` append; and
- identity-capture failure rejected before title/hash work.

These are regression **sources** until an authorized runner produces test evidence.

## Capability state — 2026-08-19 heartbeat

- helper source: **YES**;
- static no-follow candidate topology gate in existing owner: **YES / SOURCE_WIRED**;
- candidate-file identity bracket in existing owner: **YES / SOURCE_WIRED**;
- pre-I/O redirector/special-topology revalidation: **NO / RED REGRESSION SOURCE**;
- exact authenticated GitHub readback: **YES**;
- regression source: **YES / UNEXECUTED**;
- atomic cross-platform file binding: **NO**;
- probe executed by authorized runner: **NO**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall

Do not consume or mutate Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance. If a P0 issue is discovered incidentally, record one concise finding for the canonical P0 owner and stop.

## Done

This skill lights only when candidate-file identity/revalidation truth materially changes. Source wiring does not imply finite pre-I/O admission, atomicity, test passage, runtime delivery, or phone acceptance.
