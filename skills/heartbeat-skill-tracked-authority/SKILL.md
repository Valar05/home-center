# Heartbeat Skill Tracked Authority

## Purpose
Filesystem discovery is not Git authority. An ordinary `skills/**/SKILL.md` can exist in the checkout without being tracked, and ignored untracked files do not appear in ordinary `git status --untracked-files=normal` output. Such a file must not become `repository_skill` authority merely because the surrounding tracked checkout looks clean.

## Contract
- The sole provenance owner remains `tools/try_forever_skill_provenance_probe.py`.
- Every discovered repository-skill identity must be admitted against a Git-tracked identity set before title/hash authority-facing content work and before certification can authorize records.
- One unavailable tracked observation or one untracked candidate fails the whole repository-skill authority set; partial first-N or healthy-peer authority is forbidden for this global custody gate.
- Comparison is exact repository-relative identity. Case folding, path rewriting, or first/last-wins aliasing must not convert an untracked candidate into a tracked one.
- This gate is independent of dirty-worktree observation. A clean status observation is not evidence that ignored filesystem candidates are tracked.
- Tracked-path observation queries only the already-discovered candidate set, with literal Git pathspecs, finite candidate/argument budgets, a finite process deadline, and the existing sanitized Git subprocess environment. It does not perform a repository-wide tracked-file census.
- Git output outside the exact literal candidate set fails closed; platform/config case folding must not silently donate canonical identity to a differently-cased filesystem candidate.
- This doctrine owns no phone surface, P0 recovery lane, renderer, scheduler, or deployment authority.

## Existing-owner composition
The sole provenance owner now composes the existing organs directly inside `discover_skills(...)` after deterministic candidate/collision admission and before per-file content work:

1. `observe_tracked_skill_candidates(repo_root, relative_candidates)`;
2. fail closed if the bounded observation is not `OBSERVED`;
3. `require_tracked_skill_candidates(relative_candidates, tracked_paths)`;
4. fail the whole candidate authority set when any exact candidate is untracked; and only then
5. enter per-file identity/title/hash authority work.

No second Git query implementation, provenance probe, filesystem watcher, or repository daemon was created.

## Source evidence
- `tools/try_forever_skill_tracked_authority.py`: pure exact-set admission policy.
- `tools/test_try_forever_skill_tracked_authority.py`: pure policy regression source.
- `tools/try_forever_tracked_skill_observation.py`: bounded candidate-only `git ls-files -z --full-name` observation using literal pathspecs and the existing Git environment scrubber.
- `tools/test_try_forever_tracked_skill_observation.py`: supporting observation regression source.
- `tools/test_try_forever_tracked_skill_owner_boundary.py`: existing-owner composition/order regression source.
- authenticated owner blob after wiring: `11b29954654c7c8b21fa8f3f3759eeddf32e6e8e`.

All fixtures remain **REGRESSION_SOURCE / UNEXECUTED** until deterministic execution evidence exists.

## Current capability truth
- ignored/untracked candidate wound identified: **YES**
- pure tracked-set admission policy: **YES / SOURCE**
- bounded candidate-only Git tracked-path observation: **YES / SOURCE**
- existing provenance owner consumes tracked observation: **YES / SOURCE_WIRED**
- existing provenance owner consumes tracked-set gate: **YES / SOURCE_WIRED**
- owner gate occurs before per-file title/hash authority work: **YES / SOURCE_WIRED**
- owner regression source: **YES / UNEXECUTED**
- tested: **NO**
- runtime UI / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## Ownership / firewall
No second provenance probe, filesystem watcher, repository daemon, Phone Hands lane, or P0 owner may be created. The existing owner and existing tracked-observation/policy organs are authoritative. Phone/P0 surfaces remain outside this skill.
