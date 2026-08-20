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

## Current owner wound

Authenticated owner blob `cd94af837245f6c9d6c64ad4f4620699acbb19fb` still calls `markdown_title(path)` and `sha256_file(path)` separately inside `discover_skills`.

`tools/test_try_forever_skill_content_custody_owner_boundary.py` is deliberately RED against that source shape. It requires the sole owner to consume one `observe_skill_content(...)` result and retire both independent authority-facing opens from the per-candidate record path.

## Regression source

- `tools/test_try_forever_skill_content_custody.py` pins the supporting single-observation policy.
- `tools/test_try_forever_skill_content_custody_owner_boundary.py` pins the existing-owner integration seam and is intentionally RED until owner composition lands.

These are regression **sources** until an authorized runner produces execution evidence.

## Capability state — 2026-08-19 heartbeat

- supporting single-artifact observation source: **YES**;
- exact authenticated owner readback: **YES**;
- owner single-artifact title/SHA composition: **NO**;
- owner still uses separate title/hash opens: **YES / CURRENT WOUND**;
- regression source: **YES / UNEXECUTED**;
- atomic universal filesystem snapshot: **NO**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall

Do not consume or mutate Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance.

## Done

This skill lights only when single-artifact content custody materially changes. Supporting source does not imply owner wiring, test passage, runtime behavior, or phone acceptance.
