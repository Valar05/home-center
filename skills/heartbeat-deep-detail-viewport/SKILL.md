# Heartbeat Deep Detail Viewport

## Purpose

Keep explicit heartbeat Why / Consequence / Evidence / Source detail fully inspectable without letting long evidence consume the whole Operator Overlay or silently acquire navigation ownership.

## Trigger

Use when the existing heartbeat detail surface already owns the correct full projected detail but its visible native presentation can hide later content behind destructive ellipsis, layout line caps, or another non-inspectable viewport bound.

## Law

1. The existing `OperatorOverlayService` and its existing `heartbeatDetail` surface remain the sole Android owner.
2. `HeartbeatEvidenceDetailProjection` remains the explicit typed-detail formatter. Do not invent another evidence formatter to solve layout.
3. Spatial bounds and semantic/layout bounds are different contracts. Keep the visible detail well bounded, but preserve the full already-bounded projected detail in the TextView layout behind vertical touch inspection.
4. Do not use `END` ellipsis when it makes omitted Evidence/Source text unreachable from the sighted/touch surface.
5. Do not use `TextView.setMaxLines(...)` as the five-line viewport. Android feeds the line-mode maximum into `StaticLayout.Builder.setMaxLines(...)`, so it can amputate later detail from the layout itself. Use a pixel-height cap derived from five line heights plus vertical padding instead.
6. Reuse `OverlayUiPolicy.MIN_TOUCH_TARGET_DP` as the detail touch floor; do not grow a second 48dp literal that can drift.
7. TalkBack content remains the same full explicit detail. Automatic/collapsed speech stays separate and must not inherit the deep-detail payload.
8. The detail well is a **passive touch-scroll surface**, not a keyboard-navigation owner and not a click/long-click action. Installing or replacing an Android movement method can mutate `TextView` focus/click defaults; therefore the native owner must explicitly restore policy-owned `focusable`, `clickable`, and `longClickable` state **after** `setMovementMethod(...)`.
9. Passive detail scrolling must not become evidence for `root.findFocus()` heartbeat viewport ownership. Selection, heartbeat-button keyboard focus, visible viewport contact, and TalkBack accessibility focus remain separate contracts.
10. Selecting a new light resets the detail well to the top and may announce through the existing mute-aware owner path.
11. A background model/evidence refresh preserves the current reading position only while that position still exists in the refreshed layout. After layout, clamp the old `scrollY` to the new legal range; content shrink must never strand the reader beyond the new bottom.
12. Any deferred background scroll restore is owned by the detail presentation that scheduled it. A newer detail presentation invalidates the stale restore before it can yank a newer explicit selection or refresh.
13. Source wiring, successful tests, runtime scrolling, runtime TalkBack behavior, deployment, phone delivery, and acceptance are separate capability states.
14. Do not create a neighboring detail controller, renderer, state store, overlay, phone path, or P0 owner.

## Source organ

`HeartbeatDetailSurfacePolicy.fromDetail(...)` projects the existing explicit detail into these source semantics:

- full text retained;
- full content description retained;
- five-line **spatial target**, not a line-count truncation command;
- no destructive end ellipsis;
- vertical overflow inspectable;
- the existing shared overlay minimum touch target;
- keyboard-focus ownership false;
- click ownership false;
- long-click ownership false.

`HeartbeatDetailSurfacePolicy.maxViewportHeightPx(...)` converts the five-line spatial target into a pixel-height cap using the current native line height plus total vertical padding. It uses long arithmetic and saturates at `Integer.MAX_VALUE`; negative hostile dimensions fail closed to zero. The existing owner is expected to use that result with `TextView.setMaxHeight(...)`, not `setMaxLines(...)`.

`HeartbeatDetailSurfacePolicy.clampScrollY(...)` is the pure post-layout preservation rule:

- legal prior reading position survives;
- content shrink clamps to the new bottom;
- non-overflowing content returns to top;
- negative input fails closed to top;
- arithmetic is overflow-safe.

The focus/click fields are not decorative metadata. The owner must reapply them after movement-method installation because Android movement-method wiring can otherwise change those states.

