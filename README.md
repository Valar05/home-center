# Home Center

Home Center is now primarily a native Android login shell for the shared Google/Firebase tool infrastructure. The expensive part of the app is the authenticated Google tools connection; legacy chat and family voice commands remain available behind secondary controls.

Primary target for this slice:

- `add eggs to shopping list` adds `eggs` to the shared Home Center `shopping` list.
- `read shopping list` loads active items and reads the first one.
- `next`, `previous`, and `done` advance through the active readback list or mark the current Home Center task complete.
- TickTick remains as a masked legacy fallback when Firebase sync is not configured or not signed in.


## Doctrine

Home Center's repo-local product doctrine lives in `docs/HOME_CENTER_DOCTRINE.md`. Read it before changing agent behavior, memory, research, writing, life-organization, Netrunner, provider tools, or skill/simulation features. The app should not depend on a web request or external doctrine store to know its own purpose.

## Build

```sh
cd /storage/emulated/0/Documents/GodotProjects/home-center
sh tools/build_debug_apk.sh
```

The debug APK is written to:

```text
app/build/outputs/apk/debug/app-debug.apk
```

A copy is published to:

```text
/storage/emulated/0/Download/HomeCenter-debug.apk
```

The build script installs that APK through Shizuku using `tools/install_debug_apk_shizuku.sh`.

This Termux build compiles with SDK 33 because the local ARM64 `aapt2` works with that platform. Firebase dependencies are pinned in `app/build.gradle` to versions that still build against SDK 33.



## Termux / Codex Hub Pairing

Home Center can act as the auth hub for local Termux/Codex connected actions. The Android app remains the human approval surface; Termux receives a revocable Home Center hub token, not raw Google or GitHub provider tokens.

Pair from Termux:

```sh
cd /storage/emulated/0/Documents/GodotProjects/home-center
node tools/home_center_codex_pair.mjs
```

The helper prints a pairing ID and six digit code. In the installed Home Center app, sign in, approve Google tools, tap `Pair Termux Codex`, and enter both values. The helper saves a local config at:

```text
~/.config/home-center/codex-hub.json
```

That config contains the Home Center MCP URL and Home Center bearer token. The MCP URL remains:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp
```

V1 grants the safe core tool groups only: Drive, Docs, Sheets search/read, and GitHub read/issue/comment tools. Gmail sends, Calendar writes, destructive deletes, workflow dispatch, merges, and broad organizer actions are not part of the Termux/Codex v1 grant.

## Command Center MCP

Command Center is a separate cloud MCP control plane for dispatching, supervising, and preserving Codex worker execution. It has no frontend and no independent chat interface. ChatGPT remains the planner and conversational surface; Command Center persists projects, tickets, leases, events, questions, mutation approvals, logs, artifacts, and checkpoints; user-owned Codex workers execute.

Normal ChatGPT invocation should use the already-connected Home Center MCP app first:

```text
tool: command_center_operation
operation: jobs.create | jobs.get | jobs.get_events | jobs.get_artifacts | jobs.answer_question | jobs.authorize_mutation
```

This avoids a dead-end where ChatGPT can see Home Center tools but cannot discover a separate `commandCenterMcp` namespace. The standalone Command Center MCP endpoint still exists for direct MCP clients and worker-control tooling.

Automatic discovery must start at Home Center `health`, not nested `capabilities`. The health response includes `discoverability.automaticDiscovery.commandCenter` with:

- the primary tool: `command_center_operation`;
- the direct Command Center MCP URL;
- a minimal `operation=health` call;
- the string-capable `drive_operation operation=command_center.health` fallback;
- the stale enum-schema tunnel: `drive_operation operation=drive_create_folder` with `args.commandCenterOperation`;
- reconnect advice when a mounted connector still reports an older registry.

If ChatGPT still sees the older `Home Drive v4` schema after OAuth refresh, reconnect or reindex the app/link. OAuth refresh updates credentials only; it does not necessarily reload tool metadata.

The Firebase export is `commandCenterMcp` and its MCP endpoint is:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp
```

The current implementation supports durable one-shot worker dispatch, streaming executor events, persisted artifacts, handoff synthesis, linked follow-up jobs, and the Command Center knowledge bucket. See `docs/COMMAND_CENTER_MCP.md`.

