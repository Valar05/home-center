# Heartbeat Skill Tracked Authority

## Purpose

Filesystem discovery is not Git authority. An ordinary `skills/**/SKILL.md` can exist in the checkout without being tracked, and ignored untracked files do not appear in ordinary `git status --untracked-files=normal` output. Such a file must not become `repository_skill` authority merely because the surrounding tracked checkout looks clean.

## Contract

- The sole provenance owner remains `tools/try_forever_skill_provenance_probe.py`.
- Every discovered repository-skill identity must be admitted against a Git-tracked identity set before certification can authorize records.
- One untracked candidate fails the whole repository-skill authority set; partial first-N or healthy-peer authority is forbidden for this global custody gate.
- Comparison is exact repository-relative identity. Case folding, path rewriting, or first/last-wins aliasing must not convert an untracked candidate into a tracked one.
- This gate is independent of dirty-worktree observation. A clean status observation is not evidence that ignored filesystem candidates are tracked.
- A future tracked-path observation must itself be bounded, environment-isolated, deterministic, and composed into the existing provenance owner. Do not create a second provenance probe or watcher.
- This doctrine owns no phone surface, P0 recovery lane, renderer, scheduler, or deployment authority.

## Supporting source

- `tools/try_forever_skill_tracked_authority.py` provides a pure exact-set admission policy.
- `tools/test_try_forever_skill_tracked_authority.py` covers all-tracked success, an ignored-style untracked candidate, exact-case mismatch, and empty candidate behavior.

These fixtures are **REGRESSION_SOURCE / UNEXECUTED**. The supporting policy does not acquire the Git-tracked set and therefore does not by itself close the owner seam.

## Current capability truth

- ignored/untracked candidate wound identified: **YES**
- pure tracked-set admission policy: **YES / SOURCE**
- regression source: **YES / UNEXECUTED**
- bounded Git tracked-path observation: **NO**
- existing provenance owner consumes tracked-set gate: **NO**
- tested: **NO**
- runtime UI / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## Ownership / firewall

No second provenance probe, filesystem watcher, repository daemon, Phone Hands lane, or P0 owner may be created. The next valid implementation step is a bounded tracked-path observation composed into the existing owner, with exact authenticated readback before any capability promotion.
