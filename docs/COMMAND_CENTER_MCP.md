# Command Center MCP

Type: cloud MCP control plane / execution dispatch / worker supervision
Status: v1 one-shot worker substrate
Date: 2026-07-10

Command Center is a cloud-hosted MCP control plane that ChatGPT calls to dispatch, supervise, and preserve execution work.

It has no independent chat interface. It is not a user-facing Android screen, not a FastAPI dashboard, not the planner, not the primary memory system, and not another agent competing with ChatGPT.

## Operating Relationship

```text
Drew + ChatGPT
      |
      | MCP tool calls
      v
Command Center
      |
      | leases and supervises jobs
      v
Codex workers
```

ChatGPT is the conversational control surface and reasoning layer. Command Center is the durable dispatch and execution-control layer. Codex workers are user-owned Codex workers: execution machines such as cloud Codex, Termux Codex, or workstation Codex.

## Responsibility Boundary

- Drew owns intent, priorities, judgment, product decisions, and final authorization for consequential mutations.
- ChatGPT owns conversation interpretation, active project resolution, ticket drafting, acceptance criteria, routine worker-question answers, completion review, and escalation to Drew when needed.
- Command Center owns the project registry, ticket persistence, queue state, worker selection, job leasing, execution sessions, worker heartbeats, context checkpoints, log ingestion, mutation permissions, questions, notifications, artifacts, audit history, and failure recovery.
- Codex workers own repository inspection, implementation, commands, tests, builds, diagnostics, local commits when authorized, and structured reports back to Command Center.

## MCP Surface

The Firebase export is `commandCenterMcp`; the Streamable HTTP endpoint is:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp
```

V1 exposes these typed tools:

- `command_center.projects.resolve`
- `command_center.projects.get`
- `command_center.jobs.create`
- `command_center.jobs.get`
- `command_center.jobs.list`
- `command_center.jobs.cancel`
- `command_center.jobs.resume`
- `command_center.jobs.revise`
- `command_center.jobs.answer_question`
- `command_center.jobs.authorize_mutation`
- `command_center.jobs.get_summary`
- `command_center.jobs.get_events`
- `command_center.jobs.get_logs`
- `command_center.jobs.get_artifacts`
- `command_center.workers.register_oneshot`
- `command_center.workers.list`
- `command_center.workers.get_capabilities`

These are typed MCP operations. Command Center does not interpret chat prompts; ChatGPT performs interpretation and calls the correct tool.

## V1 One-Shot Worker Substrate

The first implementation now models workers as one-shot executions over prepared base workspaces. A worker is not a blank slate and does not install heavy tools such as Blender during normal job execution.

- `jobs.create` persists a one-shot ticket, selects a compatible worker, creates a lease, writes events, writes logs, and records a checkpoint.
- Every job records `executionMode=one_shot`, a `baseWorkspace` snapshot contract, required artifacts, verification commands, stop conditions, and mutation policy.
- `workers.register_oneshot` registers a user-owned worker and returns a worker token once. Command Center stores only the token hash.
- The worker gateway exposes `/worker/lease`, `/worker/events`, `/worker/artifacts`, `/worker/checkpoint`, and `/worker/complete` for registered workers.
- `tools/command_center_oneshot_worker.mjs` is the local runner scaffold: it copies a prepared workspace into a disposable run directory, runs the supplied command when present, and always emits the durable artifact contract.
- `jobs.answer_question` records the answer and resumes the job.
- `jobs.authorize_mutation` records approval or rejection under the ticket mutation policy.
- `jobs.get_summary` returns the latest checkpoint-style resumable worker state.


## One-Shot Artifact Contract

Every one-shot worker run must produce these artifacts, even on failure:

- `job-intake.json`
- `orientation.md`
- `reasoning-summary.md`
- `command-log.jsonl`
- `implementation.patch`
- `changed-files.json`
- `verification.json`
- `final-report.md`
- `mutation-requests.jsonl`

Tool-specific outputs such as Blender renders, GLB exports, GitHub Pages builds, screenshots, APKs, and logs are additional artifacts. The required artifacts are the minimum reasoning/implementation surface that lets ChatGPT review the job without relying on worker chat history.

## Prepared Base Workspaces

Base workspaces are durable, versioned substrates owned by the worker host. They contain warm repo checkouts, toolchains, caches, Blender/Godot/Node/Python/Firebase/GitHub tooling, and project-local validation scripts. Command Center records the base workspace reference and version; it does not reinstall heavy tools during job execution.

Default restore behavior is `copy_overlay`: copy the prepared workspace into a disposable writable run directory, execute one job, preserve artifacts, then discard or archive the overlay.

## Worker Gateway

Registered workers authenticate with short-lived bearer tokens whose hashes are stored in `commandCenterWorkerTokens`. Worker host secrets stay on the worker. Command Center accepts only structured worker calls:

- `POST /worker/lease` returns one leased job packet for the authenticated worker.
- `POST /worker/events` records structured status events.
- `POST /worker/artifacts` records artifact metadata and object refs.
- `POST /worker/checkpoint` records resumable execution state.
- `POST /worker/complete` marks the job completed or failed and records final artifact refs.

Consequential mutations still flow through `command_center.jobs.authorize_mutation`; workers cannot self-approve push, merge, deploy, delete, or external-provider writes.


## Local Worker Host

The local worker host is `tools/command_center_oneshot_worker.mjs`. It supports:

- `register`: register a one-shot worker and store the returned worker token in local machine config with 0600 permissions.
- `prepare-base`: inspect a base workspace manifest, verify orientation files and declared tools, and write a preparation report without modifying the target repository.
- `run-once`: lease one job from Command Center, copy the prepared workspace into a disposable overlay, execute the configured one-shot executor command, upload artifact metadata, checkpoint, and complete or fail the job.
- `run-local`: run the same overlay/artifact path from a local job packet for smoke tests.

If no executor command is configured, the worker emits the required artifacts and fails honestly with `NO_EXECUTOR_CONFIGURED` rather than pretending implementation occurred. Worker tokens are local host state and must not be committed.

The first project manifest is `tools/command_center_base_manifests/tanks-for-the-memories.json`. It records the local Tanks repo path, orientation files, tool checks, Debian proot Blender deep check, capabilities, and mutation defaults.

## Firestore Collections

V1 state is stored in these collections:

- `commandCenterProjects`
- `commandCenterJobs`
- `commandCenterWorkers`
- `commandCenterLeases`
- `commandCenterEvents`
- `commandCenterQuestions`
- `commandCenterMutationAuthorizations`
- `commandCenterArtifacts`
- `commandCenterLogs`
- `commandCenterCheckpoints`
- `commandCenterBaseWorkspaces`
- `commandCenterWorkerTokens`
- `commandCenterIdempotency`

Every mutating tool requires an `idempotencyKey`. Mutation authorization belongs to the ticket; workers cannot silently elevate their own permissions.

## Non-Goals

Do not build a frontend before the MCP ticket lifecycle, worker lease, event stream, and recovery path function end to end.

Do not use `agent-commander` or a chat-first UI as the product surface for Command Center unless a later prompt explicitly imports that repo as an implementation detail.

Do not put Codex login secrets in ticket data. Worker authentication and quota are worker concerns; Command Center stores worker capability and health metadata only.

## ChatGPT Invokability Acceptance

The accepted normal ChatGPT path is the already-connected Home Center MCP app exposing Command Center through a stable dispatcher:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp
tool: command_center_operation
```

