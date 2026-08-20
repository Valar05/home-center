# Heartbeat Generated-Index Timestamp Contract

## Purpose

Keep generated-index timestamp evidence exact enough that leading/trailing control or whitespace normalization cannot silently turn different source metadata into the same provenance timestamp.

This is source/evidence policy only. It owns no generated-index I/O, repository owner, renderer, scheduler, phone surface, P0 chain, deployment, or acceptance path.

## Trigger

Light when generated-index timestamp text is normalized before semantic admission, especially through broad `strip()` behavior that can erase edge controls or whitespace before a `VERIFIED_CURRENT` decision.

## Supporting source

`tools/try_forever_generated_index_timestamp_policy.py` preserves the current numeric seconds/milliseconds convention and naive-as-UTC compatibility while rejecting normalization-dependent string input. Boolean and non-finite numeric shapes fail closed.

## Current owner wound

Authenticated owner blob `cd94af837245f6c9d6c64ad4f4620699acbb19fb` still implements `parse_timestamp()` with broad `value.strip()` before parsing.

`tools/test_try_forever_generated_index_timestamp_owner_boundary.py` is intentionally RED against that source: edge-whitespace timestamp text must not be stripped into authority.

## Regression source

- `tools/test_try_forever_generated_index_timestamp_policy.py` pins the pure policy.
- `tools/test_try_forever_generated_index_timestamp_owner_boundary.py` pins the owner integration seam.

Both remain **UNEXECUTED** until an authorized runner produces evidence.

## Capability state — 2026-08-19 heartbeat

- exact timestamp policy source: **YES**;
- exact authenticated owner readback: **YES**;
- owner consumes exact timestamp policy: **NO**;
- owner broad-strip normalization wound: **YES / CURRENT**;
- regression source: **YES / UNEXECUTED**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall

No Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance.
