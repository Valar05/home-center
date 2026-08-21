# Home Center Mutation Lane Truth

## Purpose

Choose a real currently deployed Home Center mutation lane without resurrecting retired workers, confusing historical capability with current callability, or silently substituting a phone/P0 surface for a non-phone source task.

## Trigger

Use when a task needs Home Center to mutate repository/source state, execute a desktop-local patch, or report whether a worker/job path is actually callable now.

## First move: deployed capability truth

Read the deployed Home Center capability registry before selecting an execution lane. Repository history describes what was built; the deployed registry describes what is callable now.

Fresh deployed capability truth on 2026-08-21 exposes:

- audited GitHub admin operations including exact file read and complete-file upsert;
- `drive_operation` with current `computer_hands.request.create`, `.status`, `.cancel`, `computer_hands.worker.status`, and `.register` operation surfaces;
- `command_center_operation` for the current Command Center registry;
- Phone Hands as a distinct shared physical surface with its own binding firewall.

Fresh `computer_hands.worker.status` readback for `windows-hands-01` reports:

- tool surface callable: **YES**;
- worker online: **NO**;
- status: `idle`;
- queue depth: **4**;
- active lanes include `lane-reality-membrane`, `lane-spotify-radio`, `lane-try-forever-heartbeat-detail`, and `lane-try-forever-provenance-owner`.

Therefore current lane families must be treated as:

- **GitHub admin**: authenticated repository administration and complete-file replacement/upsert;
- **Computer Hands**: a currently deployed request/worker operation family, but a callable API is not a callable execution body when the registered worker is offline;
- **Command Center current registry**: only operations that the deployed runtime registry actually accepts; historical Codex agent/job/session/worker families are not assumed;
- **Phone Hands / primary-phone**: a distinct shared physical execution surface with its own ownership/firewall and never a substitute for blocked non-phone source mutation.

## GitHub admin lane

Use audited GitHub admin writes when the exact requested repository mutation can be expressed safely through the deployed tool.

For an existing file:

- read the exact current file and blob first;
- preserve all unrelated content;
- supply the current blob lock on replacement;
- remember that `github_admin_upsert_file` replaces complete contents; it is not a patch interpreter;
- verify the resulting remote blob/commit and review the actual diff/readback;
- do not call a locally reconstructed file proof until remote readback confirms it.

A pre-written patch artifact can establish intended source delta and review readiness, but it is not directly executable through the complete-file upsert surface. If the exact current full file is available and a complete replacement can be constructed without losing unrelated content, the audited whole-file lane may perform the mutation. If not, stop at that exact mutation-shape boundary rather than rewriting from partial context.

## Computer Hands lane

`computer_hands.*` being present in the deployed operation registry means the request surface is callable. It does **not** mean a worker is online, a request is queued, a lane has a known request identity, or a mutation has executed.

Before creating work:

- read fresh worker status;
- distinguish `tool callable` from `worker online`;
- distinguish `active lane` from `exact request identity`;
- distinguish `request accepted/queued` from `leased/running` and from `executed mutation`;
- do not enqueue duplicate work merely because an active lane name sounds related;
- do not turn an offline worker into recurring queue sludge just to produce a progress receipt;
- require worker success plus authenticated repository target readback before claiming source mutation.

When the worker is offline, continue independent repository/source work that the audited GitHub lane can safely express, or preserve the exact patch-execution boundary. Do not borrow the phone/P0 surface as a substitute.

## Retired / historical worker truth

The presence of current Computer Hands operations does not resurrect historical Command Center Codex worker/job/session APIs. Treat each operation family from the deployed registry independently.

Do not:

- retry retired Command Center worker spellings because old receipts mention them;
- create a replacement worker registry or patch daemon;
- infer current request state from old request IDs or lane prose;
- claim that an offline Computer Hands worker executed a queued mutation.

## P0 / phone firewall

A non-phone source blockage never authorizes use of the gated primary-phone surface. Phone Hands, recovery queues, Nightcore, Pocket TTS, Chromium, Context Organs, and physical acceptance remain with their canonical owners unless fresh P0 evidence explicitly reopens a non-overlapping phone-local front.

Queue liveness or old phone capability receipts do not clear later P0 execution/transport blockers.

## Evidence membrane

Keep these states separate:

`requested → request accepted/queued → leased/running → executed mutation → remote readback → tested → runtime observed → deployed → callable → delivered → accepted`

Skipping an arrow is an evidence bug.

Repository artifacts and patch files can establish intended/implemented source. They cannot prove a worker executed them. A GitHub-admin commit can prove repository mutation only after authenticated target readback. A workflow run that exposes no executable steps cannot promote source to TESTED.

## Duplicate-architecture law

Do not create a neighboring worker registry, patch daemon, phone ingress path, recovery coordinator, alternate overlay owner, or alternate provenance owner because one execution body is offline. Improve existing repository organs through a currently deployed authorized lane, or preserve the exact boundary and advance a different independent front.

## Current TRY FOREVER checkpoint — 2026-08-21 1803

- audited Home Center GitHub admin read/upsert: **CALLABLE YES**;
- Home Center `computer_hands.*` operation surface: **CALLABLE YES**;
- `windows-hands-01`: **OFFLINE**, status `idle`, queueDepth **4**, existing TRY FOREVER lanes present;
- Computer Hands mutation execution in this pulse: **NO**;
- operational-contact owner patch: **PROPOSED_NOT_APPLIED**; exact base owner blob remains `c5de1411a6b68087ae17aff83c032af754587150`;
- reason not queued: worker offline with four pending requests and active TRY FOREVER lanes; adding another deferred request would be queue theater rather than present execution;
- audited GitHub whole-file upsert remains a complete-replacement surface, not a patch interpreter; the large owner was not reconstructed from partial context merely to manufacture an implementation receipt;
- independent repository work advanced instead: operational-contact owner probe v2, hostile counterfeit-edit fixture, Adam doctrine, and the existing touchable source organism;
- gated primary-phone/Phone Hands surface for TRY FOREVER: **FIREWALLED / NOT A FALLBACK**;
- local scratch as completion proof: **FORBIDDEN**;
- source/readback/test/runtime/deploy/delivery states: **MUST REMAIN SEPARATE**.
