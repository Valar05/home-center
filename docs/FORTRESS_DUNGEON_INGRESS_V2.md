# Fortress Online: Typed Coding Dungeon Ingress v2

Status: source contract and phone-local coordinator candidate  
Promotion state: **not deployed and not device-accepted**

## Outcome

`drive_operation(operation="dungeon_run")` admits an exact, receipt-first coding campaign to the registered Android phone. The phone creates one deterministic job record, isolated Git worktree, branch, and tmux session. The campaign can continue without ChatGPT or a visible Android UI.

This surface does not use Command Center, Workspace agents, ChatGPT Work subagents, Phone Hands UI control, the operator overlay, Shizuku, a powered desktop, or a caller-provided shell command.

## Closed remote schema

The caller may provide only:

- `requestId`, `campaignId`, and an opaque phone-local `workspaceId`;
- `objective`, exact `acceptance`, and optional binding `constraints`;
- `taskKind`: `implement`, `repair`, `verify`, `review`, or `research`;
- `lane`: `critical`, `standard`, or `background`;
- fixed `budgetProfile` and `verificationProfile` selectors;
- the exact fixed policies `codex-local-low-deterministic-v1` and `checkpoint-only`.

Unknown fields fail closed. In particular, the schema rejects manifest paths, filesystem paths, shell text, command strings, argv, URLs, environment maps, model names, branch names, remote names, and publication destinations.

The authenticated owner may use the critical lane only with a concrete `criticalReason`. Status reads outrank all mutation admissions; critical mutation admissions outrank standard and background work. Standard and background work share a serialized lane, while critical work has a separate tmux/process lane and retains normal CPU priority.

## Deterministic decay ladder

1. **Deterministic coordinator** validates exact intent, resolves the trusted local workspace registry, creates the durable job, computes all paths/names, and creates the isolated worktree.
2. **Codex CLI** runs with fixed argv: `codex exec --sandbox workspace-write --ask-for-approval never --json <objective packet>`.
3. If Codex is unavailable or fails without mutating the worktree, the same exact objective decays to the existing phone-local Adam/Venice worker.
4. If that worker is unavailable or fails cleanly, the tiny local judge may classify `HOLD` versus `VERIFY`; it receives no mutation authority and cannot select commands.
5. Trusted phone-local argv arrays perform deterministic verification. No verification command crosses the remote boundary.

Any timed-out or failed inference stage that may have changed the worktree enters `QUARANTINED`. The coordinator never retries an ambiguous mutation automatically.

## Truth and recovery

Firestore owns relay admission and exact-intent idempotency. The phone owns campaign truth under:

`~/.local/state/home-center/coding-dungeon-v2/`

- `jobs/<jobId>.json` — atomic current state outside tmux;
- `runs/<jobId>/ledger.jsonl` — append-only transitions;
- `runs/<jobId>/*.log` — bounded executor and verification evidence;
- `worktrees/<jobId>/` — isolated checkpoint-only Git worktree;
- `locks/` — exact-job and lane serialization.

An expired relay admission lease requeues only the same typed command. A new lease ID prevents a late, stale device completion from overwriting the recovered admission. Replaying the same `requestId` and input hash attaches to the same local job and tmux session. Reusing a request ID for different intent fails closed.

## Operations

- `dungeon_run` — enqueue exact campaign admission.
- `dungeon_command_status` — read the owner-scoped relay command until the phone returns the local submit receipt.
- `dungeon_status` — enqueue a typed read of the opaque local `jobId`.
- `dungeon_command_status` — read that status command and its bounded campaign receipt.

`SUCCEEDED` means the trusted verification profile passed and the checkpoint remains isolated. It does not mean pushed, merged, deployed, installed, or human-accepted.

## Source acceptance

```sh
node functions/dungeon_run_contract.test.js
node tools/fortress_dungeon_ingress_contract_test.mjs
python3 tools/test_mobile_coding_dungeon_v2.py
python3 -m py_compile tools/mobile_coding_dungeon_v2.py tools/android_phone_home_center_relay.py
```

## Promotion gates

1. Merge only after repository CI and human review.
2. Deploy the Home Center MCP/phone relay from an exact clean main commit.
3. Update the physical phone checkout from that exact commit.
4. Run `tools/setup_mobile_coding_dungeon_v2.sh` on the phone.
5. Verify the phone registers `coding_dungeon_v2`.
6. Admit one probe campaign; read back the exact submit receipt, local ledger, isolated worktree, and terminal status.
7. Deliberately replay the same intent, conflict the same request ID, expire an admission lease, and induce an ambiguous dirty timeout. Verify attach, conflict, same-command recovery, and quarantine respectively.
8. Record device/runtime acceptance separately from source and mechanical receipts.
