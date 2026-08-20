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

`tools/test_try_forever_generated_index_timestamp_owner_boundary.py` now locks both source shape and behavior: the owner adapter must delegate to `parse_generated_index_timestamp(...)`, must not contain `.strip()`, must reject edge whitespace/control/bidi evidence, and must preserve the accepted exact string/numeric compatibility.

## Prepared existing-owner surgery

`patches/try-forever-provenance-content-timestamp-owner.delta.json` is durable exact-delta source, content blob `2924cc86c83238a3ce35de80d6d6db1caf227ab1`, first committed at `28fb76390199bd77d57c65f601a7e295e16162cc`.

The delta replaces the broad-strip owner parser with the existing exact timestamp policy while preserving the historical optional-return adapter shape. It shares the same owner mutation with the independent single-artifact `SKILL.md` custody surgery rather than creating a second provenance owner.

**Status: `PROPOSED_NOT_APPLIED`.** Delta existence is not owner wiring.

## Regression source

- `tools/test_try_forever_generated_index_timestamp_policy.py` pins the pure policy.
- `tools/test_try_forever_generated_index_timestamp_owner_boundary.py` pins the owner integration seam and remains intentionally RED until owner composition lands.

Both remain **UNEXECUTED** until an authorized runner produces evidence.

## Capability state — 2026-08-20 heartbeat

- exact timestamp policy source: **YES**;
- exact authenticated owner readback: **YES**;
- strengthened RED owner-boundary regression source: **YES / UNEXECUTED**;
- exact existing-owner delta source: **YES / PROPOSED_NOT_APPLIED**;
- owner consumes exact timestamp policy: **NO**;
- owner broad-strip normalization wound: **YES / CURRENT**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## P0 / phone firewall

No Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance.
