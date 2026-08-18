# Heartbeat Owner Source Capability Probe

## Purpose

Stop re-deriving the existing Operator Overlay deep-detail source state by hand. Classify the actual `OperatorOverlayService.java` as legacy, fully source-wired, or partial/unsafe without laundering source inspection into Android runtime proof.

## Trigger

Use when:

- a deep-detail owner patch exists or is queued;
- a later heartbeat needs to know whether the real existing owner actually changed;
- a branch moved while a patch executor was offline;
- a worker/result claims the owner seam was applied and needs deterministic repository readback;
- source doctrine and actual owner code may have drifted.

## Canonical organ

Run:

```text
python tools/try_forever_heartbeat_detail_owner_probe.py
```

Use `--require-wired` only when the caller intentionally wants a nonzero exit code until the owner reaches the full source contract.

The probe classifies:

- `LEGACY_OWNER` — the heartbeat detail still owns legacy destructive layout/truncation markers and none of the required deep-detail owner markers;
- `SOURCE_WIRED` — every required policy/restore/passive-ownership marker exists and the heartbeat-detail legacy markers are gone;
- `PARTIAL_UNSAFE` — any mixed state. This is deliberately not rounded up to success.

## Required source invariants

`SOURCE_WIRED` requires all of these in the existing owner:

- `heartbeatDetailPresentationGeneration`;
- `HeartbeatDetailSurfacePolicy.maxViewportHeightPx`;
- heartbeat-detail movement-method installation;
- passive focus/click/long-click ownership reassertion after movement-method installation;
- `restoreHeartbeatDetailScrollAfterLayout`;
- `HeartbeatDetailSurfacePolicy.clampScrollY`.

It rejects heartbeat-detail legacy ownership when it still finds:

- `heartbeatDetail.setMaxLines(5);`;
- heartbeat-detail `END` ellipsis in the initialization block;
- the retired ad-hoc `String safe = detail == null || detail.trim().isEmpty()` formatter.

Unrelated `END` ellipses elsewhere in `OperatorOverlayService` do not count. Spotify/latest truncation must not poison the heartbeat-detail verdict.

## Evidence law

The probe is repository/source evidence only.

A `SOURCE_WIRED` result may support:

- implemented existing-owner source = **YES**.

It does **not** support:

- tests passed;
- Android UI rendered;
- touch scrolling worked;
- keyboard focus behaved correctly;
- TalkBack exercised the surface;
- deployment;
- phone callability/execution;
- delivery;
- acceptance.

Those states require their own authorized evidence lanes.

## Mutation law

The probe does not mutate anything. It owns no renderer, controller, poller, worker, queue, phone path, or P0 coordination. A patch artifact or queued Computer Hands ticket must still be read back from GitHub before changing the capability ledger.

If the result is `PARTIAL_UNSAFE`, stop source promotion and review the actual diff. Do not complete the missing markers by inventing a neighboring owner.

## P0 / phone firewall

This skill never opens or consumes Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance. It can classify source while all of those remain dark.
