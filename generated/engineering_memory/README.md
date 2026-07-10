# Home Center Engineering Memory

This directory is the local-first engineering memory store for Home Center.

Records are append-only JSONL unless a tool explicitly writes a report artifact. The store is intentionally simple before it becomes cloud-backed or semantically indexed.

## Record Files

- `repositories.jsonl`: discovered repositories and current git state.
- `orientations.jsonl`: orientation report records.
- `artifacts.jsonl`: cataloged development artifacts.
- `workflow_runs.jsonl`: reusable workflow run records.
- `prompts.jsonl`: prompt asset records.
- `tools.jsonl`: executable capability records.
- `agents.jsonl`: stateless capability-agent records.
- `verification_runs.jsonl`: independent verification evidence.
- `edges.jsonl`: graph edges between records.

## Rules

- No anonymous artifacts.
- Every artifact should have source repo, workflow or generator, timestamp, hash, and dirty-state context when available.
- Chat history is not durable memory.
- Generated records are evidence, not automatic truth; consumers must inspect status and verification fields.
