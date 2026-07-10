# Drive Bridge Migration Plan

## Current Repository Truth

Home Center contains the active Drive Bridge implementation in Firebase Functions:

- `functions/home_center_mcp.js` owns the MCP app, OAuth metadata, Streamable HTTP transport, Drive/Docs/Sheets MCP tools, and shared Drive Bridge create helpers.
- `functions/index.js` exports the ChatGPT Action endpoints, hosted OpenAPI endpoint, and real Google sandbox smoke endpoint.
- `openapi.chatgpt.yaml` and `functions/openapi.chatgpt.yaml` define the Action contract imported by ChatGPT.
- `tools/drive_bridge_create_tools_test.mjs` verifies folder/doc creation with mocked Google APIs and mocked Firestore audit storage.
- `tools/home_center_metal_prompt_smoke.mjs` can run deployed real-provider sandbox checks.

## Existing Home_Bridge Contract

Default public tools:

- `health`
- `drive_search`
- `drive_read`
- `docs_append`
- `sheets_search`
- `sheets_read`
- `drive_create_folder`
- `docs_create`

The scalable bridge path is `drive_operation`: call `capabilities` for `operationRegistry`, then invoke operations by name without waiting for ChatGPT to refresh top-level MCP tools. The bridge also exposes audited `workbook_import_xlsx` for Excel workbook migration into native Google Sheets by using Google Drive conversion rather than manual sheet reconstruction. Extended MCP tools also include audited `sheets_create` and `sheets_update_values` when `HOME_CENTER_MCP_EXTENDED_TOOLS=true`. No Sheets delete/trash tool is exposed.

### No-Reinstall Discovery Contract

Future agents should not require a connector reinstall for ordinary Home Drive backend additions. The stable discovery path is:

1. Call `health` if only a minimal tool is available.
2. Call `capabilities` when available.
3. Read `capabilities.operationRegistry.operations`.
4. Execute supported mutations through `drive_operation` with a stable `requestId`.

For Excel migration, the normal ChatGPT path is not Base64 and not a local `/mnt/data` path. If the workbook is already in Drive, call `drive_operation` with `operation=workbook_import_xlsx` and pass `sourceFileId`, or `sourceFileName` plus `sourceFolderId`. Use `workbookBase64` only when the MCP client can provide the complete XLSX bytes. If a workbook exists only as a ChatGPT attachment and the runtime has no typed file-bytes handoff, first place the workbook in Drive, then import it by Drive ID or name.


The broader operator tools are behind `HOME_CENTER_MCP_EXTENDED_TOOLS=true` and are not part of the ChatGPT connector surface until separately hardened. The public bridge must not expose delete, trash, or restore tools for this v1 creation flow.

## Auth and Secret Handling

- MCP uses Home Center as an OAuth authorization server and stores bridge access context server-side.
- ChatGPT Action endpoints use Google OAuth bearer tokens directly.
- Google OAuth client secrets remain Firebase/Cloud secrets, not git.
- The local secret scanner remains part of `tools/run_regression_tests.sh`.

## Audit Logging

- `docs_append` keeps its existing `actionAudit` write.
- `drive_create_folder` and `docs_create` write `driveBridgeAudit` entries with request ID, actor, operation, target ID, summary/result, and metadata.
- Supplied `requestId` values are idempotency keys for successful create operations.

## Keep

- Structured Drive query construction; no raw Drive query endpoint.
- Stateless MCP transport for Cloud Run.
- Small default ChatGPT connector surface; extended operator tools are opt-in by environment flag.
- Existing OAuth challenge and metadata endpoints.
- Existing provider-smoke doctrine: real Drive/Docs behavior must be proved inside the sandbox.

## Cut

- Public delete/trash/restore tools are not part of this v1 surface.
- Broad autonomous Drive organization remains out of scope.
- Android/Home Center life-ops tools are source material only, not the Drive Bridge contract.

## Target Architecture

One shared Drive Bridge implementation sits behind both MCP tools and ChatGPT Action endpoints. Wrappers should stay thin and call the shared helpers so tool behavior, audit, idempotency, and validation do not drift.

## API / MCP Contract

### Stable Operation Registry

Top-level MCP tools should stay stable. New Drive Bridge mutations should be added as operations in `capabilities.operationRegistry.operations` and invoked through `drive_operation` with `operation` plus operation-specific `args`. Direct top-level tools may remain as compatibility aliases, but future ChatGPT agents should not need to reinstall the connector for every backend operation addition.


### `workbook_import_xlsx`

Purpose: migrate an uploaded `.xlsx` workbook into a native Google Sheets spreadsheet.

Behavior:

- Requires `requestId`.
- Accepts `sourceFileId` for an existing Drive `.xlsx`, `sourceFileName` plus optional `sourceFolderId` for Drive resolution, or `workbookBase64` when a client can provide uploaded bytes.
- Uses Google Drive conversion with target MIME `application/vnd.google-apps.spreadsheet`; it does not recreate tabs through repeated value updates.
- Preserves worksheet order, worksheet names, populated values, formulas, merges, freeze panes, and basic formatting to the extent Google Drive conversion supports them.
- Returns `spreadsheetId`, tab names, warnings, populated-cell counts, optional source/destination count diffs, metadata, and the audit entry.
- Records `workbook.importXlsx` in `driveBridgeAudit` and `actionAudit`.