## Regular ChatGPT App / MCP Setup

The durable target for normal ChatGPT is the Home Center MCP app, not a one-off Custom GPT Action. The deployed streamable HTTP MCP server URL is:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp
```

The `/mcp` transport is stateless Streamable HTTP so Cloud Run can scale horizontally without sticky sessions or in-memory MCP session state. A legacy SSE transport remains available for older MCP clients, but ChatGPT should use `/mcp`.

Legacy SSE endpoint:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/sse
```

Default public MCP tools:

- `health`
- `drive_search`
- `drive_read`
- `docs_append`
- `simulation_operation`
- `sheets_search`
- `sheets_read`
- `drive_create_folder`
- `docs_create`

The scalable Drive bridge path is `drive_operation`: call `capabilities` for `operationRegistry`, then invoke operations by name without waiting for ChatGPT to refresh top-level MCP tools. The scalable Simulation path is `simulation_operation`: call `capabilities` for `simulationOperationRegistry`, then build/query/run simulation frames by operation name. The bridge also exposes audited `workbook_import_xlsx` for Excel-to-native-Google-Sheets migration. It can convert an existing Drive `.xlsx` by `sourceFileId` or `sourceFileName`/`sourceFolderId`, or accept uploaded `.xlsx` bytes when the client can provide them. It uses Google Drive conversion and returns the new spreadsheet ID, tab names, import warnings, populated-cell count diffs when source counts are supplied, and an audit entry. Extended MCP tools also include audited `sheets_create` and `sheets_update_values` when `HOME_CENTER_MCP_EXTENDED_TOOLS=true`. No Sheets delete/trash tool is exposed.

### No-Reinstall Discovery Contract

Future agents should not require a connector reinstall for ordinary Home Drive or Simulation backend additions. The stable discovery path is:

1. Call `health` if only a minimal tool is available.
2. Call `capabilities` when available.
3. Read `capabilities.operationRegistry.operations` for Drive or `capabilities.simulationOperationRegistry.operations` for Simulation.
4. Execute supported Drive mutations through `drive_operation` with a stable `requestId`; execute Simulation project/reference/frame operations through `simulation_operation`.

For Excel migration, the normal ChatGPT path is not Base64 and not a local `/mnt/data` path. If the workbook is already in Drive, call `drive_operation` with `operation=workbook_import_xlsx` and pass `sourceFileId`, or `sourceFileName` plus `sourceFolderId`. Use `workbookBase64` only when the MCP client can provide the complete XLSX bytes. If a workbook exists only as a ChatGPT attachment and the runtime has no typed file-bytes handoff, first place the workbook in Drive, then import it by Drive ID or name.


The broader operator tools are gated behind `HOME_CENTER_MCP_EXTENDED_TOOLS=true` until their ChatGPT connector behavior is separately hardened.

The MCP transport is OAuth protected. Unauthenticated `/mcp`, `/sse`, and `/messages` requests return `401` with a `WWW-Authenticate` challenge pointing at:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/oauth-protected-resource-v2
```

That metadata advertises Home Center itself as the OAuth authorization server. Home Center exposes dynamic client registration plus authorization and token endpoints, then performs Google OAuth behind the bridge using the server-side Google client secret. ChatGPT should not need a Google client ID or a manual token exchange for this path.

Authorization server metadata:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/.well-known/oauth-authorization-server
```

Google callback used by the bridge:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/oauth/google-callback
```

The Drive/Docs/Sheets tools require the resulting Home Center MCP bearer token. The bridge resolves that token to Google Drive, Docs, and Sheets credentials server-side. Write tools use stable request IDs where meaningful and write audit records to Firestore. The public bridge surface does not expose delete, trash, or restore tools.

Dead-chat recovery tools are part of the extended MCP surface:

- `drive_operation`: stable operation-registry runner. Prefer this for new bridge capabilities so connector metadata does not need reinstall for every backend code change.
- `drive_workflow_run`: checkpoints and executes a whole approved Drive/Docs/Sheets workflow in one bridge-owned call. Prefer this for multi-write work so continuity lives in Home Bridge instead of the ChatGPT conversation.
- `recovery_checkpoint`: records intended write operations before a multi-write workflow starts.
- `recovery_status`: compares a checkpoint against `driveBridgeAudit` and `actionAudit` so the next chat can identify completed and missing writes.

If ChatGPT completes OAuth but then stops calling `/mcp`, the bridge cannot repair that dead chat from server-side code. The recovery path is to start a new tool-capable chat and paste this prompt:

```text
You are recovering a Home_Bridge Drive workflow after a dead ChatGPT connector session.

