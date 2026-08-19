# Heartbeat Provenance Emission Composition

## Purpose

Compose the already-existing late repository-custody and generated-index artifact-custody organs into one small preservation-only decision surface for the **existing** TRY FOREVER provenance owner.

## Law

Late evidence may preserve earlier authority; it may never manufacture it.

A repository-skill authority claim survives report emission only when the earlier certification was literally authoritative and the late one-process repository observation still reports the same clean certified HEAD. An unavailable late observation does not donate embedded or stale fields back into authority.

A prior generated-index `VERIFIED_CURRENT` claim survives only when both:

1. final repository custody is `STABLE_CLEAN`; and
2. the exact complete generated-index artifact SHA-256 observed during the inspection that earned the prior verdict is revalidated as `STABLE` at emission.

Declared negative generated-index diagnostics (`STALE` or `UNRESOLVED`) remain negative and are never promoted by green late gates. Unknown prior status shapes fail closed.

Only prior `VERIFIED_CURRENT` requires late generated-index artifact revalidation work. Negative or undeclared prior states cannot become current through late gates, so forcing another authority-facing artifact read for them is needless I/O.

## Existing-owner composition

The sole owner remains `tools/try_forever_skill_provenance_probe.py`; do not create a second probe, serializer daemon, scheduler, renderer, phone lane, or P0 coordinator.

Schema `try-forever-skill-provenance.v4` now composes the existing organs in this order:

1. bounded direct skill discovery + snapshot certification;
2. finite no-follow initial generated-index observation and semantic verdict;
3. retain the exact initial generated-index whole-artifact SHA only when that verdict is `VERIFIED_CURRENT`;
4. if and only if late artifact revalidation can affect currentness, perform one bounded exact artifact re-observation;
5. perform the late one-process repository observation after that artifact work;
6. compose repository and generated-index custody with `compose_provenance_emission(...)`;
7. emit repository skill records only when late repository authority survives;
8. emit prior generated-index `VERIFIED_CURRENT` only when exact artifact custody also survives.

This ordering intentionally performs no new authority-facing generated-index read after the declared final repository observation.

## Existing organs

- `tools/try_forever_repository_emission_observation.py`
- `tools/try_forever_report_emission_snapshot.py`
- `tools/try_forever_generated_index_artifact_observation.py`
- `tools/try_forever_generated_index_emission_policy.py`
- `tools/try_forever_provenance_emission_composition.py`
- `tools/try_forever_skill_provenance_probe.py`

## Hostile fixtures

`tools/test_try_forever_provenance_emission_composition.py` pins the pure composition. `tools/test_try_forever_provenance_owner_v4_emission.py` pins the existing-owner schema-v4 integration, including:

- exact initial inspection SHA retention;
- stable repository + same artifact preserving authority/currentness;
- external artifact A → B withholding only generated-index currentness when repository authority survives;
- late repository custody loss zeroing emitted repository-skill authority and withholding prior index currentness;
- strict mode failing on late custody loss;
- negative prior index state skipping needless late artifact I/O;
- portable root/generated-index display paths and external-path suppression.

Regression source is not executed-test evidence.

## Current capability truth

- pure emission-composition source: **IMPLEMENTED_SOURCE**
- composition source blob: **1074e97afc940bf92182b67b2004d9e27e2755a6**
- existing provenance owner consumes this composition: **YES / SOURCE_WIRED**
- owner schema: **try-forever-skill-provenance.v4**
- owner source commit/blob: **90054f3f0761b0993d635527d60ad43f68c20a8d / f6f1bafc6b9e99030ad29b408d74cd088f910b82**
- owner-v4 hostile regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**
- owner-v4 regression commit/blob: **19dd1621093eaefc830b13938404a2192c979584 / ebea66749d5038be4d303827681df38adfe1d554**
- generated-index named-path preservation: **YES / SOURCE_WIRED**
- finite initial artifact admission: **YES / SOURCE_WIRED**
- exact initial artifact SHA carried into late custody: **YES / SOURCE_WIRED**
- late repository/artifact composition: **YES / SOURCE_WIRED**
- portable report-path projection: **PARTIAL / repository root + generated-index path wired; skill/discovery-error path fields remain a review wound**
- tested: **NO**
- runtime UI / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## P0 firewall

Repository evidence only. Phone/P0 consumption and mutation remain zero. Do not coordinate, wake, retask, replace, duplicate, or govern the canonical Fortress recovery chain.
