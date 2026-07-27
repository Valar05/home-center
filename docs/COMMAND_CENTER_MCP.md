# Command Center MCP

> Permanent boundary, effective 2026-07-27: Command Center no longer discovers, provisions, routes, wakes, registers, leases, or resumes Codex workers. The `/agent/*` and `/worker/*` gateways return HTTP 410. Worker, host, machine-image, provisioning, Codex-session, routing, multi-worker proof, activation creation, and execution-job initiation operations are removed from advertised MCP capabilities. Historical records and the implementation notes below are retained only as audit archaeology. They are not an available capability.
>
> Non-agent Blender rendering, render queues/workers, project records, managed knowledge buckets, app-control, browser operations, and read-only historical job/agent evidence remain separate and are not disabled by this tombstone. The authoritative removal contract is `docs/COMMAND_CENTER_CODEX_WORKER_DISCOVERY_TOMBSTONE.md`.

## Blender GLB Render File Handoff

For ChatGPT Work Mode uploaded GLB/script files, use the Home Center MCP top-level tool `render_blender_glb`. Do not put `glbFile` or `scriptFile` inside `command_center_operation.args`; nested dispatcher args are JSON and do not activate the host uploader.

`command_center_operation operation=render.blender_glb` is the stable no-reinstall render path. It remains valid for durable refs: `glbRef`, `scriptRef`, or `scriptText`, and it also accepts authenticated Home Center source descriptors such as:

```json
{
  "glbSource": {
    "provider": "github",
    "repository": "Valar05/pose-lab-v2",
    "ref": "605e8f128c9be8f586526517945e6747db44df7a",
    "path": "public/assets/vanguard/vanguard_rigged_animations.glb"
  },
  "scriptText": "...",
  "settings": {},
  "executionContract": {},
  "cache": false,
  "idempotencyKey": "..."
}
```

Use the GitHub descriptor for private repository GLBs when ChatGPT cannot see the top-level binary-upload tool. Home Center downloads the file server-side using its configured GitHub authority, validates the GLB header and byte count, hashes the bytes, stages an immutable `gs://` input, then invokes the existing non-agent Blender renderer. Do not route around this with GitHub Actions, Termux workers, Codex workers, or browser automation.

The top-level Home Center tool accepts only host-uploaded `glbFile` and `scriptFile` fields, then invokes the Command Center renderer function directly so the existing upload handler can stage exact bytes and return immutable `gs://` refs. It is a convenience path, not the critical path.


## Archived Codex Worker Design (Non-Operational)

Type: historical cloud MCP control plane / disabled execution dispatch / disabled worker supervision
Status: permanently disabled; audit archaeology only
Original date: 2026-07-10
Disabled: 2026-07-27

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

Command Center delegates auth through the Home Center OAuth bridge. If Google returns `disallowed_useragent` during a ChatGPT connector refresh, treat it as a blocked embedded-browser sign-in, not as a Command Center runtime failure. The Home Center `/oauth/authorize` endpoint serves a secure-browser handoff page for embedded user agents. Chrome or another system browser completes only the Google sign-in; the original ChatGPT auth page polls `/oauth/handoff-status` and then redirects through `/oauth/handoff-complete` so ChatGPT receives the authorization code from its own connector surface and can call `/oauth/token`. A plain auth refresh may reuse stale connector/browser state; reconnect the connector through the handoff path when this happens.

## Real Codex Cloud Agent Model

`Codex in the cloud` means the real OpenAI Codex cloud surface at `https://chatgpt.com/codex/`, logged into Drew's account and consuming real Codex quota. It does not mean a generic Firebase/Cloud Run code module and it does not mean Command Center's simulated `cloud-codex-primary` registry placeholder.

Command Center owns durable state around Codex cloud and portable workers:

- `repoAgents`: durable repo/project/domain identities that own long-lived context.
- `agentSessions`: durable worker sessions. A session may be repo-bound, project-bound, task-bound, or repo-less.
- `agentActivations`: dormant-to-active task packets created from a prompt, repo state, prior session, or follow-up.
- `codexCloudRefs`: recorded real Codex cloud task URLs/resume handles.
- `agentArtifacts`: final reports, bridge transcripts, evidence refs, and redacted outputs.
- `agentContextSnapshots`: compact packets used to resume the real Codex cloud surface.

