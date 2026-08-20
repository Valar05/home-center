# Heartbeat Skill Tracked Authority

## Purpose

Filesystem discovery is not Git authority. An ordinary `skills/**/SKILL.md` can exist in the checkout without being tracked, and ignored untracked files do not appear in ordinary `git status --untracked-files=normal` output. Such a file must not become `repository_skill` authority merely because the surrounding tracked checkout looks clean.

## Contract

- The sole provenance owner remains `tools/try_forever_skill_provenance_probe.py`.
- Every discovered repository-skill identity must be admitted against a Git-tracked identity set before certification can authorize records.
- One untracked candidate fails the whole repository-skill authority set; partial first-N or healthy-peer authority is forbidden for this global custody gate.
- Comparison is exact repository-relative identity. Case folding, path rewriting, or first/last-wins aliasing must not convert an untracked candidate into a tracked one.
- This gate is independent of dirty-worktree observation. A clean status observation is not evidence that ignored filesystem candidates are tracked.
- Tracked-path observation must query only the already-discovered candidate set, with literal Git pathspecs, a finite candidate/argument budget, a finite process deadline, and the existing sanitized Git subprocess environment. It must not perform an unbounded repository-wide tracked-file census merely to answer candidate custody.
- Git output outside the exact literal candidate set fails closed; platform/config case folding must not silently donate canonical identity to a differently-cased filesystem candidate.
- This doctrine owns no phone surface, P0 recovery lane, renderer, scheduler, or deployment authority.

## Supporting source

- `tools/try_forever_skill_tracked_authority.py` provides the pure exact-set admission policy.
- `tools/test_try_forever_skill_tracked_authority.py` covers all-tracked success, an ignored-style untracked candidate, exact-case mismatch, and empty candidate behavior.
- `tools/try_forever_tracked_skill_observation.py` provides a bounded candidate-only `git ls-files -z --full-name` observation using literal pathspecs and the existing Git environment scrubber.
- `tools/test_try_forever_tracked_skill_observation.py` covers empty-set no-I/O, literal pathspecs, sanitized environment, untracked-subset composition, case/broadened-output rejection, resource bounds, invalid candidate identity, command failure, and timeout.

All fixtures are **REGRESSION_SOURCE / UNEXECUTED**. The new observation source acquires a bounded exact tracked subset, but the sole provenance owner does not yet consume that observation or the pure tracked-authority gate.

## Current capability truth

- ignored/untracked candidate wound identified: **YES**
- pure tracked-set admission policy: **YES / SOURCE**
- bounded candidate-only Git tracked-path observation: **YES / SUPPORTING_SOURCE**
- sanitized/literal/bounded tracked observation regression source: **YES / UNEXECUTED**
- existing provenance owner consumes tracked observation: **NO**
- existing provenance owner consumes tracked-set gate: **NO**
- tested: **NO**
- runtime UI / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## Ownership / firewall

No second provenance probe, filesystem watcher, repository daemon, Phone Hands lane, or P0 owner may be created. The next valid implementation step is composition into the existing provenance owner: observe the exact discovered candidate set, feed that observation to `require_tracked_skill_candidates(...)`, and fail the whole repository-skill authority set before certification when observation is unavailable or any candidate is untracked. Require authenticated owner readback before any capability promotion.