Rules:
1. Do not reason from memory alone.
2. First inspect live Home_Bridge state.
3. If Home_Bridge tools are available, call health, auth_status, capabilities, recovery_status if available, and audit_log for the relevant request IDs.
4. Treat audit records and Drive readback as source of truth.
5. Do not retry writes that already have successful audit entries.
6. For each missing write, execute exactly one write, then verify audit/readback before the next write.
7. If Home_Bridge tools are not available in this chat, say: "The Home_Bridge tool namespace is not attached to this conversation, so I cannot recover the workflow from inside this chat." Then produce a handoff ledger with completed writes, missing writes, target names, intended request IDs, and exact next operation.
8. Do not rephrase blocked writes blindly. Use the saved ledger and stable request IDs.

Current recovery target:
[PASTE THE LEDGER OR USER INTENT HERE]
```

To connect from ChatGPT, enable Developer mode, go to Plugins / Apps, add a custom remote MCP app, and use the `/mcp` URL above. If Google rejects the bridge login with `redirect_uri_mismatch`, add the Google callback URI above to the Home Center Google OAuth web client's authorized redirect URIs.

## ChatGPT Action Setup

ChatGPT should use Google OAuth directly. Do not add a separate Home Center API key, bearer token, CLI auth exchange, or refresh-token exchange for the ChatGPT Action path.

Import this OpenAPI contract URL into the custom GPT Action builder:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/chatGptOpenApi
```

The same contract is kept in the repo at `openapi.chatgpt.yaml`.

Configure Action authentication as OAuth with Google endpoints:

```text
Authorization URL: https://accounts.google.com/o/oauth2/v2/auth
Token URL: https://oauth2.googleapis.com/token
Scopes: https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents
```

The deployed functions expect ChatGPT to send the Google access token as:

```text
Authorization: Bearer <google-oauth-access-token>
```

The OAuth-direct action endpoints are:

- `POST /chatGptDriveSearch`
- `POST /chatGptDriveRead`
- `POST /chatGptDriveCreateFolder`
- `POST /chatGptDocsCreate`
- `POST /chatGptDocsAppend`

`chatGptDocsAppend` writes an `actionAudit` record. There is no delete or trash endpoint in this Action contract.

Example Drive Bridge payloads:

Create a project folder:

```json
{"name":"Tanks for the Memories v2","requestId":"tftm-v2-folder-001","callerNote":"Create project folder"}
```

Create a Story Bible document inside that folder:

```json
{"title":"Tanks for the Memories v2 — Story Bible","parentFolderId":"<folderId>","initialText":"# Story Bible\n","requestId":"tftm-v2-story-bible-001"}
```

Create a manuscript document inside that folder:

```json
{"title":"Tanks for the Memories v2 — Manuscript","parentFolderId":"<folderId>","initialText":"# Manuscript\n","requestId":"tftm-v2-manuscript-001"}
```

Append later with `docs_append` / `chatGptDocsAppend`:

```json
{"documentId":"<documentId>","heading":"New Section","text":"...","requestId":"tftm-v2-append-001"}
```

Example bridge-owned workflow payload:

```json
{
  "workflowId": "tftm-v2-bootstrap-001",
  "objective": "Create project folder and two starter docs in one durable Home Bridge workflow.",
  "approved": true,
  "operations": [
    {"type": "drive_create_folder", "name": "Tanks for the Memories v2", "saveAs": "project"},
    {"type": "docs_create", "title": "Tanks for the Memories v2 — Story Bible", "parentFolderKey": "project", "saveAs": "storyBible", "initialText": "# Story Bible\n"},
    {"type": "docs_create", "title": "Tanks for the Memories v2 — Manuscript", "parentFolderKey": "project", "saveAs": "manuscript", "initialText": "# Manuscript\n"}
  ]
}
```