Durable Codex worker sessions are a hard gate for portable execution. A Cloud Run Debian worker activation must restore a session workspace/context before execution and write a next workspace snapshot before completed success. Cloud workers do not require a repository, and a repository may have multiple workers with different capabilities, credentials, runtime images, or policies.

The Codex cloud bridge may use a persistent browser profile on a user-owned host, but Command Center must never store ChatGPT/OpenAI passwords, cookies, OAuth tokens, browser session blobs, bearer tokens, or reusable credentials. It stores only durable refs, summaries, artifacts, hashes, and redacted evidence.

Activation is fail-closed. `agents.create_activation` must select a healthy, routable, non-simulated worker that satisfies the activation's `workerRequirements`; the default `cloud-codex-primary` record is only a non-routable placeholder and cannot be leased for real work. For `cloud-run-debian` / `durable-session` workers, the selected worker must advertise a `cloud_run_job` activation channel, GCS snapshot storage, and Cloud Run Job metadata. Command Center invokes the Cloud Run Job with non-secret activation/session metadata; the worker token stays in Secret Manager on the job. Worker bridges claim activations through `POST /agent/claim`, heartbeat through `POST /agent/heartbeat`, record real Codex task refs through `POST /agent/codex-ref` when available, attach artifacts through `POST /agent/artifacts`, and finish through `POST /agent/complete`.

The red-build gate for this path is:

```sh
node tools/command_center_real_capability_gate.mjs --json --run-id <run-id>
```

Without `REAL_CODEX_CLOUD_URL` or `--codex-url https://chatgpt.com/codex/...`, the gate may prove the worker substrate but must remain red on `real_codex_cloud_ref_recorded`. Full green requires a real ChatGPT Codex cloud task URL consuming Drew's quota.

V1 exposes these typed tools:

- `command_center.projects.resolve`
- `command_center.projects.get`
- `command_center.jobs.create`
- `command_center.jobs.create_followup`
- `command_center.jobs.get`
- `command_center.jobs.list`
- `command_center.jobs.cancel`
- `command_center.jobs.resume`
- `command_center.jobs.revise`
- `command_center.jobs.reconcile_stale`
- `command_center.jobs.dispatch_queued`
- `command_center.jobs.answer_question`
- `command_center.jobs.authorize_mutation`
- `command_center.jobs.get_summary`
- `command_center.jobs.get_handoff`
- `command_center.jobs.get_events`
- `command_center.jobs.get_logs`
- `command_center.jobs.get_artifacts`
- `command_center.agents.upsert_repo_agent`
- `command_center.agents.create_activation`
- `command_center.agents.get_resume_packet`
- `command_center.agents.record_codex_cloud_ref`
- `command_center.agents.record_artifact`
- `command_center.agents.complete_activation`
- `command_center.agents.get_handoff`
- `command_center.bucket.get_layout`
- `command_center.bucket.put_object`
- `command_center.bucket.get_object`
- `command_center.bucket.list_objects`
- `command_center.bucket.promote_skill`
- `command_center.workers.register_oneshot`
- `command_center.workers.list`
- `command_center.workers.get_capabilities`

These are typed MCP operations. Command Center does not interpret chat prompts; ChatGPT performs interpretation and calls the correct tool.



## Cloud-Only Codex Capacity

Generic Command Center Codex execution is cloud-only. Termux, Android phones, local poll workers, and saved-login phone sessions are not eligible for generic Codex routing and are not a fallback when cloud capacity is red. Those records may remain as audit history or narrow specialty hosts, but default routing reports `local_host_excluded` and recommends cloud provisioning.

Command Center owns first-class cloud provisioning through these MCP operations:

- `workers.provision`: creates a cloud-only Debian Codex worker request, publishes the worker token to Secret Manager, creates or reuses the Cloud Run Job, registers the worker record, and registers/materializes the machine image metadata. It never returns token plaintext.
- `provisioning.inspect`: reads recent provisioning requests and failure evidence without secrets.
- `provisioning.reconcile`: checks whether provisioned workers became routable and recommends `workers.wake`/probe repair when they are still blocked.

No-capacity flows such as `codex_sessions.create`, `proof.run_multi_session`, and `routing.explain` now return a provisioning packet or recommendation instead of treating red capacity as a terminal excuse. Provisioned Cloud Run workers still fail closed until their authentication/capability probe proves the lane can run real Codex work.

