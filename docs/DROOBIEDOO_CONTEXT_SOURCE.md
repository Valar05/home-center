# Droobiedoo Context Source

Droobiedoo is integrated into Home Center as a read-only context source, not as a separate MCP server.

## Architecture Position

- Droobiedoo is the canonical workspace context and provenance repository for project manifests, skills, doctrine, reports, generated artifacts, and freshness metadata.
- Home Center is the executable MCP surface. It exposes Droobiedoo through `drive_operation` registry entries prefixed with `droobiedoo.`.
- Simulation Frames are still Home Center's immutable, evidence-backed context lane. Droobiedoo task packets use the same bounded packet shape and provenance discipline, but the current implementation reads from the checked-in Droobiedoo index rather than creating a new Firestore frame or MCP boundary.
- She-Raw remains the runtime/default voice. She-Raw can consume Droobiedoo context packets, but Droobiedoo is not a brain jar and does not replace She-Raw.
- Command Center remains the execution and dispatch layer. Droobiedoo lookup results can inform a Command Center job, but Droobiedoo never dispatches, mutates, or follows through on work.

## Runtime Source

Home Center reads `functions/context_sources/droobiedoo_context_index.json`, a generated copy of Droobiedoo's `generated/context/droobiedoo_context_index.json`.

The MCP-facing side is intentionally read-only:

- `remoteMutationAllowed` is `false`.
- all `droobiedoo.*` registry entries have `write: false`.
- `scripts/sync_workspace_artifacts.py` is indexed only as local provenance and is marked `remoteCallable: false`.
- `sync_workspace_artifacts.py` is not exposed as a remote mutation tool.

## Operations

Use `drive_operation` with these operation names:

- `droobiedoo.context_health`
- `droobiedoo.context_search`
- `droobiedoo.project_resolve`
- `droobiedoo.task_context_packet`
- `droobiedoo.skill_match`
- `droobiedoo.artifact_search`
- `droobiedoo.provenance_lookup`

These operations support project resolution, bounded task packets, skill matching, artifact search, provenance lookup, and stale-data reporting without requiring a new MCP connector installation.

## Refresh Procedure

Refresh is local-maintenance only:

1. Run `python3 tools/build_context_index.py` in Droobiedoo.
2. Copy `droobiedoo/generated/context/droobiedoo_context_index.json` to `home-center/functions/context_sources/droobiedoo_context_index.json`.
3. Run the Droobiedoo and Home Center contract tests.

Do not expose the sync script or the refresh procedure as a remote MCP action.
