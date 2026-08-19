# Heartbeat Report-Emission Snapshot Revalidation

## Purpose
A clean repository snapshot observed around direct skill discovery can become stale while later generated-index inspection and report assembly are still running. Authority should not escape without one final custody check.

## Contract
- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- A late revalidation may certify only that the same clean HEAD is observed again immediately before report emission.
- Missing final HEAD, changed HEAD, unknown cleanliness, or a newly dirty checkout fail closed.
- A final clean observation may narrow the late custody window but **does not prove atomic repository binding**. Swap-and-restore, filesystem identity reuse, or mutation after the final observation remain outside the claim.
- The final check must not upgrade an earlier uncertified snapshot. No certified HEAD means no late revalidation can manufacture authority.
- If integrated, a failed final gate must zero authority-facing repository-skill records rather than leave an earlier certification floating forward.

## Evidence discipline
Keep discovery-time snapshot certification, final-emission observation, atomic binding, source implementation, regression source, execution, tests, runtime, deployment, delivery, and acceptance separate.

Current state:
- pure final-emission revalidation policy: **YES / SOURCE**
- hostile regression source: **YES / SOURCE / UNEXECUTED**
- existing provenance owner consumes the policy: **NO**
- atomic cross-platform binding: **NO**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, watcher, repository daemon, scheduler, Phone Hands lane, or P0 owner may be created for this rule. Compose the existing provenance owner only. Phone/P0 surfaces are outside this skill.