If ChatGPT loses connector state after sending that call, the bridge still has `driveBridgeWorkflows`, `driveBridgeRecoveryCheckpoints`, and per-step audit records keyed by `tftm-v2-bootstrap-001`. 


## Firebase Setup

Firebase is optional at build time. Without `app/google-services.json`, the APK still builds and opens, but Home Center sync reports that Firebase config is missing and falls back to TickTick for supported commands.

Setup steps are in `docs/FIREBASE_SETUP.md`. Do not commit `app/google-services.json`, service accounts, private keys, or TickTick tokens.

## Install On This Phone

Use Shizuku for installs on this phone:

```sh
sh tools/install_debug_apk_shizuku.sh /storage/emulated/0/Download/HomeCenter-debug.apk
```

Do not stop at a manual Downloads install prompt unless Shizuku/rish is unavailable.

## Voice Commands

Supported now:

```text
add eggs to shopping list
create list pantry
create personal list meds
create household list chores
create group list soccer for kids
prefer eggs as 18 count
map eggs to walmart sku 12345
read shopping preferences
build walmart cart for shopping
remove eggs from shopping list
delete eggs from shopping list
take eggs off shopping list
cross eggs off shopping list
mark eggs done on shopping list
read shopping list
what is on shopping list
next
previous
done
turn on hotspot
turn off hotspot
```

Hotspot commands are parsed but not implemented yet. Home Center speech requests transient Android audio focus so music apps should pause or duck while responses are spoken.

ElevenLabs hosted speech runs through the Home Center gateway. The default voice path is ElevenLabs Brian via the Firebase `/tts` endpoint; the Android app should not require the user to start a local speech proxy or enter an API key.

Set `AGENT_GATEWAY_BASE_URL` in `local.properties` for the deployed Home Center gateway. Operational prompts use native Android TTS; rendered assistant responses and document reader chunks use ElevenLabs Brian through the hosted `/tts` endpoint.

## Data Model

Home Center stores synced tasks in Firestore under a household bucket. See `docs/DATA_MODEL.md`.

Task fields are:

- `name`
- `description`
- `json`
- `jsonText`
- `dueAt`
- `status` (`active` or `done`)
- audit fields such as `createdAt`, `createdBy`, `completedAt`, and `completedBy`

## Deployment

See `docs/DEPLOYMENT.md` for APK build/copy, Firebase rules deploy, and Git hook setup.

## Smoke Checks

```sh
sh tools/run_regression_tests.sh
gradle assembleDebug --no-daemon
apksigner verify --verbose app/build/outputs/apk/debug/app-debug.apk
aapt dump badging app/build/outputs/apk/debug/app-debug.apk | sed -n '1,20p'
sh tools/check_no_secrets.sh
```

`tools/run_regression_tests.sh` is dependency-free. It runs the secret scanner, source-contract checks for the Firestore membership/write flow, the agent failure matrix from `docs/AGENT_CONTRACT.md`, and a Java command-parser harness for common voice commands.

## List Visibility

Lists can be created as:

- `personal`: visible only to the Google account that owns the list.
- `household`: visible to members of the selected household bucket.
- `group`: visible to members of a Home Center family group inside the household bucket. Group sharing uses a Home Center group name/code, not Google Family Link membership.

Examples:

```text
create personal list meds
create household list chores
create group list soccer for kids
add cleats to soccer list
```

## Local Logs

Home Center writes local-only diagnostic logs by date. Logs are not sent to Firestore or any cloud service. On Android 10+ they are written through the Downloads provider so Termux and Google Files can read them:

```text
/storage/emulated/0/Download/HomeCenter/logs/YYYY-MM-DD.txt
```

The app also shows the active log path in the status area. Useful entries include app startup, spoken command parsing, bucket/list/user context, Firebase successes, automatic bucket membership repair, and Firebase errors such as `PERMISSION_DENIED`.


## Simulation MCP compiler

Simulation is MCP-first in v1. Chat or another agent assembles a large evidence-bearing reference compilation, then calls `simulation_operation` to create a project, register sources, append reference chunks, finalize the compilation, build an immutable frame, query it, generate bounded context packets, or run a deterministic frame-grounded handoff. Do not route this workflow through spreadsheets.

See `docs/SIMULATION_MCP.md` for operation details and acceptance expectations.
