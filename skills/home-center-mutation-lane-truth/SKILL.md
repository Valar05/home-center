# Home Center Mutation Lane Truth

## Purpose

Choose a real currently deployed Home Center mutation lane without resurrecting retired workers, confusing historical capability with current callability, or silently substituting a phone/P0 surface for a non-phone source task.

## Trigger

Use when a task needs Home Center to mutate repository/source state, execute a desktop-local patch, or report whether a worker/job path is actually callable now.

## First move: deployed capability truth

Read the deployed Home Center capability registry before selecting an execution lane. Repository history describes what was built; the deployed registry describes what is callable now.

At the 2026-08-20 TRY FOREVER accessibility checkpoint, the complete deployed `Home_Center_Drive_v2` resource listing exposes:

- audited GitHub admin operations including exact file read and complete-file upsert;
- `command_center_operation` as the bridge to the current Command Center registry;
- no callable `computer_hands.*` tool/resource surface.

A direct `command_center_operation(operation="workers.list")` reports that Command Center Codex agents, jobs, sessions, and workers are permanently retired and are not a Home Center capability.

Therefore current lane families must be treated as:

- **GitHub admin**: authenticated repository administration and complete-file replacement/upsert;
- **Command Center current registry**: only operations that the deployed runtime registry actually accepts; historical Codex worker/job/session APIs are not assumed;
- **Phone Hands / primary-phone**: a distinct shared physical execution surface with its own ownership/firewall and never a substitute for blocked non-phone source mutation.

If `computer_hands.*` reappears in a future deployed capability listing, re-evaluate it from fresh tool evidence before using it. Historical skills, receipts, active-lane prose, or old queue IDs do not make a missing tool callable.

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

## Retired / missing worker lanes

Do not describe a historical desktop patch worker as current merely because repository doctrine or old receipts mention it.

When the deployed Home Center resource registry exposes no `computer_hands.*` surface:

- current Computer Hands callability = **NO / NOT EXPOSED**;
- old worker status, queue depth, active lanes, and request IDs are historical evidence only;
- do not poll, enqueue, or invent a request through a missing surface;
- do not retry Command Center Codex worker spellings after the registry says that worker/job/session family is permanently retired;
- do not create a replacement worker registry or patch daemon;
- continue independent non-overlapping repository/source work or use the audited GitHub admin lane only when its complete-file contract safely matches the mutation.

## P0 / phone firewall

A non-phone source blockage never authorizes use of the gated primary-phone surface. Phone Hands, recovery queues, Nightcore, Pocket TTS, Chromium, Context Organs, and physical acceptance remain with their canonical owners unless fresh P0 evidence explicitly reopens a non-overlapping phone-local front.

Queue liveness or old phone capability receipts do not clear later P0 execution/transport blockers.

## Evidence membrane

Keep these states separate:

`requested → queued → leased/running → executed mutation → remote readback → tested → runtime observed → deployed → callable → delivered → accepted`

Skipping an arrow is an evidence bug.

Repository artifacts and patch files can establish intended/implemented source. They cannot prove a worker executed them. A GitHub-admin commit can prove repository mutation only after authenticated target readback. A workflow run that exposes no executable steps cannot promote source to TESTED.

## Duplicate-architecture law

Do not create a neighboring worker registry, patch daemon, phone ingress path, recovery coordinator, alternate overlay owner, or alternate provenance owner because a historical lane disappeared. Improve existing repository organs through a currently deployed authorized lane, or preserve the exact boundary and advance a different independent front.

## Current TRY FOREVER checkpoint

- audited Home Center GitHub admin read/upsert: **CALLABLE YES**;
- Home Center `computer_hands.*` surface: **CALLABLE NO / NOT EXPOSED IN CURRENT REGISTRY**;
- Command Center Codex workers/jobs/sessions: **RETIRED**;
- gated primary-phone/Phone Hands surface for TRY FOREVER: **FIREWALLED / NOT A FALLBACK**;
- local scratch as completion proof: **FORBIDDEN**;
- source/readback/test/runtime/deploy/delivery states: **MUST REMAIN SEPARATE**.
