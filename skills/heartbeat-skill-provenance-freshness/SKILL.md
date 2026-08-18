# Heartbeat Skill Provenance Freshness

## Purpose

Make `repository_skill` heartbeat lights prove that the named skill exists in the **current repository tree**. Generated indexes, cached matchers, old receipts, or label-shaped strings may help discover candidates, but they are never sufficient provenance by themselves.

This skill is deliberately source/evidence infrastructure. It owns no overlay controller, renderer, scheduler, phone lane, P0 recovery chain, deployment, or physical acceptance.

## Authority order

For a light whose `provenanceKind` is `repository_skill`:

1. Resolve an actual current-tree `skills/**/SKILL.md` path.
2. Hash the exact current file bytes with SHA-256.
3. Preserve the current repository head and cleanliness state separately from the skill hash.
4. Treat generated indexes only as discovery aids unless they independently pass the generated-index freshness gate below.
5. Even a `VERIFIED_CURRENT` generated index does **not** replace direct current-tree skill existence. It only proves that the index itself may be trusted as current discovery evidence.

If direct current-tree resolution fails, the light may remain dark or use the correct `doctrine`, `jar`, `reviewer`, or `runtime_boundary` provenance kind when that is what actually exists. Never promote a familiar label into `repository_skill` by vibes.

## Generated-index freshness gate

A generated/cached skill index may be classified `VERIFIED_CURRENT` only when all of these hold:

- current git HEAD is available;
- current checkout cleanliness is available and clean;
- the index declares the exact same source HEAD;
- the index explicitly declares that its source tree was clean;
- its generation timestamp is parseable;
- it is no older than the configured freshness window (default 14 days);
- it is not implausibly in the future.

Otherwise classify it fail-closed:

- `STALE` when a known mismatch exists, such as foreign HEAD, declared dirty source, or age beyond the freshness window;
- `UNRESOLVED` when required proof is missing or ambiguous, such as unavailable checkout cleanliness, missing source HEAD, missing clean-tree declaration, unreadable JSON, missing timestamp, or an implausible future timestamp.

`STALE` and `UNRESOLVED` indexes may suggest where to look. They may not earn an active repository-skill light.

## Canonical probe

Use:

`tools/try_forever_skill_provenance_probe.py`

The probe is standard-library source and performs no network calls. It:

- discovers current `skills/**/SKILL.md` files recursively;
- records repository-relative path, H1 title, and exact SHA-256;
- fails closed on case-insensitive current-tree path collisions;
- reports current git HEAD and cleanliness when available;
- classifies an optional generated index as `VERIFIED_CURRENT`, `STALE`, or `UNRESOLVED`;
- supports `--expected-head` and `--strict` for a later authorized runner.

A probe file existing in GitHub is **IMPLEMENTED SOURCE**. A regression file existing in GitHub is **REGRESSION SOURCE**. Neither means the probe or tests have executed. Only an authorized execution receipt may promote those states to `TESTED`.

## Regression source

`tools/test_try_forever_skill_provenance_probe.py` pins hostile cases including:

- direct current-tree skill discovery and hashing;
- repository-relative generated-index resolution;
- matching clean/fresh index;
- foreign source HEAD;
- dirty index source;
- dirty or unknown current checkout cleanliness;
- stale generation age;
- implausible future timestamps;
- missing clean-tree declaration.

Keep the test import independent of caller working directory so a future runner does not accidentally test Python path luck instead of the probe contract.

## Heartbeat consequence

This skill materially lights when it changes provenance truth: for example, a previously trusted generated matcher is demoted to discovery-only, a current skill path/hash is proven, or ambiguous provenance is prevented from becoming an active repository-skill light.

It stays dark when the pulse did not need repository-skill provenance work. Do not list it merely because it exists.

## Capability membrane

Preserve these states independently:

`requested -> implemented source -> exact repository readback -> probe executed -> regression tested -> runtime UI consumed -> deployed -> callable -> executed -> delivered -> accepted`

No earlier state implies a later one. In particular:

- repository skill discovery does not prove Android rendering;
- a fresh index does not prove the named current-tree skill unless the skill itself resolves;
- a source probe does not clear Phone Runtime / Phone Hands / P0 gates;
- GitHub source progress is not phone delivery or physical acceptance.

## P0 and duplicate-architecture firewall

This skill may inspect repository/source provenance only. It must not wake, retask, queue, replace, or coordinate Phone Hands, Phone Ingress, Nightcore, Pocket TTS, Chromium, Context Organs, P0 recovery, or their physical acceptance chain. It must not create a neighboring overlay controller, skill registry daemon, scheduler, or deployment path.

If a provenance check exposes a P0-related defect, preserve one concise finding for the canonical P0 owner and stop there.

## Done

A provenance pulse is complete only when it can name:

- the exact current-tree skill path/hash or exact failure to resolve it;
- the current-head/cleanliness boundary used for generated-index judgment;
- the generated-index verdict when one was consulted;
- the exact capability state reached;
- the fact that no later runtime/phone state was inferred without evidence.
