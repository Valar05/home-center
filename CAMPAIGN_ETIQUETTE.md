# Campaign Etiquette

Canonical companion: Google Drive document CAMPAIGN_ETIQUETTE — Git Script Campaign Operating Rules (2026-10-21).

## Required boot
Read AGENTS.md, the active contract, and relevant repository doctrine before mutation. For Pose Lab use docs/POSE_CAMPAIGN_FRAMEWORK.md and docs/POSE_LAB_CAMPAIGN_RULES.md in Valar05/pose-lab-v2. Record exact Git SHA, dirty state, mutable surface, locked hashes, execution lane, expected receipt, and acceptance evidence.

## Architecture
Author in Git, pin exact revision, pull into isolated worktree, execute one campaign entry point. Keep contract, campaign-specific apply helper, and shared guard/receipt machinery separate. Use machine-readable mutable paths, structural checks, idempotent stages, and fail-closed ambiguity. Preserve accepted states and avoid unrelated cleanup.

## Separate-process execution
Do not run long jobs in the interactive SSH terminal/session used by Phone Hands. Spawn an independently supervised OS process/task/service with distinct working directory, PID/job ID, redirected and closed stdin/stdout/stderr, persistent log and JSON status receipt. Computer Hands shell.exec has a 120-second timeout and must be a short control operation, not the supervisor. Start-Process alone is insufficient: on 2026-10-21 a background attempt failed because stdout did not close after process exit. Verify the child process and receipt independently.

## Polling
Poll at reasonable intervals. Never hammer the worker with repeated status calls, duplicate tickets, or retries when its heartbeat is stale/queue is backed up. An ambiguous tool error does not prove the launched job failed or stopped. Reconcile before retrying. Continue the user-authorized work within the same turn when possible; never imply a background job is complete when it is not. Outside a live turn, continued monitoring requires an explicitly scheduled task.

## Git and recovery
Use exact push/readback and isolated worktrees. Git LFS missing objects can block checkout; skip smudge only when missing binaries are not required for the specific text-only campaign. Do not reset/clean/stash unrelated user work. Record stage receipts and allow verified partial reruns.

## Evidence gates
Do not equate submitted ticket, fetched Git ref, checked-out worktree, started process, installed dependency, loaded model, passed inference, produced output, and human acceptance. Each has separate proof. Receipt sequence: mutate, verify, stage implementation, verify staged, commit implementation, create receipt, stage/commit receipt, push/readback, serve/test exact revision, human review as needed.

## 2026-10-21 incident reminders
A long installer command was rejected; a Git-authored campaign was accepted. The installer exceeded Computer Hands' 120-second limit. Torch/CLAP/soundfile were not present in the post-timeout check. Background launch returned stdout-handle failure; subsequent worker status became stale/leased. The first worktree checkout failed on missing Git LFS object, while a text-only skip-smudge checkout succeeded. Preserve ComfyUI and other environments. CLAP inference remains unverified.

## Completion rule
Report DONE only after the actual requested result passes its observable test, all receipts are read back, and required human review is complete. Otherwise report the exact unfinished stage and genuine blocker.