## Fast Machine Images And Codex Session Pool

Command Center now treats execution substrate as three separate things:

- **Host / worker installation**: the machine that heartbeats and owns local credentials, caches, toolchains, and prepared workspaces.
- **Machine image**: a versioned capability profile such as `cloud-debian-codex` or a future `debian-blender` image. It records dependency bundle refs, warm cache refs, digest/provenance, and estimated hot/cold start cost.
- **Codex session**: a durable allocatable execution slot on a host, bound to a materialized image and nonsecret auth metadata such as `chatgpt_saved_login`.

The hot path rule is strict: normal jobs must not install or materialize heavy dependencies. A job that requests an image not already advertised as materialized fails closed with `image_not_materialized`. A job that requests `allowMaterializationDuringJob=true` fails with `hot_path_materialization_forbidden`. Materialization is a maintenance/update operation, not a task execution side effect.

Inspectable MCP operations for this substrate:

- `machine_images.register`: record a versioned image profile with capability/toolchain/cache refs. It stores metadata only; no secrets and no install side effects.
- `machine_images.list` / `machine_images.inspect`: show available images and which hosts have them materialized.
- `hosts.list` / `hosts.inspect`: worker-census aliases that foreground materialized images, cache state, session capacity, and auth mode.
- `codex_sessions.create`: allocate a durable session only when a routable host has a compatible materialized image and free isolated session capacity.
- `codex_sessions.list` / `codex_sessions.inspect` / `codex_sessions.reconcile`: inspect and repair durable session state.
- `proof.run_multi_session`: fail-closed proof requiring two isolated real session slots. It may accept two slots on one host only when the host explicitly advertises session-level isolation and capacity. It never counts aliases as separate workers and never synthesizes completed jobs.

Existing job operations remain backward compatible. `jobs.create`, `jobs.create_followup`, and `routing.explain` accept optional `sessionPolicy`, `machineImageId`, and `imageRequirements` fields. Without those fields, existing worker-capability routing is unchanged. With those fields, the scheduler filters hosts through materialized-image and session-capacity diagnostics before leasing.

The initial cloud image manifest is `tools/command_center_base_manifests/cloud-run-debian-codex.json`. It advertises one materialized `cloud-debian-codex` image on Cloud Run Jobs, device-independent Debian runtime, and one honest isolated session slot. It does not claim Blender capability and does not claim multi-session capacity.

## Worker Lifecycle V2

Command Center worker records are execution lanes, not dated project tickets. Generic workers must identify themselves with:

- `workerInstallationId`: durable random id created once on the worker host and reused across restarts.
- `workerId`: stable human-readable alias for that installation.
- `workerInstanceId`: new id for each supervisor process start.
- `runnerVersion` and `protocolVersion`.
- `ownerKey`, current capabilities, prepared workspaces, heartbeat sequence, process start time, last heartbeat, and last accepted lease.
- nonsecret authentication metadata such as `chatgpt_saved_login` or `api_key`.

Reconnects from the same installation update the canonical worker record. They must not create fresh dated aliases. Legacy project-specific one-shot records, including `termux-tanks-oneshot`, are quarantined from generic routing and from the multi-worker proof. Audit history remains in Firestore; stale records are retired or marked unroutable by `workers.reconcile` rather than deleted.

Termux and phone supervisors are not generic Codex capacity. Cloud Run Codex workers are routable only when their capability probe succeeds; API-key quota/auth failures are classified as cloud auth/probe failures and should lead to cloud provisioning or auth repair, not phone fallback. Blender Cloud Run rendering is separate from Codex worker routing.

Inspectable MCP operations:

- `system.health`: separate control-plane, worker-pool, and latest real end-to-end probe health.
- `workers.list`: compact census with identity, liveness, routability reason, auth mode, capabilities, prepared workspaces, active leases, and capacity.
- `workers.inspect`: one-worker registration, recent leases/events, executor outcomes, and repair recommendation.
- `routing.explain`: candidate inclusion/exclusion reasons without creating a job.
- `workers.reconcile`: bounded owner-scoped repair for stale/legacy records and abandoned jobs/leases; supports dry-run/apply.
- `workers.request_restart`: records a restart request and reports `host_offline` when the host is not heartbeating. Command Center does not pretend cloud code can restart a dead local phone.
- `workers.provision`: provisions another cloud Debian Codex worker lane from the cached Cloud Run image.
- `provisioning.inspect` / `provisioning.reconcile`: inspect and repair cloud provisioning state.
- `proof.run_multi_worker`: fail-closed two-worker proof. It requires two distinct real fresh worker installations, excludes simulated workers and `termux-tanks-oneshot`, and remains RED unless both nonce-bearing executions genuinely complete.

