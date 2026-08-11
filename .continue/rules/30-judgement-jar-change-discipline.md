# Judgement Jar: Change Discipline

Status: active
Scope: repository edits and refactors

## Judgement

Small, inspectable changes are easier to verify and easier for a smaller local model to reason about correctly.

## Operating rule

- Prefer the smallest coherent patch that satisfies the commissioned outcome.
- Do not rewrite whole files when a targeted edit is sufficient.
- Preserve existing public contracts unless changing them is part of the mission.
- Do not mix unrelated cleanup with the requested change.
- Re-read every previously stated constraint before presenting a revision; a fix must not reintroduce a rejected approach.
- When generated code or an automated apply operation fails, inspect the actual file and retry from current repository truth rather than replaying the same patch blindly.

## File application rule

A failed filepath resolution is an application failure, not permission to guess a path. Resolve the actual path from the repository, then produce a fresh edit against that file.

## Stop condition

If the requested result cannot be produced without a broad rewrite, destructive migration, or contract break that was not commissioned, stop and surface the boundary.

## Evidence that can change this judgement

An explicit owner instruction requesting the larger refactor or contract change.
