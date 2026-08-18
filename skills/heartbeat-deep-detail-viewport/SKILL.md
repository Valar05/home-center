# Heartbeat Deep Detail Viewport

## Purpose

Keep explicit heartbeat Why / Consequence / Evidence / Source detail fully inspectable without letting long evidence consume the whole Operator Overlay.

## Trigger

Use when the existing heartbeat detail surface already owns the correct full projected detail but its visible native presentation can hide later content behind destructive ellipsis or another non-inspectable viewport bound.

## Law

1. The existing `OperatorOverlayService` and its existing `heartbeatDetail` surface remain the sole Android owner.
2. `HeartbeatEvidenceDetailProjection` remains the explicit typed-detail formatter. Do not invent another evidence formatter to solve layout.
3. Spatial bounds and semantic bounds are different contracts. Keep the visible detail well bounded, but preserve the full already-bounded projected detail behind vertical touch inspection.
4. Do not use `END` ellipsis when it makes omitted Evidence/Source text unreachable from the sighted/touch surface.
5. Reuse `OverlayUiPolicy.MIN_TOUCH_TARGET_DP` as the detail touch floor; do not grow a second 48dp literal that can drift.
6. TalkBack content remains the same full explicit detail. Automatic/collapsed speech stays separate and must not inherit the deep-detail payload.
7. Selecting a new light may reset the detail well to the top and announce through the existing mute-aware owner path. A background model/evidence refresh must not yank an operator who is already reading deeper text back to the top.
8. Source wiring, successful tests, runtime scrolling, runtime TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
9. Do not create a neighboring detail controller, renderer, state store, overlay, phone path, or P0 owner.

## Source organ

`HeartbeatDetailSurfacePolicy.fromDetail(...)` projects the existing explicit detail into these source semantics:

- full text retained;
- full content description retained;
- five-line visible well;
- no destructive end ellipsis;
- vertical overflow inspectable;
- the existing shared overlay minimum touch target.

The Android owner must explicitly consume those semantics before `existing-owner wiring = YES` can be claimed. The exact proposed owner delta is preserved at `docs/try-forever/operator-overlay-heartbeat-detail-scroll-wiring.patch`; a patch artifact is not owner implementation.

## Regression doctrine

Source fixtures should prove:

- long detail remains byte-for-byte equivalent at the Java String level after established surrounding trim;
- content description equals the full projected detail;
- the visible viewport stays bounded;
- overflow is marked scroll-inspectable rather than ellipsized away;
- the touch floor aliases the existing overlay touch contract;
- empty detail receives one deterministic fallback;
- interior Unicode/evidence content is not rewritten by layout policy.

Owner review should separately verify that explicit selection may reset scroll to the beginning while background refresh preserves the current reading position.

Regression source is not TESTED evidence until an authorized runner executes it successfully.

## P0 / phone firewall

This skill owns no Phone Hands ticket, primary-phone execution, queue/relay probe, Home Center recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organ action, physical acceptance chain, or P0 coordination.
