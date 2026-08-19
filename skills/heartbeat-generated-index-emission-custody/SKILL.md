# Heartbeat Generated-Index Emission Custody

## Purpose

Keep a generated index's `VERIFIED_CURRENT` claim bound to both the repository state and the exact generated-index artifact that earned that verdict.

## Law

Repository custody and generated-index artifact custody are separate evidence domains.

A generated index may be inspected against a certified clean repository snapshot. A prior `VERIFIED_CURRENT` result may survive report emission only when:

1. the final repository-custody verdict is `STABLE_CLEAN`, and
2. the exact generated-index content identity observed during inspection is revalidated as `STABLE` for emission.

A stable repository HEAD/cleanliness verdict cannot certify continuity of a separately mutable external index file. If the index cannot be re-read, its whole-artifact SHA-256 is missing/non-canonical, or the emission digest differs from the inspected digest, positive currentness is withheld as `UNRESOLVED`.

`tools/try_forever_generated_index_artifact_observation.py` now provides the bounded content-identity throat needed by the owner integration: complete read to EOF inside the caller's existing byte budget, exact SHA-256 over those complete bytes, and strict UTF-8 text for semantic inspection. Max+1 rejects without returning prefix authority. The helper deliberately does not decide currentness or report authority.

Already-negative `STALE`/`UNRESOLVED` diagnostics remain diagnostic and are never promoted.

Digest revalidation narrows the evidence window; it does **not** prove atomic cross-filesystem binding, prevent swap-and-restore, or certify runtime delivery.

## Hostile fixtures

- exact-max artifact reaches EOF and earns a whole-artifact digest;
- max+1 rejects without prefix digest authority;
- invalid UTF-8 cannot become semantic index text;
- external content A → content B yields `CHANGED` artifact custody even while repository custody can remain stable;
- identical complete content can yield `STABLE` artifact custody.

## Current capability truth

- pure artifact-custody + emission policy source: **IMPLEMENTED_SOURCE**
- bounded exact artifact-observation primitive: **IMPLEMENTED_SOURCE**
- hostile regression source including external mutation/resource/UTF-8 cases: **REGRESSION_SOURCE / UNEXECUTED**
- existing provenance owner consumption: **NO**
- prior report-boundary patch: **REJECTED_UNSAFE / DO NOT APPLY** until it consumes both a coherent late repository observation and exact generated-index artifact custody
- tested: **NO**
- runtime UI / TalkBack / deployment / callability / execution / delivery / acceptance: **NO**

## Ownership

Compose only into `tools/try_forever_skill_provenance_probe.py`. Do not create a second provenance probe, serializer daemon, scheduler, recovery controller, Phone Hands lane, or P0 coordinator.

## P0 firewall

This skill is repository-evidence policy only. It does not consume or mutate the primary-phone surface, Phone Hands, recovery queues/relays, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.
