# Heartbeat Refresh Deduplication

## Purpose
Keep a fast polling loop from becoming a fast UI rebuild loop or a TalkBack chatter loop. The existing Operator Overlay may poll persisted heartbeat state frequently, but UI work is earned only by semantic change.

## Ownership boundary
This skill owns **source planning plus composition into the existing UI owner**. It does not create or own a second Android service, renderer, state store, transport, queue, phone executor, P0 recovery action, deployment, delivery, or acceptance lane.

Compose existing organs in this order:

`OperatorState persisted byte/SHA identity -> HeartbeatPersistedEnvelopeProjection -> HeartbeatSceneGraph.Frame -> HeartbeatOverlayViewModel -> HeartbeatOverlayRefreshPlan -> existing OperatorOverlayService child views`

Do not bypass the parser/scene gate and do not create a neighboring overlay controller.

## Three identities, three consequences
Use separate deterministic identities for separate work:

- **structure identity** changes only when the ordered semantic light-id set changes. Stable structure means existing native child objects are updated in place instead of destroyed/recreated, preserving keyboard/TalkBack focus opportunities.
- **render identity** changes when visible/touchable contact changes or when the exact interruption wound changes. Evidence/provenance/detail, label, state, consequence, and pulse-contact changes may refresh native content without automatically requiring child replacement.
- **announcement identity** changes only when transition semantics change or a new interruption wound appears. Evidence-only/provenance-only refreshes must not become unsolicited speech.

Do not use wall-clock timestamps as semantic identities. Do not rebuild, refresh, or announce merely because the service poll ran again.

### Current capability scar
`HeartbeatOverlayRefreshPlan` exposes the structure/render/speech split and the **existing `OperatorOverlayService` source consumes it**. The service keeps a remembered `heartbeatStructureIdentity`; a changed structure identity earns the existing full child rebuild path, while stable structure plus changed render identity updates the existing semantic-id `Button` objects in place. Before any in-place mutation, child count/order/tag identity is verified case-insensitively; drift fails safe to the existing rebuild path instead of updating the wrong semantic control.

The source now also contains deterministic **viewport-anchor geometry policy** in `HeartbeatOverlayRefreshPlan.anchoredScrollX(...)`. It exists because stable native object identity is not the same thing as stable visible contact: width-changing labels or siblings can move the same Button inside a horizontal scroll surface. The policy preserves a captured semantic anchor's viewport offset and clamps the resulting scroll position to the current range. **The existing service does not yet consume that policy.** Therefore viewport-contact source policy/regression is implemented, but Android viewport anchoring remains unwired and runtime-unproven.

This is **PARTIAL EXISTING-OWNER SOURCE WIRING**, not Android execution, runtime focus-preservation proof, TalkBack runtime proof, deployment, phone delivery, or acceptance.

## Cold-start, mute, and visibility rules
An empty previous announcement identity means **unknown history**, not a proven transition. The first model may render, but automatic speech must stay quiet until there is an established prior semantic baseline and a later announcement identity differs. Do not narrate stale persisted state as though the service just witnessed it happen.

Mute and overlay visibility are presentation gates, not semantic identities. When a transition arrives while muted or hidden, suppress speech **but still advance the remembered announcement identity**. Unmuting or restoring later must not replay the old transition as though it just happened.

Explicit touch detail must honor the same global heartbeat-speech mute gate. Muting may not silence automatic status while leaving touch detail unexpectedly vocal.

## Stable selection, focus, and viewport contact
Retain selection by semantic light `id`, never by focus index. Reordering the scene may move a control's focus position without changing which light the user selected. If the selected id disappears from the new accepted/preserved model, clear selection rather than silently selecting a different light.

Do not confuse stable selection with stable native focus. When the ordered semantic-id structure is unchanged, update the existing child objects in place. Refresh their visible label, touch minimums, selected state, content description, semantic tag, and click-detail closure without replacing the `Button` instance. This preserves the native object that may currently hold keyboard/accessibility focus.

Do not confuse stable native object identity with stable viewport contact either. A content-only refresh may change text width on an earlier sibling and slide the same selected/focused Button inside the horizontal content coordinate system. A future existing-owner wiring step may capture the semantic anchor id plus its viewport offset before mutation and, after layout, restore that offset using `HeartbeatOverlayRefreshPlan.anchoredScrollX(...)`. The policy must clamp to the current scroll range, must not use wall-clock identity, and must not claim TalkBack accessibility-focus ownership.

If live Android child count/order/tag identity contradicts the deterministic structure identity, do **not** guess. Fall back to the existing rebuild path and re-establish the canonical child structure.

## Contact preservation
Storage/parser/Base64 rejection inherits the existing scene preservation contract:

- show only last-good contact;
- expose the interruption wound separately;
- keep one-shot motion clamped off;
- never surface discarded attempted candidates as current controls;
- repeating the same wound must not earn repeated rebuild/refresh/announcement work.

A wound that preserves the same visible child identities updates interruption metadata without requiring child replacement.

## Accessibility contract
A fast refresh loop must not reset TalkBack focus every poll. Existing-owner source wiring compares structure identity before replacing children, render identity before refreshing mutable content, and announcement identity before automatic status speech.

Heartbeat child controls remain independently focusable native controls. A scrolling/container wrapper must not become a competing TalkBack destination. Each light honors the scene's minimum touch target on both width and height and exposes state by token + word rather than color alone.

Visible horizontal contact matters independently from object identity. Until the existing service captures/restores a semantic viewport anchor, do not report source policy as Android viewport-preservation capability.

Explicit user-requested detail remains separately available through the existing compact/detail descriptions. Never replace exact evidence with a speech projection.

## Regression source
At minimum cover:

- cold start: structure + content work, no automatic transition speech;
- exact retry: no structure/content/speech work;
- evidence-only refresh: stable structure, changed content, no speech;
- state/consequence change with same ids: stable structure, changed content, transition speech allowed;
- reorder or membership change: structure replacement required;
- id case normalization: no fake replacement;
- interrupted refresh with preserved last-good ids: stable structure, wound content changes once;
- mute/hidden suppression without stale replay;
- live child/tag mismatch: existing owner must fail safe to canonical rebuild instead of applying content to the wrong semantic child;
- viewport-anchor math: width growth/shrink keeps a captured anchor offset stable, clamps at both scroll edges, and cannot overflow into negative scroll.

A regression file is source only until an authorized runner executes it. Existing pure refresh-plan tests cover semantic work identities; viewport-anchor regression source covers pure geometry policy; the Android child-object reconciliation and viewport-anchor consumption paths remain runtime-unproven until authorized Android execution observes them.

## Evidence membrane
Keep these states separate:

`requested -> implemented source -> regression source -> tested -> existing-owner source wired -> viewport-anchor source wired -> runtime UI observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub source/readback proves durable source presence and existing-owner source wiring only. A regression file is not a passing test until an authorized test body executes it. Pure viewport-anchor policy is not existing-service viewport wiring. Existing-owner source wiring is not runtime rendering proof.

## Done for one source pulse
This skill may light only when dedupe/selection/contact/accessibility semantics, existing-owner source composition, viewport-contact policy, or their regression source materially change. If the only event is another poll or another unchanged CI failure, keep it dark.
