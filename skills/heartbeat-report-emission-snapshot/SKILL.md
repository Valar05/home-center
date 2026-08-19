# Heartbeat Report-Emission Snapshot Revalidation

## Purpose
A clean repository snapshot observed around direct skill discovery can become stale while later generated-index inspection and report assembly are still running. Authority should not escape without one final custody check.

## Contract
- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- A late revalidation may certify only that the same clean HEAD is observed again immediately before authority-facing report assembly.
- Missing final HEAD, changed HEAD, unknown cleanliness, or a newly dirty checkout fail closed.
- A final clean observation may narrow the late custody window but **does not prove atomic repository binding**. Swap-and-restore, filesystem identity reuse, or mutation after the final observation remain outside the claim.
- The final check must not upgrade an earlier uncertified snapshot. No certified HEAD means no late revalidation can manufacture authority.
- If the final gate fails after an earlier certification, authority-facing repository-skill records must be zeroed and the report must name an emission-snapshot failure rather than leave the earlier certification floating forward.
- Strict mode must treat a failed final-emission gate as failure.
- Owner integration changes the durable report contract and therefore requires schema `try-forever-skill-provenance.v4` rather than silently mutating v3.

## Evidence discipline
Keep discovery-time snapshot certification, final-emission observation, atomic binding, source implementation, regression source, execution, tests, runtime, deployment, delivery, and acceptance separate.

Current state:
- pure final-emission revalidation policy: **YES / SOURCE**
- hostile policy regression source: **YES / SOURCE / UNEXECUTED**
- owner-integration regression source: **YES / SOURCE / UNEXECUTED**
- exact existing-owner integration delta: **YES / PROPOSED_NOT_APPLIED**
- proposed report schema: **v4**
- existing provenance owner consumes the policy: **NO**
- authenticated current owner blob: **afe2b29eb7f4daf2ebf79c483c2e7d3abac9ed6a**
- atomic cross-platform binding: **NO**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, watcher, repository daemon, scheduler, Phone Hands lane, or P0 owner may be created for this rule. Compose the existing provenance owner only. Phone/P0 surfaces are outside this skill.
