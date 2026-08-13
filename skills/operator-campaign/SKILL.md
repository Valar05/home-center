# Operator Campaign Skill

## Purpose
Any time an agent asks Drew to run something, the requested action must create or invoke a durable campaign capability rather than a disposable one-off command chain.

## Campaign law
An operator-facing campaign must provide continuing value after the immediate incident is resolved. A script that succeeds once and leaves no reusable capability fails this contract.

Every campaign must provide, where materially applicable:

1. **Stable entrypoint** — one named command remains valid for future `run`, `resume`, `status`, and receipt inspection. Do not invent a new paste chain for each failure.
2. **Durable state** — current stage, last good stage, failure, evidence pointers, timestamps, and campaign history survive process exit/reboot.
3. **Self-heal** — diagnose known failures, invoke governed repair lanes when authorized, rerun bounded verification, and continue the same campaign instead of returning the failure to Drew as the product.
4. **Daemon patience** — back off transient failures and connector limits. Time and latency are never automatic abandonment conditions.
5. **Preservation** — never trample pre-existing user/device work to update the campaign. Preserve and restore local edits or halt at an explicit reconciliation boundary with durable evidence.
6. **Venice governance** — research/plan/jar selection/antagonism/`PLAN_ALLOWED` before substantive repair; Venice completion/code review before stopping.
7. **Receipts** — append-only campaign history and compact latest-state receipts distinguish requested/implemented/tested/deployed/callable/delivered/accepted.
8. **Continuing operations** — health/status, recovery controls, accumulated reviewer memory, and useful monitoring remain available after the first successful run.
9. **Control surface** — on the Android phone, the persistent Home Center notification is a menu for campaigns and recovery. It must include a path to resume/status campaigns, recover Phone Hands, and turn the Adam overlay back on.
10. **Idempotence** — rerunning the campaign should converge toward healthy state rather than duplicate side effects or require new instructions.

## Checkpoint continuation

Campaign execution is checkpointed. A worker owns one bounded, meaningful slice at a time; it does not run indefinitely merely because the overall campaign remains unfinished.

Reaching a checkpoint is permission for the current worker to yield control. **It is not permission to claim the campaign complete, and it does not substitute for Venice `STOP_ALLOWED`.** Campaign completion and worker-slice yield are separate states.

Before yielding a checkpoint, persist enough durable state that a fresh worker can continue without making Drew reconstruct the mission. The checkpoint must record, where materially applicable:

- the current campaign objective and bounded slice;
- what the worker actually completed;
- evidence and receipt pointers for that slice;
- requested, implemented, tested, deployed, callable, delivered, and accepted capability states without rounding them upward;
- unresolved blockers, risks, failed attempts, and recovery observations;
- the current Venice directive and relevant reviewer-memory identity;
- the exact next bounded slice or resume condition.

`CONTINUE_REQUIRED` means the campaign is still active: persist the current checkpoint and advance or resume the same commissioned campaign with another bounded worker slice. It must not be interpreted as "keep this worker alive until cancellation," and it must not be translated into completion, abandonment, or a manual Drew handoff.

A fresh worker must consume the latest durable checkpoint before acting and preserve all earlier mission constraints. Reconstructing the campaign from Drew when a valid checkpoint exists is a checkpoint failure.

`STOP_ALLOWED` remains the campaign-level stopping gate. A worker may yield at a checkpoint before `STOP_ALLOWED`, but the campaign remains explicitly open and resumable until Venice permits actual stopping or Drew changes/cancels the mission.

## Acceptance
A campaign is not accepted merely because its immediate task passed or a worker reached a checkpoint. It must prove that the stable entrypoint, durable state/history, checkpoint/resume path, recovery path, status/control surface, and future rerun behavior exist and remain callable. True campaign completion still requires the applicable Venice stop review.

## Compact law
Do not hand Drew a command. Leave him a machine that keeps helping. Work in bounded checkpoints; yield workers freely, but never confuse yielding with being done.
