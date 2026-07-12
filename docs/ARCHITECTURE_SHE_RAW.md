# She-Raw Architecture

## Shape

```text
Remote MCP client
  -> sheRawMcp Firebase Function
    -> Invocation Gate
    -> Retrieval Engine
    -> Model Adapter
    -> Critique Engine
    -> Introspection Engine
    -> Learning Engine
    -> Corpus Sync Surface
    -> Firestore Persistence
    -> Audit Events
```

This stays one deployable service. The modules have not earned separate services.

## Persistence

Repo truth currently uses Firebase Functions and Firestore for cloud MCP state. The She-Raw vertical slice follows that existing production substrate instead of introducing PostgreSQL beside it. PostgreSQL with JSONB/full-text search remains the preferred future production store if She-Raw becomes independent from Home Center.

Firestore collections use the `sheRaw*` prefix and are append-oriented where failures or superseded records matter.

## Model Adapter

The model layer is replaceable. The slice records provider, model, prompt version, retrieval set, request size, response size, latency, and structured-output validity in `sheRawModelRuns`.

The default adapter is deterministic for local contract tests. A production adapter should require structured JSON, retry invalid structure once, store failures, and return typed errors rather than inventing success.

## GitHub Boundary

The current repo has token-backed GitHub tools. She-Raw docs preserve the product requirement that production corpus sync should use a least-privilege private GitHub App with Metadata read, Contents read/write, and Pull requests read/write only when promotion PRs are implemented.
