# Simulation MCP Compiler

Chat assembles. The MCP compiler preserves.

This feature is intentionally MCP-first. Home Center's Android UI can inspect these artifacts later, but the executable v1 surface is the remote MCP tool `simulation_operation` so ChatGPT and future agents can build and query frames directly.

Do not use Sheets, workbooks, tabs, or manual spreadsheet entry for simulation context compilation. A simulation frame is an immutable, provenance-backed, queryable context system.

## Workflow

1. `simulation_project_create` creates or returns a durable project.
2. `simulation_source_register` records Drive, Docs, GitHub, URL, note, local document, or prior-simulation references without forcing immediate full ingestion.
3. `simulation_reference_begin` opens a resumable reference compilation.
4. `simulation_reference_append` appends chunks idempotently by `compilationId`, `sequence`, and content hash.
5. `simulation_reference_finalize` freezes the compilation hash.
6. `build_simulation_frame` parses Markdown headings, metadata lines, source annotations, uncertainty, and contradictions into immutable frame records.
7. `simulation_frame_query` retrieves evidence-backed records from the selected frame.
8. `simulation_context_packet` returns a bounded agent-ready packet with provenance and invention guards.
9. `run_simulation_frame` returns a deterministic frame-grounded handoff for an agent continuation; it does not silently invent canon or resolve conflicts.

## Storage

The v1 compiler uses Firestore collections behind the existing Home Center MCP app:

- `simulationProjects`
- `simulationSources`
- `simulationReferenceCompilations`
- `simulationReferenceChunks`
- `simulationFrames`
- `simulationFrameRecords`
- `simulationFrameRecordSources`
- `simulationFrameConflicts`
- `simulationFrameTerms`
- `simulationAudit`
- `simulationRecoveryCheckpoints`

Firestore is used because the compiler must be executable from ChatGPT through MCP. A local SQLite mirror can be added later for offline Android inspection if the UI needs it.

## Reference Format

References should be readable Markdown with optional metadata lines after headings:

```markdown
## Entity: Lexen Vigil
id: character.lexen_vigil
type: character
confidence: high
rank_at_normandy: sergeant

Lexen is a Sherman commander in the Western Allied campaign.

Sources:
- drive:1abc123
- github:Valar05/example/path/to/file.md#L20-L45
```

The compiler tolerates partial documents. Unknown structure becomes `passage` records instead of being discarded.

## Retrieval Contract

Every query result includes frame identity, frame version, matching explanation, confidence, source references, and unresolved conflict warnings where available. Context packets instruct future agents not to invent missing canon and not to silently reconcile contradictions.
