# Heartbeat Skill Snapshot Certification

## Purpose
A bounded discovery result is not automatically current repository-skill authority. Certification is a separate global gate.

## Authority contract
- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Direct records may earn `repository_skill` authority only when `repositorySnapshot.status == STABLE_CLEAN` and any requested `--expected-head` binding has no mismatch.
- `UNSTABLE` snapshot or expected-head mismatch means **zero authority-facing skill records**. Diagnostic discoveries may be retained separately, but they must be labeled non-authoritative.
- Do not rely on `--strict` exit status as the only authority membrane. A non-strict caller must not be handed authoritative-looking records that contradict the report's own snapshot/head evidence.
- Failure is set-level and fail-closed; never first-wins or partial authority.
- The current owner report schema is `try-forever-skill-provenance.v5`; `discoveredSkillCount` remains diagnostic discovery breadth while `skillCount`/`skills` are emission-authoritative records only.

## Observation contract
The certification interval needs two distinct repository observations: immediately before direct skill discovery and immediately after it.

The repository already owns a stronger observation organ at `tools/try_forever_repository_emission_observation.py`: one bounded `git status --porcelain=v2 --branch --untracked-files=normal --ignore-submodules=none` process yields both canonical HEAD and cleanliness, keeps porcelain paths as opaque bytes, and fails closed on timeout or ambiguous OID evidence.

The current provenance owner still builds the **initial** discovery snapshot from separate `git_head()` and `git_dirty()` subprocesses. That is weaker than the existing one-process organ and can also hang without the emission observer's deadline. The desired owner composition is therefore:

1. one existing bounded observation before discovery;
2. direct `discover_skills(...)`;
3. a second bounded observation after discovery;
4. `assess_repository_snapshot(...)` compares those two observations;
5. the later final-emission observation remains a third, independent preservation-only custody check.

This narrows each observation. It does **not** prove atomic repository binding across discovery, swap-and-restore immunity, or identity-reuse immunity.

## Evidence discipline
Keep these states separate: discovered, certified-current, implemented source, tested, executed probe, runtime, deployed, callable, delivered, accepted.

Current source state for this heartbeat:
- supporting certification policy: **YES / SOURCE**
- existing provenance owner consumes certification policy: **YES / SOURCE_WIRED**
- current owner schema: **try-forever-skill-provenance.v5**
- authenticated owner blob: **e1d10fb4c917813bc89780486c79a5e2d2bc4bea**
- one-process final-emission observation owner wiring: **YES / SOURCE_WIRED**
- one-process initial before/after discovery observation owner wiring: **NO**
- RED owner-boundary regression source: `tools/test_try_forever_provenance_initial_snapshot_owner_boundary.py` **YES / REGRESSION_SOURCE / UNEXECUTED**
- exact owner delta: `patches/try-forever-provenance-initial-snapshot-observation.patch` **YES / PROPOSED_NOT_APPLIED**
- tested: **NO**
- runtime/deployed/callable/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, registry, index daemon, overlay controller, scheduler, Phone Hands lane, or P0 recovery owner may be created for this rule. Compose the existing provenance owner and existing repository-observation organ only. Phone/P0 surfaces are outside this skill.
