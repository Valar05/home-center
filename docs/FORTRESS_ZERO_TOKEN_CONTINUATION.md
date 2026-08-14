# Fortress Online: Zero-Token Continuation

Status: source implementation and exact-head validation candidate. Phone deployment and human acceptance remain separate.

## Mission

When paid or hosted inference is exhausted, Fortress does not stop and does not silently spend. Home Center keeps ownership of the existing durable work request. The `fortress_dungeon_v2` route compiles that exact request into the existing typed phone-local Coding Dungeon. The phone then prefers local deterministic work and verification. No second scheduler, queue, browser farm, or control plane is introduced.

## Local token-drought authority

The phone owns `~/.config/home-center/fortress-token-drought.v1.json`. Absence means off. A valid enabled sentinel skips the fixed Codex stage. A corrupt or schema-invalid existing sentinel fails closed and also skips paid inference. Remote `dungeon_run` and `home_center_work_request` schemas contain no field that can enable, disable, replace, or bypass this sentinel.

```sh
dungeon-v2 drought status
dungeon-v2 drought on --reason "Paid inference is exhausted."
dungeon-v2 drought off --reason "Owner restored paid inference authority."
```

Drought mode continues through the existing phone-local Adam/Venice adapter, then the non-mutating low-local judge, then deterministic verification or HOLD. A potentially mutated failed stage remains `QUARANTINED`; it is never retried automatically.

## Existing Home Center queue

Submit one ordinary `home_center_work_request` with:

- `route: fortress_dungeon_v2`;
- a stable `requestId`;
- exact `requestText`;
- one or more exact `acceptance` strings;
- optional constraints and fixed profile selectors.

Home Center persists the work item and invokes the existing dungeon admission operation. Relay admission is `QUEUED` or `RUNNING`. A phone receipt of `SUCCEEDED` closes only the bounded work item and means a verified isolated Git checkpoint. It never means pushed, merged, deployed, installed, delivered, or human-accepted. Those remain separate evidence gates.

## Capability truth

- Requested: yes.
- Combined source: this branch.
- Deterministic tests: required before promotion.
- Home Center deployed with this route: no.
- Primary phone updated and advertising `coding_dungeon_v2`: no.
- Local drought canary on the phone: no.
- End-to-end work request to verified checkpoint: no.
- Delivered or human-accepted: no.

## Runtime promotion gates

1. Merge only after exact-head tests and review.
2. Deploy Home Center from exact clean main and read back release identity.
3. Update the physical phone from the same exact commit and run `setup_mobile_coding_dungeon_v2.sh`.
4. Enable drought locally, prove Codex was skipped, and capture the local ledger event.
5. Admit a harmless `fortress_dungeon_v2` work request and read back queue, relay, job, tmux, worktree, verification, and status receipts.
6. Restore paid inference only through the local phone command when the owner chooses.
