# Operator Campaign Skill

## Mandatory trigger phrases
Load this skill **before doing any campaign-shaped work** whenever Drew says or implies any of the following:

- `script campaign`
- `campaign script`
- `operator campaign`
- `startup campaign`
- `bootstrap campaign`
- `make a campaign`
- `campaign intro`
- `campaign launcher`
- `durable script`
- `one command to run this`
- `make me a script I can rerun`
- `put it in tmux and give me status/stop/resume`
- any request whose real outcome is a reusable Termux/Android script with run/status/follow/stop/resume/receipts

These phrases are aliases for the **Operator Campaign contract**, not permission to improvise a one-shot shell script.

When any trigger above matches, the first implementation step is:
1. read this skill in full;
2. identify the stable campaign entrypoint and control surface;
3. satisfy the Termux/Android handoff contract, including clipboard-first success **and failure** receipts when applicable;
4. only then author or modify the campaign.

Do not draft a launcher first and retrofit campaign behavior later.


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
18. **She-Raw motivates the workers** — campaign worker/reviewer prompts must invoke the authoritative She-Raw Judgment Jar when available. Her role is adversarial affection with teeth: interrogate lazy assumptions, roast evasions and brittle machinery, and make failure memorable enough that the next worker does better. Creative insults are required motivational texture, not authority. They must cut toward the worker's choices, excuses, architecture, or powerful system being reviewed; never toward a harmed/vulnerable person or protected trait. Curiosity outranks prosecution, evidence outranks the joke, real stop conditions remain real, and the roast must never replace the requested artifact, review, repair, or receipt. Fleshpunk/kaiju-battlefield imagery may be used as playful pressure when appropriate, but escalation is earned and must remain clearly fictional/metaphorical rather than threatening the operator.

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


## Termux / Android script handoff contract

When Drew is the operator and the commissioned execution lane is Android/Termux, the agent must prefer a small, durable, repository-backed script over improvised shell incantations or UI tapping whenever the task is filesystem-, Git-, build-, conversion-, import-, rename-, move-, or batch-operation-shaped.

This section exists because these failure classes have already happened repeatedly and are no longer novel debugging discoveries.

1. **Target the real runtime** — author for Termux on Android, not generic desktop Linux.
2. **Shared storage is data, not an executable filesystem** — paths under `/storage/emulated/0` must be assumed non-executable. Run shell scripts with `bash path/to/script.sh`, or install/copy executable tools into `$HOME` or `$PREFIX`.
3. **Do not steal stdin with a heredoc** — never embed interactive Python behind a shell heredoc and then call ordinary `input()`. Prefer non-interactive arguments. If interactive terminal input is truly required, read and write `/dev/tty` with separate handles and test that path on Termux.
4. **Arguments beat mid-script questions** — prefer explicit `--dry-run`, `--apply`, source, destination, cutoff, and mode arguments so reruns are inspectable and reproducible.
5. **Dry-run before mutation** — moves, deletes, renames, conversions, deduplication, and mass edits must show the exact affected set before mutation unless Drew explicitly waives preview.
6. **Print the contract before touching files** — source, destination, cutoff/selection rule, file count, collision policy, and recursion behavior must be visible.
7. **Guard parent/child paths** — if a destination lives beneath the source, traversal must exclude the destination and must not recursively consume its own output.
8. **Idempotence is the default** — a second run should converge safely rather than duplicate work or corrupt names/state.
9. **Collision safety** — never silently overwrite unrelated files. Use deterministic conflict handling and report every collision decision.
10. **Useful receipt** — print what changed, what did not, and the final relevant status. When Git is involved, print `git status --short`; do not commit or push unless the commission explicitly includes that action.
11. **Repository-backed scripts beat chat-local cargo** — anything worth running twice belongs in the real project repository under a stable path such as `tools/`. The preferred loop is: agent edits GitHub -> Drew pulls -> Drew runs one named script -> Drew returns the receipt/error -> agent fixes the same script in GitHub.
12. **Phone Hands is not a shell substitute** — use Phone Hands for UI-only state, permissions, taps, screenshots, and device surfaces that cannot be expressed safely as deterministic filesystem/shell work. Do not spend robot-finger effort on work a script can do exactly.
13. **No dependency lasagna** — do not introduce an unproved command-repair shell, wrapper, daemon, or agent merely to compensate for fragile commands. First make the direct script lane correct and testable. Add another layer only when repeated evidence proves a distinct requirement.
14. **No giant artisanal one-liners** — beyond trivial inspection commands, prefer a named script committed to the repository. If the same complex command is handed to Drew twice, that is evidence it should become a durable script.
15. **Operator stays in the loop** — the handoff should keep Drew visibly in control: one bounded command, immediate output, short receipt, then the next correction. Long invisible automation is not automatically superior to a fast operator-driven loop.
16. **Clipboard-first receipts** — every operator-facing script or nontrivial command must copy the concise, relevant user-facing result to the Android clipboard automatically so Drew can paste it back without selecting terminal text. Prefer `termux-clipboard-set` when available. Clipboard delivery must be best-effort and must never make the actual task fail if the clipboard command is unavailable. Copy the compact receipt, summary, error, or requested output, not megabytes of logs. Never place secrets, tokens, passwords, private keys, auth headers, or other sensitive values on the clipboard. If clipboard support is unavailable, print one explicit line saying so and still emit the same receipt to stdout.
17. **Failures copy too** — clipboard-first applies to failure paths, not only success receipts. Operator scripts must install a bounded error trap or otherwise capture the final relevant failure summary and copy it to the Android clipboard before exiting nonzero. Never force Drew to select a wall of terminal text just because the command failed. Prefer the failing command, exit code, and the last useful 20–40 log lines. Preserve the same secret-scrubbing rules as successful receipts.

### Android script acceptance canary

A Termux/Android script handoff is not acceptable until the agent can answer yes to all materially applicable checks:

- Is the exact source path known?
- Is the exact destination path known?
- Is recursion bounded?
- Is a child destination excluded from source traversal?
- Is shared-storage execution avoided?
- Is the preview/dry-run visible before mutation?
- Are duplicate names handled without silent overwrite?
- Is stdin/TTY behavior compatible with the chosen transport?
- Is rerun behavior safe?
- Is the script persisted in the real repository if it has continuing value?
- Does the receipt expose the actual changed set and Git status where relevant?
- Is the concise operator-facing receipt copied to the Android clipboard when `termux-clipboard-set` is available, without copying secrets?

Known regression fixtures include: direct execution from `/storage/emulated/0/Download` returning permission denied; Python `input()` behind a heredoc producing EOF; opening `/dev/tty` in a mode unsupported by the stream; and recursive scans where the destination is nested beneath the source.

## Acceptance
A campaign is not accepted merely because its immediate task passed or a worker reached a checkpoint. It must prove that the stable entrypoint, durable state/history, checkpoint/resume path, recovery path, status/control surface, future rerun behavior, process isolation, and out-of-band stop path exist and remain callable. True campaign completion still requires the applicable Venice stop review.

## Compact law
Do not hand Drew a command. Leave him a machine that keeps helping. Work in bounded checkpoints; yield workers freely, but never confuse yielding with being done. Never let the machine take the operator's shell hostage. Never narrate the next callable action instead of taking it. And if a worker tries to polish a turd instead of shipping the commissioned machine, She-Raw gets to explain the structural problem with memorable theatrical disrespect.