Common failure diagnoses include `local_host_excluded`, `stale_heartbeat`, `legacy_identity_incomplete`, `legacy_project_specific_worker`, `protocol_version_mismatch`, `api_key_capability_unavailable`, `capacity_exhausted`, and `host_offline`. Each diagnosis should say whether automatic repair is safe and whether local physical intervention is genuinely required.

## V1 One-Shot Worker Substrate

The first implementation now models workers as one-shot executions over prepared base workspaces. A worker is not a blank slate and does not install heavy tools such as Blender during normal job execution.

- `jobs.create` persists a one-shot ticket, records every compatible worker candidate, selects the least-loaded compatible live worker, creates a lease, writes events, writes logs, records a checkpoint, and requests activation when the worker declares an activation channel.
- A lease is not execution. Real `codex-cloud` workers must expose either a verified push activation channel or a live poll channel before they are eligible for leasing; metadata such as `simulated:false`, `routable:true`, or `health:"healthy"` is not enough.
- Job activation records live in `commandCenterJobActivations` and emit `activation_requested`, then `activation_accepted` or `activation_rejected`. Rejection marks the lease and job failed with diagnostics instead of leaving the job indefinitely `leased`. Poll workers record acceptance only when `/worker/lease` is actually claimed.
- `jobs.create_followup` creates a new linked invocation from a prior job handoff; it never rewrites the source job.
- `jobs.dispatch_queued` dry-runs or leases recoverable queued work against the current worker registry. It uses active lease counts and each worker's declared concurrency limit, records `eligibleWorkerIds`, `workerDiagnostics`, `selectedWorkerLoad`, and `dispatchAttemptCount`, and emits `job_dispatched_from_queue` before normal activation. Expired queued jobs are retried only when `retryExpired=true`.
- Every job records `executionMode=one_shot`, a `baseWorkspace` snapshot contract, required artifacts, verification commands, stop conditions, and mutation policy.
- `workers.register_oneshot` registers a user-owned worker and returns a worker token once. Command Center stores only the token hash.
- The worker gateway exposes `/worker/lease`, `/worker/events`, `/worker/artifacts`, `/worker/checkpoint`, and `/worker/complete` for registered workers.
- `tools/command_center_oneshot_worker.mjs` is the local runner scaffold: it copies a prepared workspace into a disposable run directory, runs the supplied command when present, and always emits the durable artifact contract.
- `jobs.answer_question` records the answer and resumes the job.
- `jobs.authorize_mutation` records approval or rejection under the ticket mutation policy.
- `jobs.get_summary` returns the latest checkpoint-style resumable worker state.
- `jobs.get_handoff` returns a bounded review/correction packet synthesized from job state, events, logs, artifacts, checkpoints, and bucket objects.


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

The worker also emits review-oriented postmortem artifacts:

- `acceptance-matrix.json`
- `handoff-packet.json`

Tool-specific outputs such as Blender renders, GLB exports, GitHub Pages builds, screenshots, APKs, and logs are additional artifacts. The required artifacts are the minimum reasoning/implementation surface that lets ChatGPT review the job without relying on worker chat history.

## Review And Correction Handoff

Every worker run must produce a `handoff-packet.json` artifact. Command Center also exposes `command_center.jobs.get_handoff` so ChatGPT can retrieve a review packet even when the local artifact URI is not directly readable from the cloud.

The handoff packet answers:

- what job ran, on which worker/base workspace, under which mutation policy;
- what changed, which commands ran, and what verification recorded;
- which events, logs, artifacts, checkpoints, and bucket objects support the result;
- which acceptance criteria are explicitly evaluated versus still `not_evaluated`;
- what the recommended next action is;
- how to create a corrective linked invocation.

Acceptance criteria are not automatically passed by executor exit code. Unknown criteria default to `not_evaluated` in `acceptance-matrix.json` unless the worker records explicit criterion evidence.