The Android owner must explicitly consume all of those semantics before `existing-owner wiring = YES` can be claimed. The corrected owner delta is preserved at `docs/try-forever/operator-overlay-heartbeat-detail-scroll-wiring.patch`; it now uses a pixel-height viewport so the full TextView layout survives, adds a generation-bound one-shot pre-draw restore so stale callbacks cannot overwrite newer detail ownership, and restores passive focus/click/long-click state after movement-method installation. A patch artifact is not owner implementation.

## Android platform evidence

The implementation order and viewport distinction are grounded in Android framework behavior rather than guessed from the patch:

- AOSP `TextView.setMovementMethod(...)` calls `fixFocusableAndClickableSettings()` and explicitly warns callers that a `TextView` with a movement method that should not be focusable must call `setFocusable(...)` again after installing the movement method. Current framework source also sets focusable, clickable, and long-clickable when a movement method is present. Source: `https://android.googlesource.com/platform/frameworks/base/+/main/core/java/android/widget/TextView.java`.
- `TextView.onTouchEvent(...)` delegates touch handling to the installed movement method when the view is enabled and has spannable laid-out text; that delegation is not conditioned on `isClickable()`. Source: the same AOSP `TextView.java`.
- `ScrollingMovementMethod.onTouchEvent(...)` delegates to the framework scrolling touch helper. Source: `https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/text/method/ScrollingMovementMethod.java`; API reference: `https://developer.android.com/reference/android/text/method/ScrollingMovementMethod`.
- AOSP `TextView.setMaxLines(...)` places the view in line-count maximum mode, and `makeNewLayout(...)` passes that maximum into `StaticLayout.Builder.setMaxLines(...)`. By contrast, pixel-height maximum mode leaves the layout line budget at `Integer.MAX_VALUE` while measured height is capped by the pixel maximum. Source: the same current AOSP `TextView.java`.

Therefore the corrected patch order—full layout + pixel-height viewport + scrolling movement method + reasserted passive focus/click/long-click ownership—is platform-grounded source behavior, not a decorative preference. This evidence still does **not** prove runtime touch scrolling, runtime keyboard focus, or TalkBack behavior on the target Android overlay; those remain separate native/runtime evidence gates.

## Regression doctrine

Source fixtures should prove:

- long detail remains byte-for-byte equivalent at the Java String level after established surrounding trim;
- content description equals the full projected detail;
- the visible viewport stays spatially bounded without setting a TextView line-count maximum;
- five-line spatial intent converts deterministically to line-height × five + vertical padding;
- viewport-height arithmetic fails closed for negative values and saturates safely on overflow;
- overflow is marked scroll-inspectable rather than ellipsized away;
- the touch floor aliases the existing overlay touch contract;
- the policy declares `keyboardFocusable=false`, `clickable=false`, and `longClickable=false` while vertical touch inspection remains enabled;
- empty detail receives one deterministic fallback;
- interior Unicode/evidence content is not rewritten by layout policy;
- a legal background reading position survives;
- a position beyond a newly shorter layout clamps to the new bottom;
- non-overflowing and negative positions resolve to top;
- stale deferred restores are generation-invalidated by newer owner presentation.

Owner review must separately verify, on the real native `heartbeatDetail`, that the TextView keeps its full layout while its measured viewport is height-capped; movement-method installation is followed by the declared passive ownership state; explicit selection resets to top; background refresh preserves/clamps reading position; and the detail surface does not become a new direct-keyboard-focus witness for heartbeat viewport restoration. The AOSP source evidence above strengthens the contract but does not satisfy that native assertion.

Regression source is not TESTED evidence until an authorized runner executes it successfully.

## Capability membrane

- detail policy source: **YES**
- pixel-height full-layout viewport policy source: **YES**
- passive focus/click ownership policy source: **YES**
- Android framework source evidence for max-lines and movement-method behavior: **YES / SOURCE EVIDENCE**
- post-layout clamp policy source: **YES**
- hostile pure regression source: **YES**
- corrected existing-owner patch artifact: **YES / PROPOSED_NOT_APPLIED**
- real native full-layout/focus fixture executed: **NO**
- existing `OperatorOverlayService` deep-detail wiring: **NO**
- tested: **NO**
- runtime scrolling / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## P0 / phone firewall

This skill owns no Phone Hands ticket, primary-phone execution, queue/relay probe, Home Center recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organ action, physical acceptance chain, or P0 coordination.