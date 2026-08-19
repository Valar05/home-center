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

- stable clean late repository + exact stable artifact preserves prior authority/currentness;
- matching final HEAD cannot manufacture missing prior repository authority;
- an `UNAVAILABLE` late observation cannot reuse stale embedded head/dirty values;
- external artifact A → B with a stable repository withholds prior `VERIFIED_CURRENT` as `UNRESOLVED`;
- a declared prior `STALE` diagnostic remains `STALE` under green late gates;
- an undeclared prior generated-index status fails closed.

Regression source is not executed-test evidence.

## Current capability truth

- pure emission-composition source: **IMPLEMENTED_SOURCE**
- source blob: **54f0bebc96ff86f31a1dfab630b6f0b420522ba9**
- hostile regression source: **REGRESSION_SOURCE / UNEXECUTED**
- regression blob: **e038ac5b4b576396ebfb9483c30a099e92f7137a**
- existing provenance owner consumes this composition: **NO**
- existing owner preserves generated-index named redirector before artifact admission: **NO**
- tested: **NO**
- runtime UI / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## P0 firewall

Repository evidence only. Phone/P0 consumption and mutation remain zero. Do not coordinate, wake, retask, replace, duplicate, or govern the canonical Fortress recovery chain.
