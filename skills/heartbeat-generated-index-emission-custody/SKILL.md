# Heartbeat Generated-Index Emission Custody

## Purpose

Keep a generated index's `VERIFIED_CURRENT` claim bound to both the repository state and the exact finite generated-index artifact that earned that verdict.

## Law

Repository custody and generated-index artifact custody are separate evidence domains.

A generated index may be inspected against a certified clean repository snapshot. A prior `VERIFIED_CURRENT` result may survive report emission only when:

1. the final repository-custody verdict is `STABLE_CLEAN`; and
2. the exact generated-index whole-artifact SHA-256 observed during the inspection that earned the verdict is revalidated as `STABLE` for emission.

A stable repository HEAD/cleanliness verdict cannot certify continuity of a separately mutable external index file. If the index cannot be re-read, its whole-artifact SHA-256 is missing/non-canonical, or the emission digest differs from the inspected digest, positive currentness is withheld as `UNRESOLVED`.

Only declared prior string states `VERIFIED_CURRENT`, `STALE`, and `UNRESOLVED` exist. Unknown or non-string shapes fail closed. Negative states are never promoted by green late gates and do not require needless late artifact I/O.

## Named-path preservation and finite inspection admission

The existing owner preserves caller-supplied generated-index topology with lexical absolute-path normalization; it does not dereference with `Path.resolve()` before topology admission. The named path then enters `observe_generated_index_artifact(...)` before JSON semantics.

The artifact observer admits only one bounded finite ordinary file: no-follow/reparse checks, path↔descriptor identity, complete EOF inside the existing byte budget, strict UTF-8, and persistent path/descriptor stability observations. These checks are strong observations, not universal atomic filesystem binding.

## Existing-owner v4 emission composition

Schema `try-forever-skill-provenance.v4` now carries the exact `observation.sha256` from the initial artifact observation into `IndexVerdict.inspection_sha256` when and only when the initial semantic verdict is `VERIFIED_CURRENT`.

At emission:

- only prior `VERIFIED_CURRENT` triggers another exact artifact observation;
- the emission artifact SHA is compared with the retained inspection SHA through the existing custody policy;
- a final one-process repository observation is performed after artifact revalidation;
- `compose_provenance_emission(...)` requires both stable repository custody and stable artifact identity before prior positive currentness survives;
- changed/unreadable artifact custody with a stable repository withholds generated-index currentness without discarding independently surviving repository-skill authority;
- no generated-index authority-facing read occurs after the final repository observation.

## Hostile fixtures

Existing pure fixtures cover exact stable/changed artifact custody and declared prior statuses. `tools/test_try_forever_provenance_owner_v4_emission.py` adds owner-level source fixtures for exact inspection SHA retention, same-artifact survival, A→B withholding, negative-state I/O suppression, and strict late-custody failure. Regression source remains unexecuted.

## Current capability truth

- pure artifact-custody + emission policy source: **IMPLEMENTED_SOURCE**
- bounded exact artifact-observation primitive: **IMPLEMENTED_SOURCE**
- finite regular-artifact topology gate: **IMPLEMENTED_SOURCE**
- existing owner preserves caller named path: **YES / SOURCE_WIRED**
- existing owner consumes finite initial artifact admission: **YES / SOURCE_WIRED**
- existing owner retains exact inspection artifact SHA: **YES / SOURCE_WIRED**
- existing owner consumes late repository/artifact emission composition: **YES / SOURCE_WIRED**
- owner schema: **try-forever-skill-provenance.v4**
- owner commit/blob: **90054f3f0761b0993d635527d60ad43f68c20a8d / f6f1bafc6b9e99030ad29b408d74cd088f910b82**
- owner-v4 regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**
- owner-v4 regression commit/blob: **19dd1621093eaefc830b13938404a2192c979584 / ebea66749d5038be4d303827681df38adfe1d554**
- universal wall-clock artifact I/O deadline / atomic artifact binding: **NO**
- tested: **NO**
- runtime UI / TalkBack / deployment / callability / execution / delivery / acceptance: **NO**

## Ownership

Compose only into `tools/try_forever_skill_provenance_probe.py`. Do not create a second provenance probe, serializer daemon, scheduler, recovery controller, Phone Hands lane, or P0 coordinator.

## P0 firewall

Repository evidence only. Phone/P0 consumption and mutation remain zero.