Verification: `tools/workbook_import_xlsx_acceptance.py /storage/emulated/0/Download/Lexen_Vigil_Judgment_Engine.xlsx` parses source tabs/cell counts, calls the bridge operation, and reports missing destination tabs or count diffs.

### `drive_create_folder`

Input:

```json
{"name":"Tanks for the Memories v2","parentFolderId":"optional","requestId":"optional","callerNote":"optional"}
```

Output includes `folderId`, `name`, `webViewLink`, `parentFolderId`, `metadata`, and `auditRequestId`.

### `docs_create`

Input:

```json
{"title":"Tanks for the Memories v2 — Story Bible","parentFolderId":"optional","initialText":"optional","requestId":"optional","callerNote":"optional"}
```

Output includes `documentId`, `title`, `webViewLink`, `parentFolderId`, `metadata`, and `auditRequestId`.

## Safety Rules

- No public delete/trash/restore tool in v1.
- No raw Drive query endpoint.
- Every write must leave an audit trail.
- Creation writes are idempotent when a `requestId` is supplied.
- Real provider tests must create only inside `Home Center Smoke Sandbox/HC_SMOKE_RUN_*` and clean up the smoke run folder.

## Implementation Phases

1. Add shared create helpers and MCP tools.
2. Add ChatGPT Action endpoints and OpenAPI paths.
3. Add mock tests and regression contract checks.
4. Deploy MCP, Action endpoints, and hosted OpenAPI.
5. Run real sandbox smoke for folder creation, doc creation, append, readback verification, audit IDs, and cleanup.

## Verification Note

Files changed in this phase:

- `functions/home_center_mcp.js`
- `functions/index.js`
- `openapi.chatgpt.yaml`
- `functions/openapi.chatgpt.yaml`
- `README.md`
- `tools/drive_bridge_create_tools_test.mjs`
- `tools/home_center_regression_tests.py`
- `tools/run_regression_tests.sh`
- `tools/home_center_metal_prompt_smoke.mjs`
- `docs/DRIVE_BRIDGE_MIGRATION_PLAN.md`

Tests and checks run:

- `node --check functions/home_center_mcp.js`
- `node --check functions/index.js`
- `node --check tools/home_center_metal_prompt_smoke.mjs`
- `node tools/drive_bridge_create_tools_test.mjs`
- `python3 tools/home_center_regression_tests.py`
- `npm --prefix functions run lint`
- `sh tools/run_regression_tests.sh`

Deployed functions:

- `homeCenterMcp` revision `homecentermcp-00011-xul`
- `chatGptDriveCreateFolder` revision `chatgptdrivecreatefolder-00001-kod`
- `chatGptDocsCreate` revision `chatgptdocscreate-00001-nin`
- `chatGptOpenApi` revision `chatgptopenapi-00002-cav`
- `metalPromptSmoke` revision `metalpromptsmoke-00044-yag`

Real sandbox verification:

- Command: `node tools/home_center_metal_prompt_smoke.mjs --scenario drive-bridge-create-tools --run-id drivebridge-20260709144303`
- Evidence: `tools/metal_prompt_evidence/metal_prompt_smoke_drivebridge-20260709144303.json`
- Sandbox folder: `Home Center Smoke Sandbox/HC_SMOKE_RUN_drivebridge-20260709144303`
- Created project folder: `Tanks for the Memories v2`
- Created docs: `Tanks for the Memories v2 — Story Bible`, `Tanks for the Memories v2 — Manuscript`
- Verified appended text by exporting both docs.
- Cleanup: smoke run folder trashed successfully.

## Open Questions

- Whether the visible ChatGPT Home_Bridge namespace is currently MCP-backed or OpenAPI-backed; both surfaces were updated to avoid a stale split.
- Whether `docs_append` should also move from `actionAudit` to `driveBridgeAudit` in a later compatibility phase.

## Dead-Chat Recovery Contract

When a ChatGPT connector session loses the Home_Bridge namespace, Home Center cannot force that chat to regain tools. The bridge instead supports resumable workflows:

- Agents should call `recovery_checkpoint` before multi-write Drive/Docs work.
- Every intended write should carry a stable `requestId`.
- `recovery_status` compares checkpointed intents with `driveBridgeAudit` and `actionAudit`.
- MCP logs include `toolName`, `requestId`, `operationBatchId`, and sanitized target fields for `tools/call`.
- OAuth/token/userinfo without later `/mcp` activity is an OAuth-only dead session, not provider success.

## Durable Workflow Primitive

Chat continuity must not be the durable state holder. Multi-write Drive/Docs work should prefer `drive_workflow_run`, which checkpoints the full operation list, executes approved steps with stable per-step request IDs, records progress in `driveBridgeWorkflows`, and mirrors recovery status through `driveBridgeRecoveryCheckpoints`. Single-step tools remain useful, but batches that create/move/append multiple files should be bridge-owned.
