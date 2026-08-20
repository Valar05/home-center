# Heartbeat Skill Content Custody

## Purpose

Bind one repository-skill title, whole-file SHA, and Git blob object identity to one bounded opened `SKILL.md` artifact observation instead of relying on independent path opens or a later content reread.

This skill owns source/evidence policy only. It owns no repository discovery controller, renderer, scheduler, phone lane, Phone Hands surface, P0 recovery chain, deployment path, or physical acceptance action.

## Trigger

Light when authority-facing evidence for one admitted `SKILL.md` risks being derived from different content observations, when a later authority gate needs an identity derived from already-observed bytes rather than reopening the path, or when regression source drifts back toward retired multi-open helper assumptions.

## Existing owner and supporting organ

Sole owner: `tools/try_forever_skill_provenance_probe.py`.

Supporting source: `tools/try_forever_skill_content_custody.py`.

The supporting source composes the repository's already-hardened finite regular-file observation organ rather than duplicating no-follow/reparse/descriptor-custody logic. One complete bounded strict-UTF-8 artifact observation supplies raw SHA, text for title derivation, and Git blob object identity. Title and Git object framing both run in memory and do not reopen the named path.

## Why this is different from file-identity revalidation

`heartbeat-skill-file-identity-revalidation` detects persistent redirector/type/device/inode/size/mtime drift before and after content work. That remains useful.

It does **not** prove that two separate opens in the middle saw one immutable object. A swap-and-restore can occur entirely between observations. Content custody therefore composes with file-identity revalidation; it does not replace it.

## Existing-owner source wiring

Authenticated Home Center GitHub-admin mutation applied the original content-custody surgery in commit `52e47781f5e9c11a17bc59c3b842700fcc784127`. The sole owner calls `observe_skill_content(...)` exactly once per admitted candidate with the owner's existing byte/title resource authorities, takes `content.title`, `content.sha256`, and `content.git_blob_identity` from that one observation, and preserves post-content file-identity revalidation.

Authenticated follow-up surgery in commit `94122a12714414686d34827321eaf7481d543424` wired the bounded HEAD blob set plus `assess_skill_head_content_binding(...)` into the same sole owner. The owner now compares the Git blob identity derived from the exact admitted `SKILL.md` observation to the ordinary blob committed at the discovery HEAD before `SkillRecord` append.

Therefore the old claim that content↔HEAD owner binding is still proposed/unwired is retired.

## Applied surgery provenance

- `patches/try-forever-provenance-content-timestamp-owner.delta.json` — content-custody portion **APPLIED_SOURCE**.
- `patches/try-forever-skill-head-content-owner.delta.json` — content↔HEAD portion **APPLIED_SOURCE**.

Patch artifacts are provenance; current authenticated owner source is the capability truth.

## Regression-source ownership

Canonical current fixtures:

- `tools/test_try_forever_skill_content_custody.py` pins title/raw-SHA/Git-blob identity to one artifact observation and fails closed on byte-count drift.
- `tools/test_try_forever_skill_content_custody_owner_boundary.py` pins the sole-owner single-artifact integration.
- `tools/test_try_forever_skill_head_content_owner_boundary.py` pins the source-wired HEAD binding.
- `tools/test_try_forever_skill_title_resource_budget.py` was migrated at the 2026-08-20 1100 heartbeat to exercise title budgets through `observe_skill_content(...)`, not the retired owner-local `markdown_title(...)` helper path.
- `tools/test_try_forever_skill_provenance_probe.py` was narrowed at the same heartbeat to pure top-level probe/report/index contracts. It no longer treats a non-Git temp root as repository-skill authority and no longer patches legacy `sha256_file(...)` / `markdown_title(...)` helpers as if the owner consumed them.

Legacy helper functions may remain in the owner module as compatibility/source archaeology until separately removed, but **they are not the authority path and regression source must not imply that they are**.

All regression files remain regression **source** until an authorized runner produces execution evidence.

## Capability state — 2026-08-20 1100 heartbeat

- supporting single-artifact observation source: **YES**;
- authenticated owner uses single-artifact title/SHA/Git-blob path: **YES / SOURCE_WIRED**;
- bounded HEAD blob-set observation: **YES / SOURCE_WIRED**;
- owner content↔HEAD binding before record append: **YES / SOURCE_WIRED**;
- same-observation regression source: **YES / UNEXECUTED**;
- owner-boundary regression source: **YES / UNEXECUTED**;
- title-resource regression migrated to current custody path: **YES / SOURCE**;
- top-level provenance regression retired stale legacy-helper assumptions: **YES / SOURCE**;
- atomic universal filesystem snapshot: **NO / UNCLAIMED**;
- tested: **NO**;
- runtime UI / TalkBack: **NO**;
- deployed / callable / executed / delivered / accepted: **NO**.

## P0 / phone firewall

Do not consume or mutate Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance.

## Done

This skill lights only when single-artifact content custody materially changes or its regression/doctrine truth is corrected. Source wiring and authenticated readback do not imply test passage, runtime behavior, deployment, or phone acceptance.
