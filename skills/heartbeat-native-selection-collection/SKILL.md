# Heartbeat Native Selection Collection

## Purpose
Keep persistent heartbeat-light selection semantically honest across DOM specimens and the existing native Operator Overlay owner.

A heartbeat light selects one item whose Why/Consequence/Evidence/Source appears in a shared detail surface. Activating the selected light does not switch selection off. This is a persistent one-of-many state machine, not a toggle.

## Core law
`PERSISTENT ONE-OF-MANY ≠ TOGGLE`.

Selection, keyboard focus, accessibility focus, activation, and detail presentation are separate state machines. Do not infer one from another.

### DOM / source specimens
Use radio-style semantics for a persistent mutually-exclusive light set:
- one `radiogroup` owner;
- each light exposes `role=radio` + `aria-checked`;
- exactly one selected light owns the tab stop when a selection exists;
- Arrow keys move and select deterministically; Home/End may select first/last;
- activating the already-selected light keeps it selected;
- the shared detail surface remains a separate persistent region;
- dynamic detail is inert text, not injected HTML.

This supersedes older heartbeat source-specimen wording that treated persistent light selection as `aria-pressed` toggle state. The reusable `persistent-selection-semantics` law is authoritative on this point.

### Native Android source contract
The existing `OperatorOverlayService` already carries a semantic selected id and calls `Button.setSelected(...)`. That is not the complete accessibility collection contract by itself.

`HeartbeatSelectionAccessibilityPolicy` defines source-only collection/item semantics from the already accepted `HeartbeatOverlayViewModel.Model`:
- one single-selection collection when controls exist;
- because the native control strip is a horizontal list, Android framework collection geometry is **rows = item count, columns = 1**;
- each item uses zero-based `rowIndex=index`, `columnIndex=0` for native collection geometry;
- a separate source-level one-based `positionInSet=index+1` remains useful for human/set-order semantics;
- semantic id remains the identity across reorder;
- stale selection does not invent a replacement selection;
- selection does not claim keyboard or accessibility focus ownership.

The Android framework documentation models a horizontal list as one column with as many rows as list items. Do not transpose this custom `HorizontalScrollView` + horizontal `LinearLayout` owner into one row/many columns merely because some higher-level collection widgets use a different convention. That geometry distinction is a review boundary, not a reason to cargo-cult a RecyclerView implementation into this owner.

### Owner lifecycle application law
Collection semantics belong to the **collection lifecycle**, not to each child-construction call.

For the native owner to count as `SOURCE_WIRED`:
- initial native selected state must be applied by the existing light owner;
- selected state must be refreshed when the persistent selected id changes;
- the collection/item policy must be projected inside one dedicated existing-owner helper;
- the helper must be applied **after the heartbeat row is constructed** so the collection and every current child can be described together;
- the helper must run again after persistent selection changes so `CollectionItemInfo.selected` cannot stay stale;
- an implementation that only calls collection wiring from `applyHeartbeatLight(...)` is **PARTIAL_UNSAFE** even if every marker is present, because it rewrites collection semantics as a per-child side effect and does not prove later selection refresh;
- comments, literals, wrong methods, policy existence, or patch artifacts do not count as owner wiring.

Stable-structure in-place content refresh is **not a third required owner proof**. The collection metadata derives from current child order/identity plus the persistent selected id; those are already governed by structure rebuild and selection-refresh owners. Reapplying the helper during an in-place content refresh is allowed as a defensive synchronization step, but a source probe must not falsely downgrade an otherwise complete owner merely because a consequence/evidence-only refresh did not rebuild identical collection metadata.

For the current minSdk 26 source contract, eventual owner implementation must use Android APIs available to that runtime. `AccessibilityNodeInfo.CollectionInfo.obtain(...)`, `CollectionItemInfo.obtain(...)`, and single-selection mode are API-21-compatible source shapes. Android now deprecates the pooling `obtain(...)` APIs in API 33 in favor of constructors added later; that deprecation is **not** permission to raise the runtime floor or add version-branch churn to a minSdk-26 owner. Prefer the oldest correct runtime-compatible shape until the build/runtime contract changes deliberately. Deprecation status does not prove runtime TalkBack behavior either.

## Broad-doctrine convergence
The stale broad heartbeat sentence permitting `aria-pressed` for this persistent one-of-many light set was removed through the audited Home Center GitHub lane at commit `01038f86ee131257b0eb68acf3e59e585d779891`; resulting `skills/heartbeat-skill-lights/SKILL.md` blob: `6287c7660a00a45b07bc00675af353f2a7ac6e0e`.

The exact correction provenance remains at `patches/try-forever-heartbeat-selection-doctrine-convergence.patch` with status **APPLIED_SOURCE**. The source regression at `tools/test_heartbeat_selection_doctrine_convergence.py` pins broad doctrine + specialized doctrine + current DOM specimen to the same radio-style contract. That regression is repository source only until an authorized execution lane runs it.

## Touch and motion
Keep the existing minimum touch target and visible-focus contracts. Selection semantics do not authorize new animation. Christmas-light motion remains governed by material heartbeat transition identity; selecting a light to inspect detail is not a new heartbeat transition.

## Contact preservation
An interrupted or rejected heartbeat keeps the last-good visible selection surface. Do not expose discarded attempted controls as current collection items. A stale selected id may yield zero selected items rather than inventing a new selected identity.

## Capability membrane
Keep these separate:
`requested → supporting source → owner source wired → regression executed → tested → runtime UI → runtime TalkBack → deployed → callable → executed → delivered → accepted`.

A Java policy, JUnit source, DOM specimen, owner probe, or patch artifact is not runtime TalkBack proof.

## Current PR #329 truth — 2026-08-21 22:02 CT
- persistent-selection reusable doctrine: **YES**;
- broad heartbeat persistent-selection doctrine: **CONVERGED / APPLIED_SOURCE**;
- doctrine convergence regression source: **YES / UNEXECUTED**;
- corrected radio-style heartbeat DOM specimen: **SOURCE YES**;
- `HeartbeatSelectionAccessibilityPolicy`: **SUPPORTING SOURCE YES**;
- Android framework horizontal geometry review: **ROWS=N / COLUMNS=1 RETAINED**;
- deterministic JUnit source: **YES / UNEXECUTED**;
- direct-owner source probe: **v2 / SOURCE YES / UNEXECUTED**;
- hostile owner fixture rejects per-light-only collection wiring: **YES / UNEXECUTED**;
- exact base-blob-locked native owner surgery: **YES / PROPOSED_NOT_APPLIED**;
- authenticated owner base blob for that surgery: `c5de1411a6b68087ae17aff83c032af754587150`;
- current native owner selected-state lifecycle: **YES / SOURCE**;
- native collection/item owner wiring: **NO / PARTIAL_UNSAFE**;
- TESTED / runtime UI / runtime TalkBack / deployed / phone delivered / accepted: **NO**.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. Repository/source work does not reopen the shared phone surface.

## Done for one pulse
Light this skill only when the persistent-selection contract, native collection semantics, owner evidence boundary, or source specimen materially changes. Once those source seams are stable, keep it dark until fresh evidence changes them.
