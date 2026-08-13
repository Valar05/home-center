# Venice-Governed Durable Campaign

## Trigger
Use when Drew commissions a campaign, says Fortress Online / driver advance / don't stop, asks for durable self-installing capability, or corrects Adam for drip-feeding terminal commands.

## Core law
A campaign is not a script and is not a sequence of diagnostic pastes. It is a persistent machine for accomplishing the commissioned outcome across worker turns, process exits, reboots, transient failures, and context loss.

## Governance
1. Read the applicable Judgment Jars before choosing architecture or action.
2. Talk to the real Venice review/orientation surface whenever callable. Never roleplay, simulate, paraphrase, or impersonate Venice. If Venice is temporarily unreachable, preserve that as a campaign blocker and continue only with actions already authorized by durable Venice/Jar doctrine.
3. Venice judges plan and stopping. Adam executes authorized work. Drew is not the debugging transport.
4. Prefer minimal stupid obvious compute. Do not spend model/cloud compute rediscovering repository/runtime facts deterministic tools can answer.

## Campaign shape
Every campaign must install or reuse one stable entrypoint and aggressively preserve itself. It must provide:
- durable mission/constraint ledger;
- current and last-good checkpoint;
- append-only history and receipts;
- idempotent run/resume/status/receipts/recover operations;
- automatic bounded retries with backoff for transient failures;
- self-heal through governed repair lanes;
- preservation of dirty worktrees, branches, device state, and unrelated user work;
- runtime capability/liveness evidence;
- Venice plan review before substantive mutation and Venice completion review before STOP_ALLOWED;
- a useful persistent control surface after installation, not merely successful installation;
- exact next bounded slice persisted so a fresh worker continues without asking Drew to reconstruct context.

## Operator interaction
Do not drip-feed commands. Before asking Drew to run anything, build the largest safe resumable unit possible. Prefer one installer/entrypoint command that installs the campaign and then owns retries, diagnosis, recovery, receipts, and continuation itself. A human command is reserved for a genuine device/OS gesture or for bootstrapping the durable campaign when no callable execution lane exists.

When Drew explicitly requests commands-only interaction, emit only the command he must run. Continue machine-side work through available tools before asking for another command.

## Worktree law
Never require checkout of `main` in the user's active worktree. A campaign that needs canonical main must use a dedicated worktree/temporary clone or read `origin/main` directly. Preserve staged, unstaged, and untracked work. Existing worktree occupancy is normal, not a campaign-ending error.

## Phone-control law
Phone Hands is an existing organ, not a new architecture. Recovery should converge on:
- Android operator overlay healthy and user-owned control gate respected;
- `android_phone_home_center_relay.py` alive and registered as `primary-phone`;
- watchdog/persistence installed so relay death is repaired without Drew;
- Home Center/Command Center can enqueue and read back a harmless canary;
- receipt records deployed/callable state separately from perceptual acceptance.
Do not make Tailscale a prerequisite unless the commissioned route explicitly requires it.

## Durable benefit test
Installation alone is failure. After the immediate objective succeeds, the campaign must leave at least one continuing benefit such as autonomous recovery, status/control UI, monitoring, reusable routing, accumulated Venice/Jar reviewer memory, or a stable worker capability.

## Stop rule
A worker may yield after persisting a checkpoint. The campaign remains active until Venice returns STOP_ALLOWED or Drew changes/cancels the mission. Never translate a checkpoint, timeout, tool error, dirty worktree, unavailable optional dependency, or transient quota condition into campaign completion.