This is the loop-closing path. If ChatGPT cannot see a separate `commandCenterMcp` tool namespace, it must not stop; it should call Home Center `command_center_operation`.

Normal flow:

1. Call Home Center `health`; it advertises `preferredCommandCenterTool=command_center_operation`.
2. Call `command_center_operation` with `operation=health`; the bridged Command Center health result must return `ok=true` and `invokable=true`.
3. Resolve a project with `operation=projects.resolve` when needed.
4. Create a follow-up worker action with `operation=jobs.create`.
5. Recover or supervise with `operation=jobs.get`, `jobs.get_events`, `jobs.get_artifacts`, and `jobs.get_summary`.
6. Continue the job with `jobs.answer_question` or `jobs.authorize_mutation` when policy allows.

The standalone Command Center endpoint remains available for direct MCP clients and worker-control tooling:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp
```

Local/live protocol gate:

```sh
node tools/command_center_chatgpt_invokability_gate.mjs
node tools/command_center_home_bridge_invokability_gate.mjs
```

With a real Home Center MCP OAuth bearer token, the gate can also create/read the live smoke job:

```sh
HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN=... node tools/command_center_chatgpt_invokability_gate.mjs --create-job --require-real-token
```

## Deployment Evidence

Deployed to Firebase/GCF gen2 on 2026-07-10 with:

```sh
gcloud functions deploy commandCenterMcp --gen2 --runtime=nodejs20 --region=us-central1 --source=functions --entry-point=commandCenterMcp --trigger-http --allow-unauthenticated --timeout=300s --project=home-center-dclar
```

Live revision verified after deploy:

```text
commandcentermcp-00002-ger ACTIVE https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp
```

Live probes verified:

- `/` returns `service=command-center-mcp` and `hasFrontend=false`.
- `/.well-known/oauth-protected-resource` advertises `commandCenterMcp/mcp` and delegates authorization to `homeCenterMcp`.
- `/mcp` without a bearer token returns `401` with a `WWW-Authenticate` challenge.

ChatGPT invokability protocol gate passed after the `commandcentermcp-00002-ger` deploy:

```text
tools/command_center_invokability_evidence/command_center_invokability_command-center-chatgpt-20260710.json
```

That evidence verifies protected-resource metadata, Home Center OAuth delegation, the unauthenticated MCP challenge, Streamable HTTP initialize, tool listing, and a successful `command_center.health` tool call. The local regression suite also runs the one-shot worker self-test, proving the prepared-workspace copy and required artifact contract.

Home Center bridge revision `homecentermcp-00025-xuf` also exposes `command_center_operation` directly through the normal Home Center MCP app. Red/green evidence:

- Red before deploy: `tools/command_center_invokability_evidence/command_center_home_bridge_invokability_predeploy-red-20260710.json` recorded `Tool command_center_operation not found`.
- Green after deploy: `tools/command_center_invokability_evidence/command_center_home_bridge_invokability_postdeploy-green-20260710.json` recorded tool discovery and `operation=health` execution through Home Center MCP.
