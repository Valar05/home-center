# Heartbeat Generated-Index Timestamp Contract

## Purpose

Keep generated-index timestamp evidence exact enough that leading/trailing control or whitespace normalization cannot silently turn different source metadata into the same provenance timestamp.

This is source/evidence policy only. It owns no generated-index I/O, repository owner, renderer, scheduler, phone surface, P0 chain, deployment, or acceptance path.

## Trigger

Light when generated-index timestamp text is normalized before semantic admission, especially through broad `strip()` behavior that can erase edge controls or whitespace before a `VERIFIED_CURRENT` decision.

## Supporting source

`tools/try_forever_generated_index_timestamp_policy.py` preserves the current numeric seconds/milliseconds convention and naive-as-UTC compatibility while rejecting normalization-dependent string input. Boolean and non-finite numeric shapes fail closed.

## Existing-owner source wiring

Authenticated Home Center GitHub-admin mutation applied the prepared exact-timestamp delta to the sole provenance owner in commit `52e47781f5e9c11a17bc59c3b842700fcc784127`; authenticated owner readback blob is `2f3ebd530f46283a59bd6ff34149042a1b825d89`.

`tools/try_forever_skill_provenance_probe.py::parse_timestamp(...)` now delegates to `parse_generated_index_timestamp(...)`, converts `GeneratedIndexTimestampError` to the historical optional `None` result, and contains no broad `.strip()` normalization.

## Applied surgery provenance

`patches/try-forever-provenance-content-timestamp-owner.delta.json`, originally blob `2924cc86c83238a3ce35de80d6d6db1caf227ab1`, defined the exact timestamp adapter together with the independent single-artifact `SKILL.md` custody surgery. Its timestamp portion is now **APPLIED_SOURCE**.

## Regression source

- `tools/test_try_forever_generated_index_timestamp_policy.py` pins the pure policy.
- `tools/test_try_forever_generated_index_timestamp_owner_boundary.py` pins the owner integration seam.

Both remain **UNEXECUTED** until an authorized runner produces evidence.

## Capability state — 2026-08-20 heartbeat

- exact timestamp policy source: **YES**;
- authenticated owner readback: **YES**;
- owner-boundary regression source: **YES / UNEXECUTED**;
- existing-owner delta source: **YES / APPLIED_SOURCE**;
- owner consumes exact timestamp policy: **YES / SOURCE_WIRED**;
- owner broad-strip normalization wound: **NO / RETIRED_FROM_AUTHORITY_PATH**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall

No Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance.
