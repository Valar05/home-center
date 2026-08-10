# Mobile Coding Dungeon

A persistent, bounded execution ecology for Home Center on Android/Termux.

## Identity boundary

The Dungeon is **Hands**, not an independent strategic agent. A run must name an owner, principal, workspace, objective, steps, and stop conditions. It may continue an authorized trajectory; it may not invent a new mission.

## V1 anatomy

- **Warden** — manifest validation, cycle/retry ceilings, timeouts, stop conditions.
- **Hands** — Termux commands and existing Phone Hands/Android capabilities.
- **Scribes** — append-only per-run ledger plus manifest snapshot.
- **Hounds** — repeated-cycle observation and verification.
- **Scars** — regex-matched known failure -> bounded known repair -> reverify.
- **Local judge** — optional tiny phone model for low-stakes ambiguity. Deterministic mechanisms remain preferred.
- **Adam** — remote strategic principal; difficult or boundary-changing decisions escalate rather than being invented locally.

## Manifest contract

JSON works with no extra dependency. YAML is supported when PyYAML is installed.

Every manifest requires:

- `name`
- `owner`
- `principal`
- `workspace` (v1: Git worktree root)
- `objective`
- `steps`
- `stop`

Supported v1 step types are `command`, `verify`, and `local_judge`.

A scar contains a regex `match`, a bounded `repair`, and optional `max_uses`. Repairs are not synthesized by the Dungeon; they are explicit durable behavior authorized in the manifest.

## Evidence

Every run creates:

`~/.local/state/home-center/coding-dungeon/<run-id>/`

with:

- `manifest.json` — exact authority packet used for the run
- `ledger.jsonl` — append-only start/cycle/command/scar/checkpoint/complete-or-stop evidence

The runner captures initial Git HEAD and dirty state, command output/exit status, failure signatures, scar usage, and diff statistics at checkpoints.

## Safety/authority rules

1. No new mission is generated locally.
2. The local model is not granted raw strategic authority.
3. Deterministic reflexes and known scars take precedence over model judgment.
4. Repeated identical failures stop rather than loop forever.
5. Every command has a timeout.
6. Environment exposure is minimized to ordinary Termux variables plus `HC_*` configuration.
7. A run ending `green` means its declared verification steps passed; it does not imply deployment unless deployment/readback is itself part of the manifest.

## Install on the phone

From the `feature/mobile-coding-dungeon` worktree:

```bash
chmod +x tools/setup_mobile_coding_dungeon.sh
bash tools/setup_mobile_coding_dungeon.sh
```

The installer creates `~/bin/dungeon`, installs an example bounded manifest, and executes it as the physical-phone smoke test.

## V1 acceptance

The Coding Dungeon is deployed on a phone only after the physical device proves:

1. installer completes;
2. example manifest executes;
3. ledger exists on-device;
4. both verification steps are recorded with exit 0;
5. final event is `complete` with result `green`;
6. a deliberately failing manifest stops at its configured repeated-failure or cycle limit;
7. an explicit scar can repair a known synthetic failure and the subsequent verification passes.
