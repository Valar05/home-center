# Heartbeat Skill Head Content Binding

## Purpose

Prevent a clean-looking Git worktree from certifying `repository_skill` provenance when the exact observed `SKILL.md` bytes do not equal the ordinary blob committed at the discovery HEAD.

## Contract

1. The bounded raw HEAD tree, not clean-status inference, owns committed content identity.
2. Authority-facing Git subprocesses use the shared sanitized environment with replacement objects disabled.
3. Worktree identity comes from `content.git_blob_identity` derived from the same bounded stable `observe_skill_content(...)` artifact that supplies title and raw SHA. Do not reopen `SKILL.md` or call `git hash-object` for this binding.
4. One bounded HEAD blob-set observation is performed for the bounded candidate set before per-file authority work when an authority HEAD is available.
5. Missing/incomplete HEAD blob authority fails the repository-skill set closed; exact mismatch/unavailable binding rejects the candidate before `SkillRecord` append.
6. Existing tracked-path, root, file-identity, content-custody, snapshot, expected-head, and final-emission custody gates remain authoritative and independent.
7. This equality check does not prove universal filesystem atomicity, swap-and-restore immunity, or identity-reuse immunity.
8. Keep the sole provenance owner. No second probe/controller/daemon and no phone/P0 surface consumption.

## Owner source wiring — 2026-08-20 0900

Authenticated source surgery at commit `94122a12714414686d34827321eaf7481d543424` changed `tools/try_forever_skill_provenance_probe.py` from base blob `1882ed3b6cf7fe7a9ab5c44862640a6f415bdd1d` to blob `60e85d95c484cee0ca5f637ac3d5763fd20d21cf`.

The owner now:
- accepts `authority_head` in `discover_skills(...)` from the existing pre-discovery repository observation;
- calls `observe_head_skill_blobs(...)` once before the per-file loop for the bounded candidate set;
- fails closed with `HeadSkillContentUnavailable` when HEAD blob authority is unavailable;
- compares each existing `content.git_blob_identity` via `assess_skill_head_content_binding(...)` after post-content file-identity revalidation and before record append;
- emits `HeadSkillContentMismatch` or `HeadSkillContentUnavailable` instead of promoting mismatched content.

## Existing organs

- `tools/try_forever_skill_provenance_probe.py` — sole owner, **SOURCE_WIRED**.
- `tools/try_forever_skill_content_custody.py` — one bounded artifact supplies title/raw SHA/Git blob identity.
- `tools/try_forever_skill_head_blob_observation.py` — bounded exact ordinary HEAD blobs.
- `tools/try_forever_skill_head_content_binding.py` — pure exact equality policy.
- `tools/test_try_forever_skill_head_content_owner_boundary.py` — source-wired acceptance fixture, **UNEXECUTED**.
- `patches/try-forever-skill-head-content-owner.delta.json` — **APPLIED_SOURCE** provenance.

## Capability membrane

- Shared Git environment replacement-object suppression: **YES / SOURCE_WIRED**
- Single-artifact content Git blob identity: **YES / SOURCE_WIRED**
- Sole-owner bounded HEAD blob observation: **YES / SOURCE_WIRED**
- Sole-owner content↔HEAD gate before record append: **YES / SOURCE_WIRED**
- Authenticated owner readback: **YES**
- Regression source: **YES / UNEXECUTED**
- Atomic filesystem binding: **NO / UNCLAIMED**
- TESTED: **NO**
- Runtime UI / TalkBack: **NO**
- Deployed / callable / executed / delivered / accepted: **NO**
- Phone/P0 consumption or mutation: **NO**
