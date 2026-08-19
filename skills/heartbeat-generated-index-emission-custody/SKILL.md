# Heartbeat Generated-Index Emission Custody

## Purpose

Keep a generated index's `VERIFIED_CURRENT` claim bound to both the repository state and the exact generated-index artifact that earned that verdict.

## Law

Repository custody and generated-index artifact custody are separate evidence domains.

A generated index may be inspected against a certified clean repository snapshot. A prior `VERIFIED_CURRENT` result may survive report emission only when:

1. the final repository-custody verdict is `STABLE_CLEAN`, and
2. the exact generated-index content identity observed during inspection is revalidated as `STABLE` for emission.

A stable repository HEAD/cleanliness verdict cannot certify continuity of a separately mutable external index file. If the index cannot be re-read, its whole-artifact SHA-256 is missing/non-canonical, or the emission digest differs from the inspected digest, positive currentness is withheld as `UNRESOLVED`.

Already-negative `STALE`/`UNRESOLVED` diagnostics remain diagnostic and are never promoted.

Digest revalidation narrows the evidence window; it does **not** prove atomic cross-filesystem binding, prevent swap-and-restore, or certify runtime delivery.

## Hostile fixture

`externalGeneratedIndexMutationAfterInspectionMustWithholdCurrentness()`:

- inspect external content A and bind its complete bounded SHA-256;
- keep repository HEAD H clean and stable;
- replace the external artifact with content B;
- final repository custody may still be `STABLE_CLEAN`;
- required: generated-index currentness is withheld unless the exact artifact/content identity is independently revalidated.

## Current capability truth

- pure artifact-custody + emission policy source: **IMPLEMENTED_SOURCE**
- hostile regression source including external mutation: **REGRESSION_SOURCE / UNEXECUTED**
- existing provenance owner consumption: **NO**
- prior report-boundary patch: **REJECTED_UNSAFE / DO_NOT APPLY** until it inherits external-artifact custody and coherent final repository observation
- tested: **NO**
- runtime UI / TalkBack / deployment / callability / execution / delivery / acceptance: **NO**

## Ownership

Compose only into `tools/try_forever_skill_provenance_probe.py`. Do not create a second provenance probe, serializer daemon, scheduler, recovery controller, Phone Hands lane, or P0 coordinator.

## P0 firewall

This skill is repository-evidence policy only. It does not consume or mutate the primary-phone surface, Phone Hands, recovery queues/relays, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.
