# Home Center Mutation Lane Truth

## Purpose

Choose a real currently deployed Home Center mutation lane without resurrecting retired workers, confusing queue admission with execution, or silently substituting a phone/P0 surface for a non-phone source task.

## Trigger

Use when a task needs Home Center to mutate repository/source state, execute a desktop-local patch, or report whether a worker/job path is actually callable now.

## First move: deployed capability truth

Read the deployed Home Center capability registry before selecting an execution lane. Repository history describes what was built; the deployed registry describes what is callable now.

Current lane families are distinct:

- GitHub admin tools / `github_admin.*` operations: authenticated repository administration and complete-file upsert.
- `computer_hands.*` Home Drive operations: Windows Computer Hands worker registration/status/request lifecycle.
- Command Center: current browser/app/project/phone-hands surfaces only. Do not assume historical Codex jobs/workers/sessions still exist.
- Phone Hands: shared phone execution surface with its own ownership/firewall. Never use it merely because a desktop/source lane is blocked.

If a direct call to a historical Command Center jobs/workers operation reports that agents, jobs, sessions, and workers are permanently retired, preserve that as capability truth. Do not keep trying spelling variants or build a shadow worker API.

## GitHub admin lane

Use audited GitHub admin writes when the exact requested repository mutation can be expressed safely through the deployed tool.

For an existing file:

- read the exact current file and blob first;
- preserve all unrelated content;
- supply the current blob lock on replacement;
- remember that `github_admin.files.upsert` replaces complete contents; it is not a patch interpreter;
- verify the resulting remote blob/commit and review the actual diff;
- do not call a locally reconstructed file proof until remote readback confirms it.

If a large-file whole replacement cannot be constructed safely from exact current content, stop at that boundary rather than rewriting from partial context.

## Computer Hands lane

`computer_hands.request.create` is a separate non-phone lane. Before depending on it:

1. read `computer_hands.worker.status`;
2. separate `online`, `status`, `queueDepth`, and `activeLanes`;
3. make the request idempotent with a stable request/ticket/lane identity;
4. for `shell.exec`, require the explicit write/high-risk approval already authorized by the commission;
5. make source mutation fail closed on stale blobs, unexpected diffs, patch-check failure, or branch movement;
6. use lease-protected pushes rather than overwriting a newer branch head.

A queued ticket means only **QUEUED**. It does not mean leased, running, completed, source-applied, tested, deployed, delivered, or accepted.

An offline worker may retain queued work, but no capability ledger may promote it until a completed request receipt and target-system readback exist.

### Active lane is not request identity

`worker.status.activeLanes` is an aggregate scheduling signal. It does **not** identify which ticket owns the lane, prove that a remembered request ID still exists, or authorize creating another request merely because the remembered ticket cannot be found.

When a lane appears active but `computer_hands.request.status` for the expected request/ticket returns not found:

- revoke the specific queued-ticket claim;
- preserve the lane as **OCCUPIED_OR_UNRESOLVED**, not empty and not proven queued for that request;
- do not enqueue a duplicate surgery blindly into the same lane;
- require either an exact request/ticket identity, a completed worker receipt, or fresh target-system readback before promoting or replacing the work;
- continue independent non-overlapping fronts rather than manufacturing queue churn.

This prevents stale chat/PR receipts from becoming current queue authority and preserves fair shared-lane scheduling.

## P0 / phone firewall

A non-phone source blockage never authorizes use of the gated primary-phone surface. Phone Hands, recovery queues, Nightcore, Pocket TTS, Chromium, Context Organs, and physical acceptance remain with their canonical owners unless fresh P0 evidence explicitly reopens a non-overlapping phone-local front.

## Evidence membrane

Keep these states separate:

`requested → queued → leased/running → executed mutation → remote readback → tested → runtime observed → deployed → callable → delivered → accepted`

Skipping an arrow is an evidence bug.

Repository artifacts and patch files can establish intended/implemented source. They cannot prove a worker executed them. Worker receipts can prove execution attempts. Only target-system readback proves the repository/runtime state actually changed.

## Duplicate-architecture law

Do not create a neighboring worker registry, patch daemon, phone ingress path, recovery coordinator, or alternate overlay owner because the canonical lane is offline. Improve or wait on the canonical lane and continue other independent work instead.
