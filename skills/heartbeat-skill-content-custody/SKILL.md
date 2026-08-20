# Heartbeat Skill Content Custody

## Purpose

Bind one repository-skill title and whole-file SHA to one bounded opened `SKILL.md` artifact observation instead of relying on two independent path opens bracketed only by portable stat observations.

This skill owns source/evidence policy only. It owns no repository discovery controller, renderer, scheduler, phone lane, Phone Hands surface, P0 recovery chain, deployment path, or physical acceptance action.

## Trigger

Light when an admitted `SKILL.md` can be opened more than once for authority-facing content work and a swap-and-restore between those opens could make title and SHA describe different underlying content while pre/post path observations return to the original object.

## Existing owner and supporting organ

Sole owner: `tools/try_forever_skill_provenance_probe.py`.

Supporting source: `tools/try_forever_skill_content_custody.py`.

The supporting source composes the repository's already-hardened finite regular-file observation organ rather than duplicating no-follow/reparse/descriptor-custody logic. One complete bounded strict-UTF-8 artifact observation supplies both the digest and the text from which title is derived. Title extraction then runs in memory and does not reopen the named path.

## Why this is different from file-identity revalidation

`heartbeat-skill-file-identity-revalidation` detects persistent redirector/type/device/inode/size/mtime drift before and after content work. That remains useful.

It does **not** prove that two separate opens in the middle saw one immutable object. A swap-and-restore can occur entirely between observations. Content custody therefore composes with file-identity revalidation; it does not replace it.

## Existing-owner source wiring

Authenticated Home Center GitHub-admin mutation applied the prepared content-custody delta to the sole owner in commit `52e47781f5e9c11a17bc59c3b842700fcc784127`; authenticated owner readback blob is `2f3ebd530f46283a59bd6ff34149042a1b825d89`.

`discover_skills(...)` now calls `observe_skill_content(...)` exactly once per admitted candidate with the owner's existing byte/title resource authorities, takes `content.title` and `content.sha256` from that one observation, and preserves post-content file-identity revalidation. The old helper functions may remain defined for compatibility/source archaeology, but they no longer own the authority path.

## Applied surgery provenance

`patches/try-forever-provenance-content-timestamp-owner.delta.json`, originally blob `2924cc86c83238a3ce35de80d6d6db1caf227ab1`, defined this source change together with the independent exact timestamp adapter. Its content-custody portion is now **APPLIED_SOURCE**.

## Regression source

- `tools/test_try_forever_skill_content_custody.py` pins the supporting single-observation policy.
- `tools/test_try_forever_skill_content_custody_owner_boundary.py` pins the existing-owner integration seam.

These remain regression **sources** until an authorized runner produces execution evidence.

## Capability state — 2026-08-20 heartbeat

- supporting single-artifact observation source: **YES**;
- authenticated owner readback: **YES**;
- owner-boundary regression source: **YES / UNEXECUTED**;
- existing-owner delta source: **YES / APPLIED_SOURCE**;
- owner single-artifact title/SHA composition: **YES / SOURCE_WIRED**;
- owner separate title/hash authority opens: **NO**;
- post-content file-identity revalidation retained: **YES / SOURCE_WIRED**;
- atomic universal filesystem snapshot: **NO**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall

Do not consume or mutate Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance.

## Done

This skill lights only when single-artifact content custody materially changes. Source wiring and authenticated readback do not imply test passage, runtime behavior, or phone acceptance.