Corrective work should use `command_center.jobs.create_followup` with `sourceJobId`. Through the Home Center bridge, call `command_center_operation` with `operation=jobs.create_followup`; if a ChatGPT session exposes string-capable `drive_operation`, call `drive_operation` with `operation=command_center.jobs.create_followup`.

Some ChatGPT connector mounts cache the older `drive_operation.operation` enum even after OAuth refresh. For that stale-schema case only, use the explicit compatibility tunnel:

```json
{
  "operation": "drive_create_folder",
  "args": {
    "commandCenterOperation": "jobs.create_followup",
    "sourceJobId": "job_...",
    "title": "...",
    "objective": "...",
    "idempotencyKey": "..."
  }
}
```

The compatibility route activates only when `commandCenterOperation` is present; otherwise `drive_create_folder` remains the normal Drive folder operation. A follow-up job records `sourceJobId`, `followupOf`, and source evidence refs, then receives its own lease, events, artifacts, checkpoints, bucket objects, and final handoff. Do not revise or overwrite the old job to continue execution history.

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

For completed jobs, Command Center requires real executor evidence before accepting terminal success: `executor_started`, `executor_finished`, and at least one artifact whose origin is the executor workspace. Failed terminal states are allowed without success evidence so blockers can be recorded honestly.

Consequential mutations still flow through `command_center.jobs.authorize_mutation`; workers cannot self-approve push, merge, deploy, delete, or external-provider writes.


## Local Worker Host

The local worker host is `tools/command_center_oneshot_worker.mjs`. It supports:

- `register`: register a one-shot worker and store the returned worker token in local machine config with 0600 permissions.
- `prepare-base`: inspect a base workspace manifest, verify orientation files and declared tools, and write a preparation report without modifying the target repository.
- `run-once`: lease one job from Command Center, copy the prepared workspace into a disposable overlay, execute the configured one-shot executor command, upload artifact metadata, checkpoint, and complete or fail the job.
- `run-local`: run the same overlay/artifact path from a local job packet for smoke tests.

If no executor command is configured, the worker emits the required artifacts and fails honestly with `NO_EXECUTOR_CONFIGURED` rather than pretending implementation occurred. Worker tokens are local host state and must not be committed.

The first project manifest is `tools/command_center_base_manifests/tanks-for-the-memories.json`. It records the local Tanks repo path, orientation files, tool checks, Debian proot Blender deep check, capabilities, and mutation defaults.

## Historical Local Worker Records

Older Termux/local worker records remain readable for audit and retirement, but generic Codex routing excludes them by default with `local_host_excluded`. They are not a capacity fallback and should not be used to satisfy cloud-worker shortages.

## Verbose Worker Execution

One-shot executor output must stream while the child process is alive. The worker uses streaming `spawn` for configured executor commands; `spawnSync` is reserved for short internal checks such as git status, tool checks, and local setup commands.

During execution the worker emits these Command Center events through `/worker/events`:

- `executor_started`
- `executor_stdout`
- `executor_stderr`
- `executor_heartbeat`
- `executor_finished`
- `executor_failed`
- `executor_cancelled`
- `artifact_upload_summary`

Stdout and stderr are batched by 20 lines or 5 seconds, whichever happens first. The worker emits a heartbeat every 25 seconds while the child is alive. Heartbeat events update job, lease, and worker freshness so long Codex jobs do not appear stuck during quiet phases. `executor_started` moves the job to `executing` and records PID/process evidence. `executor_finished` is required before a worker may mark a job `completed`.

The worker redacts token-like strings, bearer headers, worker tokens, GitHub tokens, Google/OAuth-looking tokens, API keys, and environment-style secret assignments before writing local transcripts or cloud events. It never logs the full environment.

Every executor run leaves local postmortem artifacts:

- `stdout-transcript.txt`
- `stderr-transcript.txt`
- `event-transcript.jsonl`
- `executor-status.json`
- `artifact-upload-summary.json`

Live smoke command:

```sh
node tools/command_center_verbose_worker_smoke.mjs --run-id verbose-worker-$(date +%Y%m%d%H%M%S)
```

The smoke registers a temporary one-shot worker, creates a unique-capability job, runs a long fake executor, polls `command_center.jobs.get_events` while the child is still alive, and fails unless stdout/stderr/heartbeat events are visible in cloud readback before `executor_finished`.

## Managed Knowledge Bucket

Command Center owns a managed logical bucket named `command-center`. It is not a chat transcript and not a dashboard. It is the durable organization surface for execution memory, reusable skills, and cross-repository notes.

