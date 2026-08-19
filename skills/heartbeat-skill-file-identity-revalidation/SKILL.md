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

The existing provenance owner now composes:

`repository-owned skills root -> bounded traversal -> no-follow ordinary SKILL.md candidate -> bounded candidate set -> admitted candidate-file identity -> path/collision/containment checks -> pre-I/O candidate-file identity revalidation -> bounded title -> exact bounded whole-file SHA -> post-I/O candidate-file identity revalidation -> stable repository snapshot`

The candidate topology gate fails the whole discovery before title/hash authority if a named `SKILL.md` is a symlink/redirector or non-ordinary file at enumeration time. The new pre-I/O revalidation rejects persistent redirector/type/device/inode/size/mtime drift before either content reader. The later revalidation remains and rejects drift during/after content work before `SkillRecord` append.

No second provenance probe, registry, controller, scheduler, phone path, or recovery owner is created.

## Verdicts

- `STABLE` — the same no-follow device/inode and size/mtime observation bracketed the checked work.
- `REDIRECTOR_BLOCKED` — the admitted candidate observation itself is a symlink/junction redirector.
- `FILE_CHANGED` — file type, redirector state, device/inode identity, size, or mtime changed between observations.
- `IDENTITY_UNAVAILABLE` — the platform observation does not expose a usable inode/file-index token.

Only `STABLE` is eligible to become a `SkillRecord`.

## Pre-I/O topology repair

`tools/test_try_forever_skill_file_identity_integration.py` contains `test_redirector_replacement_before_title_io_must_be_revalidated_before_any_content_open`. The owner now has the source gate that this fixture requires: after containment and immediately before `markdown_title(...)`, it captures a fresh no-follow identity and compares it with the admitted identity. A persistent symlink/redirector replacement therefore takes the existing identity error path before either `markdown_title(...)` or `sha256_file(...)` is invoked.

This is **SOURCE_WIRED**, not TESTED. The regression has not been observed passing on an authorized runner in this heartbeat.

## Applied surgery provenance

`patches/try-forever-provenance-owner-preio-v5.patch` records the exact applied surgery. It was base-locked to owner blob `f6f1bafc6b9e99030ad29b408d74cd088f910b82`; the owner source mutation landed at commit `bf91827aa74651e1500edd916a26ff9f6acac13e`, authenticated owner blob `e1d10fb4c917813bc89780486c79a5e2d2bc4bea`.

The same source surgery also composes the independent schema-v5 record-path projection wound. Combining the non-overlapping hunks under one base prevented two future whole-file mutations from racing; it does **not** merge their evidence claims.

## Atomicity boundary

`STABLE` is an observation verdict, **not** an atomic file-handle claim.

Portable no-follow stat revalidation can detect persistent replacement and common in-place mutation. The new pre-I/O gate still does not prove absence of swap-and-restore races entirely between observations, inode/file-index reuse, same-size/same-mtime content rewrites, replacement after the precheck, or title/hash reads being bound to one immutable file handle on every platform.

Do not rename `STABLE` to `ATOMIC`, `BOUND`, or `SAFE_TOCTOU` without platform-specific evidence and owner integration that actually earns that claim.

## Regression source

`tools/test_try_forever_skill_file_identity.py` pins the pure helper.

`tools/test_try_forever_skill_file_identity_integration.py` pins existing-owner source behavior for stable authority, named non-file/symlink rejection, pre-I/O persistent replacement rejection before content readers, replacement after hashing before record append, and identity-capture failure before content work.

These are regression **sources** until an authorized runner produces test evidence.

## Capability state — 2026-08-19 heartbeat

- helper source: **YES**;
- static no-follow candidate topology gate in existing owner: **YES / SOURCE_WIRED**;
- candidate-file identity bracket in existing owner: **YES / SOURCE_WIRED**;
- pre-I/O redirector/special-topology revalidation: **YES / SOURCE_WIRED**;
- applied owner source commit: **bf91827aa74651e1500edd916a26ff9f6acac13e**;
- authenticated owner source blob: **e1d10fb4c917813bc89780486c79a5e2d2bc4bea**;
- applied surgery provenance blob: **580bdc724c02086a14aacddddc568608968dc293**;
- exact authenticated GitHub readback: **YES**;
- regression source: **YES / UNEXECUTED**;
- atomic cross-platform file binding: **NO**;
- probe executed by authorized runner: **NO**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall

Do not consume or mutate Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance. If a P0 issue is discovered incidentally, record one concise finding for the canonical P0 owner and stop.

## Done

This skill lights only when candidate-file identity/revalidation truth materially changes. Source wiring does not imply atomicity, test passage, runtime delivery, or phone acceptance.
