# Heartbeat Skill Candidate Enumeration

## Purpose

Bound the repository-skill candidate set **before** per-file title or hash work. This skill exists because a bounded file parser is still vulnerable if discovery first materializes an unbounded list of candidate paths.

It owns source/evidence policy only. It owns no renderer, scheduler, phone lane, Phone Hands surface, P0 recovery chain, skill registry daemon, deployment path, or physical acceptance action.

## Canonical rule

For direct `skills/**/SKILL.md` discovery:

1. Complete the separate bounded filesystem traversal throat first.
2. Admit at most `MAX_SKILL_CANDIDATES = 2048` actual file candidates.
3. Store at most `limit + 1` candidate paths while determining overflow.
4. Sort only the already-bounded admitted set for deterministic downstream identity checks.
5. If max+1 is observed, fail the **entire** repository-skill discovery before title extraction or whole-file hashing.
6. Return no partial `SkillRecord` authority on overflow.

Partial authority is forbidden because an omitted later candidate could collide case-insensitively with an already-admitted path. "First 2048 look healthy" is not a complete repository identity claim.

## Failure shape

Candidate overflow is a structured repository discovery wound:

- `path = skills`
- `stage = enumeration`
- `error_type = SkillCandidateResourceLimitError`
- reason states that the count budget was exceeded and partial repository-skill authority is forbidden.

The result may still be emitted as diagnostic evidence, but it contains no repository-skill records from that incomplete discovery.

## Determinism

Do not regain determinism by calling `sorted(skills_root.rglob("SKILL.md"))`; that recreates both the old unbounded candidate-list wound and the now-repaired unbounded recursive traversal wound. The canonical probe performs one bounded traversal, accumulates only the bounded candidate set, then sorts the admitted candidates.

Exact-limit acceptance and max+1 rejection are different states. Zero budget rejects the first candidate. A negative configured budget is a programmer/configuration error, not a repository discovery result.

## What this bounds

This skill bounds **candidate count and candidate-path list memory**. The distinct filesystem traversal workload is now governed by `heartbeat-skill-filesystem-traversal-budget`; neither skill substitutes for the other.

Do not report the candidate count as the traversal count, and do not report a successful traversal as proof that candidate admission, title, hash, repository snapshot, runtime, or phone delivery succeeded.

## Regression source

`tools/test_try_forever_skill_candidate_enumeration.py` pins:

- exact-limit deterministic ordering;
- max+1 fail-closed overflow;
- no partial records on overflow;
- no title/hash calls after overflow;
- zero-budget rejection;
- negative-budget programmer-error behavior.

`tools/test_try_forever_skill_filesystem_traversal_budget.py` separately pins the traversal throat; it does not replace these candidate fixtures.

Regression source existing in GitHub is not TESTED. Only an authorized runner receipt can promote it.

## Composition

This skill composes into the existing `tools/try_forever_skill_provenance_probe.py` and its existing `discover_skills` owner. It must not create a second provenance probe or skill registry.

The order is:

`bounded filesystem traversal -> bounded candidate admission -> path identity/collision checks -> bounded title admission -> bounded exact whole-file SHA -> stable pre/post repository snapshot verdict`

## Capability membrane

Preserve independently:

`requested -> implemented source -> exact repository readback -> probe executed -> regression tested -> runtime UI consumed -> deployed -> callable -> executed -> delivered -> accepted`

Source code and regression fixtures are earlier states only. Nothing here clears Phone Runtime / Phone Hands / P0 gates.

## P0 / phone firewall

Do not consume or mutate Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance. If a P0 issue is discovered incidentally, record one concise finding for the canonical P0 owner and stop.

## Done

This skill may light only when candidate-enumeration truth materially changes: a count/list resource wound is bounded, overflow is made fail-closed, deterministic bounded ordering is repaired, or fresh evidence invalidates one of those claims. Traversal work belongs to its separate skill light. Otherwise this one stays dark.
