# Heartbeat Collapsed Operational Refresh

## Purpose
Keep the surviving collapsed Operator Overlay accessibility owner synchronized with **Home Center operational truth even when heartbeat persistence is unchanged**.

This is a temporal ownership skill, not another speech formatter. The existing projection already knows how to compose owner-supplied HC status with heartbeat/contact truth. The wound is that HC state and heartbeat persisted state change on different clocks.

## Core law
`HEARTBEAT SKIP_UNCHANGED` may skip heartbeat decode/scene/UI work. It must **not** suppress a material change in the visible/collapsed Home Center operational state.

The existing owner derives states such as:

- `CONTROL OFF`
- `HOME CENTER • OFFLINE`
- `REMOTE INPUT • ACTIVE`
- `HOME CENTER • ON`
- optional `• MUTED`

Those states are operator-visible truth. When the details subtree is collapsed, the custom `dragHandle.contentDescription` replaces visible text as the semantic value. Therefore the owner must refresh that custom description from the current status on the ordinary owner refresh cadence, independently of heartbeat persisted-snapshot dedupe.

## Existing-organ composition
Keep this chain:

`OperatorOverlayService.refreshUi -> current owner status -> HeartbeatCollapsedOwnerAccessibility -> dragHandle`

Do not add a second poller, accessibility controller, heartbeat decoder, overlay owner, phone lane, or recovery daemon.

The heartbeat model remains whatever accepted/preserved model is current. Only the owner-supplied operational-status component is refreshed independently.

## Idempotence
Refreshing every owner tick does not mean writing every owner tick.

Compute the next collapsed description, then update `dragHandle.contentDescription` **only when it differs** from the current description. This keeps operational truth live without creating 200 ms accessibility churn.

## Acceptance source
A direct-owner source probe should require all of the following before `SOURCE_WIRED`:

1. the existing owner supplies current operational status to the three-argument collapsed projection;
2. `refreshUi()` invokes collapsed-owner projection independently of heartbeat `SKIP_UNCHANGED` return paths;
3. redundant `contentDescription` writes are guarded by semantic equality;
4. the existing `OperatorOverlayService` remains the sole owner.

Comments, patch files, policy existence, or calls only inside heartbeat model mutation paths do not count as owner wiring.

## Cross-pollination
This wound exists because two correct local optimizations intersect:

- heartbeat persistence dedupe correctly suppresses unchanged heartbeat work;
- collapsed custom speech correctly replaces visible text with a bounded semantic projection.

Together they can freeze HC operational semantics unless owner-status refresh remains independent. Preserve both optimizations; separate their clocks.

## Current PR #329 truth — 2026-08-21 1703
- three-argument collapsed projection: **IMPLEMENTED SOURCE YES**;
- owner-status sub-budget: **IMPLEMENTED SOURCE YES**;
- deterministic operational-contact owner probe: **SOURCE YES / UNEXECUTED**;
- exact combined sole-owner surgery: **PROPOSED_NOT_APPLIED**;
- current authenticated owner blob at plan time: `c5de1411a6b68087ae17aff83c032af754587150`;
- collapsed operational-refresh owner wiring: **NO / PARTIAL_UNSAFE**;
- regression executed: **NO**;
- Android runtime / TalkBack / deployment / phone delivery / acceptance: **NO**.

## P0 / phone firewall
This skill owns no Phone Hands ticket, phone execution, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.

## Done for one pulse
Light this skill only when the temporal coupling between owner operational state and heartbeat dedupe materially changes. Once the owner consumes the refresh law and evidence is updated, keep it dark unless fresh evidence reopens it.
