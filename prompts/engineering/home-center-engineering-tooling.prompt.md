# Home Center Engineering Tooling Prompt

## Purpose

Orient an AI or human engineer inside Home Center's durable engineering workspace without relying on chat history. Use repository truth and engineering memory to decide what changed, why it changed, what evidence exists, and what should happen next.

## Inputs

- Target repository path or owner/repo identifier.
- Optional workflow id.
- Optional artifact path or evidence path.
- Optional user question about current engineering state.

## Required Tools

- Local filesystem read access.
- Git CLI when the target is a git repo.
- Home Center engineering orientation records when present.
- Home Center artifact catalog when present.
- Project-native validators when acceptance depends on behavior.

## Workflow Steps

1. Read the target repository orientation files first.
2. Discover git state, docs, build systems, validation commands, artifacts, and recent evidence.
3. Prefer existing engineering memory records over chat recollection.
4. If evidence is missing, name the missing record and the smallest command that would create it.
5. Separate facts, risks, unknowns, and next actions.

## Outputs

- A concise orientation or answer grounded in repository artifacts.
- Links or paths to supporting evidence records.
- Any new artifact or workflow ids created during the run.
- Explicit unknowns and next verification commands.

## Expected Artifacts

- `generated/engineering_memory/orientations/*.json`
- `generated/engineering_memory/orientations/*.md`
- `generated/engineering_memory/repositories.jsonl`
- `generated/engineering_memory/artifacts.jsonl`
- `generated/engineering_memory/workflow_runs.jsonl`
- `generated/engineering_memory/edges.jsonl`

## Acceptance Criteria

- Does not depend on chat history.
- Names repository path, branch, commit, and dirty-state evidence when available.
- Distinguishes source checks, provider checks, visual/user-path checks, and artifact validation.
- Does not claim semantic search, deployment success, provider access, or visual correctness without evidence.
