# Heartbeat Generated-Index Emission Custody

## Purpose

Keep a generated index's `VERIFIED_CURRENT` claim on the same side of the final repository-custody gate as direct repository-skill authority.

## Law

A generated index may be inspected against the certified clean discovery snapshot. If a later report-emission HEAD/cleanliness revalidation is not `STABLE_CLEAN`, an earlier `VERIFIED_CURRENT` result must be withheld as `UNRESOLVED` in the authority-facing report.

Do not re-read or re-verify the generated index after the declared final repository-custody observation merely to recover a green currentness claim. That creates new evidence work after the supposed final gate. Preserve already-negative `STALE`/`UNRESOLVED` diagnostics without promoting them.

## Evidence membrane

- pure policy source present: IMPLEMENTED_SOURCE only
- hostile regression source present: REGRESSION_SOURCE only until executed
- owner patch present: PROPOSED, not owner wiring
- authenticated owner readback decides whether the existing provenance owner consumes the policy
- repository source never proves runtime UI, TalkBack, deployment, callability, execution, delivery, or acceptance

## Ownership

Compose only into `tools/try_forever_skill_provenance_probe.py`. Do not create a second provenance probe, serializer daemon, scheduler, recovery controller, Phone Hands lane, or P0 coordinator.

## P0 firewall

This skill is repository-evidence policy only. It does not consume or mutate the primary-phone surface, Phone Hands, recovery queues/relays, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.
