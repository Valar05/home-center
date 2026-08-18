# Heartbeat Skill Snapshot Certification

## Purpose
A bounded discovery result is not automatically current repository-skill authority. Certification is a separate global gate.

## Authority contract
- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Direct records may earn `repository_skill` authority only when `repositorySnapshot.status == STABLE_CLEAN` and any requested `--expected-head` binding has no mismatch.
- `UNSTABLE` snapshot or expected-head mismatch means **zero authority-facing skill records**. Diagnostic discoveries may be retained separately, but they must be labeled non-authoritative.
- Do not rely on `--strict` exit status as the only authority membrane. A non-strict caller must not be handed authoritative-looking records that contradict the report's own snapshot/head evidence.
- Failure is set-level and fail-closed; never first-wins or partial authority.

## Evidence discipline
Keep these states separate: discovered, certified-current, implemented source, tested, executed probe, runtime, deployed, callable, delivered, accepted.

Current source state for this heartbeat:
- supporting certification policy: **YES / SOURCE**
- hostile regression source: **YES / SOURCE / UNEXECUTED**
- existing provenance owner consumes certification policy: **NO**
- tested: **NO**
- runtime/deployed/callable/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, registry, index daemon, overlay controller, scheduler, Phone Hands lane, or P0 recovery owner may be created for this rule. Compose the existing provenance owner only. Phone/P0 surfaces are outside this skill.
