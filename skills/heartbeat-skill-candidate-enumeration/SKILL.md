# Heartbeat Skill Candidate Enumeration

## Purpose

Bound the repository-skill candidate set **before** per-file title or hash work, and require every named `SKILL.md` candidate to be one ordinary non-redirecting file. This skill exists because a bounded parser is still unsafe if discovery first materializes an unbounded candidate list or follows one underlying file through multiple repository path aliases.

It owns source/evidence policy only. It owns no renderer, scheduler, phone lane, Phone Hands surface, P0 recovery chain, skill registry daemon, deployment path, or physical acceptance action.

## Canonical rule

For direct `skills/**/SKILL.md` discovery:

1. Complete the separate bounded filesystem traversal throat first.
2. Treat a directory entry named `SKILL.md` as a candidate **only** when it is an ordinary file under no-follow inspection.
3. A `SKILL.md` symlink, redirector, directory, or other non-ordinary topology fails the **entire** candidate admission with `SkillCandidateTopologyError`; do not follow it, silently skip it, or let first-path-wins choose an owner.
4. Admit at most `MAX_SKILL_CANDIDATES = 2048` ordinary file candidates.
5. Store at most `limit + 1` candidate paths while determining overflow.
6. Sort only the already-bounded admitted set for deterministic downstream identity checks.
7. If topology is ambiguous or max+1 is observed, fail the **entire** repository-skill discovery before title extraction or whole-file hashing.
8. Return no partial `SkillRecord` authority after either global candidate-set failure.

Partial authority is forbidden because an omitted or followed alias can hide identity collisions. "The first candidates look healthy" is not a complete repository identity claim.

## Failure shapes

Candidate overflow is a structured repository discovery wound:

- `path = skills`
- `stage = enumeration`
- `error_type = SkillCandidateResourceLimitError`
- reason states that the count budget was exceeded and partial repository-skill authority is forbidden.

Candidate file-topology ambiguity is a distinct structured wound:

- `path = bounded lexical path of the named SKILL.md entry`
- `stage = identity`
- `error_type = SkillCandidateTopologyError`
- reason states that `SKILL.md` must be an ordinary non-redirecting file and partial repository-skill authority is forbidden.

Both wounds may be emitted as diagnostic evidence, but neither result contains repository-skill records from the incomplete discovery.

## Why silent skip is forbidden

A symlink such as `skills/alias/SKILL.md -> ../real/SKILL.md` can make one underlying file appear under two repository path identities when file checks follow links. Later outside-root validation does not repair the in-root alias case. Silently ignoring a named `SKILL.md` is also insufficient because complete discovery can no longer prove that no omitted path could collide with an admitted identity.

The admission boundary therefore sits at directory-entry topology: no-follow ordinary file or fail closed.

## Determinism

Do not regain determinism by calling `sorted(skills_root.rglob("SKILL.md"))`; that recreates both the old unbounded candidate-list wound and the repaired unbounded recursive traversal wound. The canonical probe performs one bounded traversal, rejects named candidate redirectors/non-ordinary topology, accumulates only the bounded ordinary candidate set, then sorts the admitted candidates.

Exact-limit acceptance and max+1 rejection are different states. Zero budget rejects the first ordinary candidate. A negative configured budget is a programmer/configuration error, not a repository discovery result.

## What this bounds

This skill bounds **candidate count, candidate-path list memory, and candidate file-topology ownership**. The distinct filesystem traversal workload is governed by `heartbeat-skill-filesystem-traversal-budget`; neither skill substitutes for the other.

Do not report successful traversal as proof that candidate topology/count, title, hash, repository snapshot, runtime, or phone delivery succeeded.

## Regression source

`tools/test_try_forever_skill_candidate_enumeration.py` pins:

- exact-limit deterministic ordering;
- max+1 fail-closed overflow;
- no partial records on overflow;
- no title/hash calls after overflow;
- in-root `SKILL.md` symlink-alias rejection with zero partial authority;
- named `SKILL.md` directory/non-ordinary topology rejection before healthy-peer authority;
- zero-budget rejection;
- negative-budget programmer-error behavior.

The topology fixtures are intentionally **regression source** against the currently observed owner until authenticated readback proves the proposed owner delta has been applied. Source existing in GitHub is not TESTED; only an authorized runner receipt can promote it.

`tools/test_try_forever_skill_filesystem_traversal_budget.py` separately pins the traversal throat; it does not replace these candidate fixtures.

## Composition

This skill composes into the existing `tools/try_forever_skill_provenance_probe.py` and its existing `discover_skills` owner. It must not create a second provenance probe or skill registry.

The intended order is:

`repository-owned root -> bounded traversal -> ordinary/no-follow SKILL.md topology -> bounded candidate admission -> path identity/collision checks -> bounded title admission -> bounded exact whole-file SHA -> stable pre/post repository snapshot verdict`

## Current owner evidence

At the 2026-08-18 1200 heartbeat, authenticated readback of owner blob `e3627e342150c48f38099bb68fb118b3c54f2bf4` still uses `entry.is_file(follow_symlinks=True)` for named `SKILL.md` entries. Therefore:

- regression source: **YES**;
- exact base-blob-locked owner patch: **YES / PROPOSED_NOT_APPLIED** at `patches/try-forever-skill-file-topology.patch`;
- existing-owner file-topology consumption: **NO**;
- TESTED/runtime/deployed/delivered/accepted: **NO**.

Do not upgrade those states because the patch exists.

## Capability membrane

Preserve independently:

`requested -> implemented supporting source -> exact repository readback -> existing-owner source wired -> probe executed -> regression tested -> runtime UI consumed -> deployed -> callable -> executed -> delivered -> accepted`

No earlier state implies a later one. Nothing here clears Phone Runtime / Phone Hands / P0 gates.

## P0 / phone firewall

Do not consume or mutate Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, P0 coordination, or physical acceptance. If a P0 issue is discovered incidentally, record one concise finding for the canonical P0 owner and stop.

## Done

This skill may light only when candidate-enumeration or candidate-topology truth materially changes: a count/list resource wound is bounded, a named candidate redirector/non-ordinary topology is made fail-closed, overflow is repaired, deterministic bounded ordering changes, or fresh evidence invalidates one of those claims. Traversal work belongs to its separate skill light. Otherwise this one stays dark.
