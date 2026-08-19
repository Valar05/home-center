# Heartbeat Provenance Emission Composition

## Purpose

Compose the already-existing late repository-custody and generated-index artifact-custody organs into one small preservation-only decision surface for the **existing** TRY FOREVER provenance owner.

## Law

Late evidence may preserve earlier authority; it may never manufacture it.

A repository-skill authority claim survives report emission only when the earlier certification was literally authoritative and the late one-process repository observation still reports the same clean certified HEAD. An unavailable late observation does not donate any embedded/stale fields back into authority.

A prior generated-index `VERIFIED_CURRENT` claim survives only when both:

1. final repository custody is `STABLE_CLEAN`; and
2. the exact complete generated-index artifact SHA-256 remains `STABLE` through emission revalidation.

A declared negative generated-index diagnostic (`STALE` or `UNRESOLVED`) remains negative and is never promoted by green late gates. Unknown prior status shapes fail closed through the existing generated-index emission policy.

Only prior `VERIFIED_CURRENT` requires late generated-index artifact revalidation work. Negative or undeclared prior states cannot become current through late gates, so forcing another authority-facing artifact read for them is needless I/O. `needs_generated_index_artifact_revalidation(...)` exposes that work-planning decision without performing I/O or granting authority.

## Existing organs

Compose, do not duplicate:

- `tools/try_forever_repository_emission_observation.py`
- `tools/try_forever_report_emission_snapshot.py`
- `tools/try_forever_generated_index_artifact_observation.py`
- `tools/try_forever_generated_index_emission_policy.py`
- `tools/try_forever_provenance_emission_composition.py`

The sole owner remains `tools/try_forever_skill_provenance_probe.py`. This skill does not authorize a second probe, serializer daemon, scheduler, renderer, phone lane, or P0 coordinator.

## Hostile fixtures

`tools/test_try_forever_provenance_emission_composition.py` must pin at least:

- only prior `VERIFIED_CURRENT` requests late artifact-revalidation work;
- stable clean late repository + exact stable artifact preserves prior authority/currentness;
- matching final HEAD cannot manufacture missing prior repository authority;
- an `UNAVAILABLE` late observation cannot reuse stale embedded head/dirty values;
- external artifact A → B with a stable repository withholds prior `VERIFIED_CURRENT` as `UNRESOLVED`;
- a declared prior `STALE` diagnostic remains `STALE` without needing a late artifact read;
- an undeclared prior generated-index status fails closed without needing a late artifact read.

Regression source is not executed-test evidence.

## Current capability truth

- pure emission-composition source: **IMPLEMENTED_SOURCE**
- source blob: **1074e97afc940bf92182b67b2004d9e27e2755a6**
- artifact-revalidation work-planning gate: **IMPLEMENTED_SOURCE**
- hostile regression source: **REGRESSION_SOURCE / UNEXECUTED**
- regression blob: **92d5c308257f38cecc25bbec398301608882857b**
- existing provenance owner consumes this composition: **NO**
- existing owner preserves generated-index named redirector before artifact admission: **NO**
- tested: **NO**
- runtime UI / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## P0 firewall

Repository evidence only. Phone/P0 consumption and mutation remain zero. Do not coordinate, wake, retask, replace, duplicate, or govern the canonical Fortress recovery chain.