The bucket metadata lives in `commandCenterBucketObjects`. Large payloads may live elsewhere and be referenced by `objectUri`, such as `gs://`, Drive, GitHub, or worker-local artifact refs. Bucket records must never inline reusable credentials, bearer tokens, worker tokens, OAuth secrets, private keys, passwords, or raw unredacted environment dumps.

Bucket lanes:

- `memory/past-logs`: append-only historical execution logs and evidence summaries.
- `memory/current-condensed`: latest compact resumable state per job or project.
- `skills/scratch`: unpromoted candidate procedures captured from runs.
- `skills/promoted`: reviewed reusable procedures with acceptance evidence.
- `notes/cross-repo`: project-spanning engineering notes and links.

Bucket object kinds:

- `memory.past_log`
- `memory.current_condensed`
- `skill.scratch`
- `skill.promoted`
- `note.cross_repo`

Automatic writes:

- `recordLog` mirrors Command Center job logs into `memory/past-logs/<projectId>/<jobId>/...`.
- `recordCheckpoint` and worker `/worker/checkpoint` mirror compact resumable execution state into `memory/current-condensed/<projectId>/<jobId>.json`.

Manual MCP tools:

- `command_center.bucket.get_layout` returns the current lane and storage policy.
- `command_center.bucket.put_object` writes a typed bucket object with provenance, project/repository/job links, tags, source refs, evidence refs, content hash, and optional `objectUri`.
- `command_center.bucket.get_object` reads one bucket object by id.
- `command_center.bucket.list_objects` lists bucket objects by kind, project, repository, job, tag, or bucket id.
- `command_center.bucket.promote_skill` promotes an existing `skill.scratch` object into `skills/promoted` while preserving supersession links and evidence.

The bucket is deliberately broad enough for cross-repo notes, but narrow enough to preserve artifact boundaries. Do not collapse unrelated repo notes, scratch doctrine, job logs, and promoted skills into a single mega-document.

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
- `commandCenterBucketObjects`
- `appControlProfiles`
- `appControlRuns`
- `browserSessions`
- `browserEpisodes`
- `browserDiscoveries`
- `browserPlaybooks`
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

Before claiming a ChatGPT plugin/MCP app installation is broken or unavailable, run the Termux debugger:

```sh
node tools/debug_chatgpt_plugin_install.mjs
```

That command treats Playwright Chromium desktop ChatGPT as the primary visible install surface. Android ChatGPT app or Shizuku UI evidence is fallback only.

This is the loop-closing path. If ChatGPT cannot see a separate `commandCenterMcp` tool namespace, it must not stop; it should call Home Center `command_center_operation`.

Status surfaces have one responsibility each. Home Center and Command Center `health` report process liveness only. `readiness` reports bounded required-configuration checks. `capabilities` reports deterministic top-level tool names and names-only operation summaries. Detailed worker-pool and end-to-end probe diagnostics remain under `system.health`.

Normal flow:

1. Call Home Center `health` for liveness and `readiness` before accepting work.
2. Call Home Center `capabilities` when operation-name discovery is needed, then call `command_center_operation` with `operation=health`; the bridged operation result must return `ok=true` and `invokable=true`.
3. Resolve a project with `operation=projects.resolve` when needed.
4. Create a follow-up worker action with `operation=jobs.create`.
5. Recover or supervise with `operation=jobs.get`, `jobs.get_events`, `jobs.get_artifacts`, and `jobs.get_summary`.
6. Review with `operation=jobs.get_handoff`.
7. Continue the job with `jobs.answer_question` or `jobs.authorize_mutation` when policy allows.
8. Create corrective new invocations with `jobs.create_followup`, never by rewriting the old job.
9. Preserve reusable execution learning with `bucket.put_object`, inspect it with `bucket.list_objects`, and promote proven scratch procedures with `bucket.promote_skill`.
10. Publish and inspect installed-app control profiles with `app_control.seed_profiles`, `app_control.list_profiles`, `app_control.get_profile`, `app_control.put_profile`, and `app_control.record_run`.
11. Run browser hands through Playwright-backed operations: `browser_sessions.create`, `browser_sessions.observe`, `browser_sessions.act`, `browser_sessions.record_episode`, `browser_discoveries.list`, and `browser_discoveries.promote`.

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
