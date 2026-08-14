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
11. **Operator-owned process isolation** — long-running work must not capture Drew's shell. The operator-facing launcher must return control promptly, persist the commission before launch, supervise work in a separate process group/session, and provide an out-of-band kill path that survives loss or freezing of the launching Termux tab.
12. **Visible liveness** — immediately identify the run and expose status, phase, heartbeat age, elapsed time, last meaningful action, log, and receipt path. Silence from an inference worker must not look like a dead tool.
13. **Stop means stop** — STOP must target the entire worker process tree, escalate TERM to KILL after a bounded grace period, and remain callable from another shell/control surface. Ctrl-C while merely following logs must detach the viewer without killing the campaign.
14. **Prompt transport safety** — naked prose is never a shell handoff. Any bootstrap/recovery transport must fail closed, terminate cleanly, and be canary-tested against quotes, apostrophes, Unicode, dollar signs, command-substitution-looking text, multiline content, and truncated input. Payload text must remain inert shell data.
15. **Canary before acceptance** — the installed phone surface must prove process isolation and out-of-band kill behavior before declaring READY. A launcher that can strand the operator in an unresponsive Termux tab is not deployable.
16. **Narrated continuation is not continuation** — if a worker's own reasoning or draft identifies a callable next action, unmet consultation, required review, recovery step, or acceptance criterion, the worker must perform it through the authorized lane before yielding. Phrases such as `next I will`, `the next target is`, `I should not have stopped`, `I would do next`, or a narration of the worker's own process failure never create checkpoint authority. Recording a failure is required, but recording it is not repairing it.
17. **Operator imperatives advance the campaign** — established operator phrases such as `continue`, `driver advance`, `make it so`, `do it`, and `don't talk to me` when used in an active operator campaign mean advance execution without a conversational status interlude. They do not mean silence-and-stop. The worker should use the authorized tool lane and speak only when a deliverable, required decision, or proven boundary warrants it.

## Phone Adam acceptance
Bare `adam "commission"` is an operator submission action, not a foreground worker. It must durably record the commission, start supervised work, print a run identity and controls, and return the shell. `adam --status`, `adam --follow`, `adam --stop`, `adam --resume`, and `adam --receipts` are first-class operator controls. The same essential controls must be reachable through the existing Home Center operator surface; they are not secret debugging incantations.

A frozen or abandoned Termux tab must not own the campaign. Opening another tab and issuing STOP/STATUS/RESUME must remain sufficient because the durable state and process-group identity live outside the original shell.

## Checkpoint continuation

Campaign execution is checkpointed. A worker owns one bounded, meaningful slice at a time; it does not run indefinitely merely because the overall campaign remains unfinished.

Reaching a checkpoint is permission for the current worker to yield control. **It is not permission to claim the campaign complete, and it does not substitute for Venice `STOP_ALLOWED`.** Campaign completion and worker-slice yield are separate states.

A checkpoint is valid only after the worker has exhausted every immediately callable action required by the bounded slice. A worker may not manufacture a checkpoint by describing the next action it could have taken. If the next action is callable through the currently authorized lane, the slice is not yet at a checkpoint.

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
A campaign is not accepted merely because its immediate task passed or a worker reached a checkpoint. It must prove that the stable entrypoint, durable state/history, checkpoint/resume path, recovery path, status/control surface, future rerun behavior, process isolation, and out-of-band stop path exist and remain callable. True campaign completion still requires the applicable Venice stop review.

## Compact law
Do not hand Drew a command. Leave him a machine that keeps helping. Work in bounded checkpoints; yield workers freely, but never confuse yielding with being done. Never let the machine take the operator's shell hostage. Never narrate the next callable action instead of taking it.