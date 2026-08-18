# Heartbeat Deep Detail Viewport

## Purpose

Keep explicit heartbeat Why / Consequence / Evidence / Source detail fully inspectable without letting long evidence consume the whole Operator Overlay or silently acquire navigation ownership.

## Trigger

Use when the existing heartbeat detail surface already owns the correct full projected detail but its visible native presentation can hide later content behind destructive ellipsis or another non-inspectable viewport bound.

## Law

1. The existing `OperatorOverlayService` and its existing `heartbeatDetail` surface remain the sole Android owner.
2. `HeartbeatEvidenceDetailProjection` remains the explicit typed-detail formatter. Do not invent another evidence formatter to solve layout.
3. Spatial bounds and semantic bounds are different contracts. Keep the visible detail well bounded, but preserve the full already-bounded projected detail behind vertical touch inspection.
4. Do not use `END` ellipsis when it makes omitted Evidence/Source text unreachable from the sighted/touch surface.
5. Reuse `OverlayUiPolicy.MIN_TOUCH_TARGET_DP` as the detail touch floor; do not grow a second 48dp literal that can drift.
6. TalkBack content remains the same full explicit detail. Automatic/collapsed speech stays separate and must not inherit the deep-detail payload.
7. The detail well is a **passive touch-scroll surface**, not a keyboard-navigation owner and not a click/long-click action. Installing or replacing an Android movement method can mutate `TextView` focus/click defaults; therefore the native owner must explicitly restore policy-owned `focusable`, `clickable`, and `longClickable` state **after** `setMovementMethod(...)`.
8. Passive detail scrolling must not become evidence for `root.findFocus()` heartbeat viewport ownership. Selection, heartbeat-button keyboard focus, visible viewport contact, and TalkBack accessibility focus remain separate contracts.
9. Selecting a new light resets the detail well to the top and may announce through the existing mute-aware owner path.
10. A background model/evidence refresh preserves the current reading position only while that position still exists in the refreshed layout. After layout, clamp the old `scrollY` to the new legal range; content shrink must never strand the reader beyond the new bottom.
11. Any deferred background scroll restore is owned by the detail presentation that scheduled it. A newer detail presentation invalidates the stale restore before it can yank a newer explicit selection or refresh.
12. Source wiring, successful tests, runtime scrolling, runtime TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
13. Do not create a neighboring detail controller, renderer, state store, overlay, phone path, or P0 owner.

## Source organ

`HeartbeatDetailSurfacePolicy.fromDetail(...)` projects the existing explicit detail into these source semantics:

- full text retained;
- full content description retained;
- five-line visible well;
- no destructive end ellipsis;
- vertical overflow inspectable;
- the existing shared overlay minimum touch target;
- keyboard-focus ownership false;
- click ownership false;
- long-click ownership false.

The focus/click fields are not decorative metadata. The owner must reapply them after movement-method installation because Android movement-method wiring can otherwise change those states.

`HeartbeatDetailSurfacePolicy.clampScrollY(...)` is the pure post-layout preservation rule:

- legal prior reading position survives;
- content shrink clamps to the new bottom;
- non-overflowing content returns to top;
- negative input fails closed to top;
- arithmetic is overflow-safe.

The Android owner must explicitly consume those semantics before `existing-owner wiring = YES` can be claimed. The corrected owner delta is preserved at `docs/try-forever/operator-overlay-heartbeat-detail-scroll-wiring.patch`; it adds a generation-bound one-shot pre-draw restore so stale callbacks cannot overwrite newer detail ownership and explicitly restores passive focus/click/long-click state after movement-method installation. A patch artifact is not owner implementation.

## Regression doctrine

Source fixtures should prove:

- long detail remains byte-for-byte equivalent at the Java String level after established surrounding trim;
- content description equals the full projected detail;
- the visible viewport stays bounded;
- overflow is marked scroll-inspectable rather than ellipsized away;
- the touch floor aliases the existing overlay touch contract;
- the policy declares `keyboardFocusable=false`, `clickable=false`, and `longClickable=false` while vertical touch inspection remains enabled;
- empty detail receives one deterministic fallback;
- interior Unicode/evidence content is not rewritten by layout policy;
- a legal background reading position survives;
- a position beyond a newly shorter layout clamps to the new bottom;
- non-overflowing and negative positions resolve to top;
- stale deferred restores are generation-invalidated by newer owner presentation.

Owner review must separately verify, on the real native `heartbeatDetail`, that movement-method installation is followed by the declared passive ownership state; explicit selection resets to top; background refresh preserves/clamps reading position; and the detail surface does not become a new direct-keyboard-focus witness for heartbeat viewport restoration. That native assertion is not satisfied merely by the pure policy fixture.

Regression source is not TESTED evidence until an authorized runner executes it successfully.

## Capability membrane

- detail policy source: **YES**
- passive focus/click ownership policy source: **YES**
- post-layout clamp policy source: **YES**
- hostile pure regression source: **YES**
- corrected existing-owner patch artifact: **YES / PROPOSED_NOT_APPLIED**
- real native focus-ownership fixture executed: **NO**
- existing `OperatorOverlayService` deep-detail wiring: **NO**
- tested: **NO**
- runtime scrolling / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## P0 / phone firewall

This skill owns no Phone Hands ticket, primary-phone execution, queue/relay probe, Home Center recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organ action, physical acceptance chain, or P0 coordination.
