# Heartbeat Skill Content Custody

## Purpose

Bind one repository-skill title, whole-file SHA, and Git blob object identity to one bounded opened `SKILL.md` artifact observation instead of relying on independent path opens or a later content reread.

This skill owns source/evidence policy only. It owns no repository discovery controller, renderer, scheduler, phone lane, Phone Hands surface, P0 recovery chain, deployment path, or physical acceptance action.

## Trigger

Light when authority-facing evidence for one admitted `SKILL.md` risks being derived from different content observations, or when a later authority gate needs an exact identity that should be derived from the already-observed bytes rather than reopening the path.

## Existing owner and supporting organ

Sole owner: `tools/try_forever_skill_provenance_probe.py`.

Supporting source: `tools/try_forever_skill_content_custody.py`.

The supporting source composes the repository's already-hardened finite regular-file observation organ rather than duplicating no-follow/reparse/descriptor-custody logic. One complete bounded strict-UTF-8 artifact observation supplies raw SHA, text for title derivation, and Git blob object identity. Title and Git object framing both run in memory and do not reopen the named path.

## Why this is different from file-identity revalidation

`heartbeat-skill-file-identity-revalidation` detects persistent redirector/type/device/inode/size/mtime drift before and after content work. That remains useful.

It does **not** prove that two separate opens in the middle saw one immutable object. A swap-and-restore can occur entirely between observations. Content custody therefore composes with file-identity revalidation; it does not replace it.

## Existing-owner source wiring

Authenticated Home Center GitHub-admin mutation applied the prepared content-custody delta to the sole owner in commit `52e47781f5e9c11a17bc59c3b842700fcc784127`; authenticated owner readback later remained on the single `observe_skill_content(...)` authority path. `discover_skills(...)` calls that organ exactly once per admitted candidate with the owner's existing byte/title resource authorities, takes `content.title` and `content.sha256` from that one observation, and preserves post-content file-identity revalidation.

The 2026-08-20 0700 source advance extends the already-consumed `SkillContentObservation` with `git_blob_identity`, derived from the same strict-UTF-8 observation. The finite artifact's byte count must equal the re-encoded strict-UTF-8 byte count or the observation fails closed. This does **not** yet mean the sole owner compares that identity against the committed HEAD blob; that separate authority seam remains open and is governed by `heartbeat-skill-head-content-binding`.

## Applied surgery provenance

`patches/try-forever-provenance-content-timestamp-owner.delta.json`, originally blob `2924cc86c83238a3ce35de80d6d6db1caf227ab1`, defined the earlier title/SHA source change together with the independent exact timestamp adapter. Its content-custody portion is **APPLIED_SOURCE**.

`patches/try-forever-skill-head-content-owner.delta.json` is a later base-blob-locked proposal for composing the new Git blob identity with bounded raw-HEAD evidence inside the same owner. It is **PROPOSED_NOT_APPLIED**.

## Regression source

- `tools/test_try_forever_skill_content_custody.py` pins title/raw-SHA/Git-blob identity to one artifact observation and fails closed on byte-count drift.
- `tools/test_try_forever_skill_content_custody_owner_boundary.py` pins the existing owner integration seam for single-artifact content custody.
- `tools/test_try_forever_skill_head_content_owner_boundary.py` remains RED until the owner binds `content.git_blob_identity` to the bounded HEAD blob observation.

These remain regression **sources** until an authorized runner produces execution evidence.

## Capability state — 2026-08-20 0700 heartbeat

- supporting single-artifact observation source: **YES**;
- authenticated owner uses that single-artifact title/SHA path: **YES / SOURCE_WIRED**;
- same observation now exposes Git blob object identity: **YES / SOURCE_WIRED DATA SURFACE**;
- same-observation regression source: **YES / UNEXECUTED**;
- owner-boundary regression source: **YES / UNEXECUTED**;
- post-content file-identity revalidation retained: **YES / SOURCE_WIRED**;
- owner content↔HEAD binding: **NO**;
- exact content↔HEAD owner delta: **YES / PROPOSED_NOT_APPLIED**;
- atomic universal filesystem snapshot: **NO**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall

Do not consume or mutate Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance.

## Done

This skill lights only when single-artifact content custody materially changes. Source wiring and authenticated readback do not imply HEAD authority, test passage, runtime behavior, or phone acceptance.
