# Heartbeat Refresh Deduplication

## Purpose
Keep a fast polling loop from becoming a fast UI rebuild loop or a TalkBack chatter loop. The existing Operator Overlay may poll persisted heartbeat state frequently, but UI work is earned only by semantic presentation change.

## Ownership boundary
This skill owns **source planning plus composition into the existing UI owner**. It does not create or own a second Android service, renderer, state store, transport, queue, phone executor, P0 recovery action, deployment, delivery, or acceptance lane.

Compose existing organs in this order:

`OperatorState persisted byte/SHA identity -> HeartbeatPersistedEnvelopeProjection -> HeartbeatSceneGraph.Frame -> HeartbeatOverlayViewModel -> HeartbeatOverlayRefreshPlan -> existing OperatorOverlayService child views`

Do not bypass the parser/scene gate and do not create a neighboring overlay controller.

## Four identities, four jobs
Keep exact evidence identity separate from UI work identity:

- **exact contact/checkpoint identity** (`HeartbeatFrameCheckpoint.contactSha256`) includes the accepted visible pulse id plus the full last-good contact surface. It exists for evidence/idempotence truth; a new pulse id is allowed to be a new exact checkpoint even when nothing visible changed.
- **presentation identity** (`HeartbeatFrameCheckpoint.presentationSha256`) excludes the otherwise invisible accepted pulse id but includes ordered controls, labels, provenance/evidence detail, state, consequence, focus order, and touch targets. This is the semantic surface used to decide whether native content actually needs refreshing.
- **structure identity** changes only when the ordered semantic light-id set changes. Stable structure means existing native child objects are updated in place instead of destroyed/recreated, preserving keyboard/TalkBack focus opportunities.
- **announcement identity** changes only when transition semantics change or a new interruption wound appears. Evidence-only/provenance-only refreshes and pulse-id-only retries must not become unsolicited speech.

`HeartbeatOverlayRefreshPlan.renderIdentity` is derived from **presentation identity + interruption state + exact interruption boundary**, not from exact pulse/checkpoint identity. Therefore a producer may advance `pulseId` with an identical presented/touchable surface without earning native content churn. If a later refresh is interrupted, the interruption wound still changes render identity and the scene can speak the exact current visible pulse id through its bounded interrupted-refresh projection.

Do not use wall-clock timestamps as semantic identities. Do not rebuild, refresh, or announce merely because the service poll ran again or because an otherwise invisible pulse id advanced.

### Current capability scar
`HeartbeatOverlayRefreshPlan` exposes the structure/presentation-render/speech split and the **existing `OperatorOverlayService` source consumes it**. The service keeps remembered structure/render/announcement identities; a changed structure identity earns the existing full child rebuild path, while stable structure plus changed render identity updates the existing semantic-id `Button` objects in place. Before any in-place mutation, child count/order/tag identity is verified case-insensitively; drift fails safe to the existing rebuild path instead of updating the wrong semantic control.

The existing service also consumes deterministic semantic viewport-restore policy for **stable in-place refresh, structural rebuild, and live-structure-drift fallback rebuild**. It captures a visible semantic owner before mutation, carries a generation-bound restore ticket through a one-shot pre-draw callback, and revalidates current interaction ownership plus the actual mutation class before moving the viewport. Direct keyboard focus, semantic selection, visible viewport contact, and TalkBack accessibility focus remain separate claims. This is existing-owner **source wiring**, not Android viewport/keyboard-focus/TalkBack runtime proof.

The automatic-speech path now also distinguishes **whole-overlay visibility** from **heartbeat-surface visibility** in the existing owner. `OperatorOverlayService` derives `overlayVisible` from the persisted hidden state plus root visibility, derives `heartbeatSurfaceVisible` from the existing `details` subtree visibility, and passes both into the five-argument `shouldAnnounce(...)` gate. Because `applyPresentationState()` makes `details` `GONE` when collapsed, a visible root no longer authorizes heartbeat speech from behind the collapsed wall at the source level.

This is **EXISTING-OWNER SOURCE WIRING including the heartbeat-surface speech gate**, not Android execution, runtime focus-preservation proof, TalkBack runtime proof, deployment, phone delivery, or acceptance.

## Cold-start, mute, and visibility rules
An empty previous announcement identity means **unknown history**, not a proven transition. The first model may render, but automatic speech must stay quiet until there is an established prior semantic baseline and a later announcement identity differs. Do not narrate stale persisted state as though the service just witnessed it happen.

Mute, whole-overlay visibility, and heartbeat-surface visibility are presentation gates, not semantic identities. A root overlay can remain visible while the heartbeat/details subtree is deliberately collapsed/GONE. In that state automatic heartbeat speech must remain silent. When a transition arrives while muted, hidden, or collapsed, suppress speech **but still advance the remembered announcement identity**. Unmuting, restoring, or expanding later must not replay the old transition as though it just happened.

Explicit touch detail must honor the same global heartbeat-speech mute gate. Muting may not silence automatic status while leaving touch detail unexpectedly vocal.

## Stable selection, focus, and viewport contact
Retain selection by semantic light `id`, never by focus index. Reordering the scene may move a control's focus position without changing which light the user selected. If the selected id disappears from the new accepted/preserved model, clear selection rather than silently selecting a different light.

Do not confuse stable selection with stable native focus. When the ordered semantic-id structure is unchanged, update the existing child objects in place. Refresh their visible label, touch minimums, selected state, content description, semantic tag, and click-detail closure without replacing the `Button` instance. This preserves the native object that may currently hold keyboard/accessibility focus.

Do not confuse stable native object identity with stable viewport contact either. A content-only refresh may change text width on an earlier sibling and slide the same selected/focused Button inside the horizontal content coordinate system. Existing-owner source wiring captures a semantic anchor plus viewport offset before mutation and restores that offset after layout with bounded restore policy. Structural rebuild and structure-drift fallback now use the same existing-owner generation-bound semantic ticket path. The policy clamps to the current scroll range, does not use wall-clock identity, and does not claim TalkBack accessibility-focus ownership or runtime focus preservation.

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

A pulse-id-only accepted refresh with exactly the same presentation must earn **none** of those UI/speech consequences. Exact checkpoint identity may still advance independently.

Heartbeat child controls remain independently focusable native controls. A scrolling/container wrapper must not become a competing TalkBack destination. Each light honors the scene's minimum touch target on both width and height and exposes state by token + word rather than color alone.

Visible horizontal contact matters independently from object identity. Existing source wiring attempts viewport restoration through stable refresh, rebuild, and drift fallback; runtime viewport/keyboard-focus/TalkBack behavior remains unproven until an authorized Android body observes it.

A visible overlay root is not sufficient evidence that heartbeat content is presented. Automatic heartbeat speech requires the heartbeat surface itself to be presented; collapsed/GONE heartbeat content is silent while semantic announcement history continues to advance. Explicit user-requested detail remains separately available through the existing compact/detail descriptions when the surface is present. Never replace exact evidence with a speech projection.

## Regression source
At minimum cover:

- cold start: structure + content work, no automatic transition speech;
- exact retry: no structure/content/speech work;
- **new pulse id + byte-for-byte-equivalent presented surface: exact checkpoint changes, presentation/render/announcement stay stable, no UI/speech work**;
- evidence-only refresh: stable structure, changed presentation/content, no speech;
- state/consequence change with same ids: stable structure, changed content, transition speech allowed;
- reorder or membership change: structure replacement required;
- id case normalization: no fake replacement;
- interrupted refresh with preserved last-good ids: stable structure, wound content changes once;
- mute/hidden suppression without stale replay;
- **root visible + heartbeat surface collapsed/GONE: automatic speech suppressed while announcement history advances; expanding later must not replay that transition**;
- **the four-argument compatibility speech gate cannot represent collapsed-subtree truth and must not be substituted for existing-owner five-argument wiring**;
- live child/tag mismatch: existing owner must fail safe to canonical rebuild instead of applying content to the wrong semantic child;
- viewport-anchor math: width growth/shrink keeps a captured anchor offset stable, clamps at both scroll edges, and cannot overflow into negative scroll.

A regression file is source only until an authorized runner executes it. Existing pure refresh-plan/checkpoint tests cover semantic work identities; `HeartbeatInvisiblePulseIdDedupTest` covers the exact-checkpoint/presentation split; `HeartbeatCollapsedPresentationSpeechTest` covers whole-overlay-vs-heartbeat-surface speech policy plus the compatibility-gate gap. Existing `OperatorOverlayService` source now consumes the five-argument collapsed-surface gate; Android child reconciliation, viewport behavior, and TalkBack speech behavior remain runtime-unproven until authorized evidence advances them.

## Evidence membrane
Keep these states separate:

`requested -> implemented source -> regression source -> tested -> existing-owner source wired -> runtime UI observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub source/readback proves durable source presence and existing-owner source wiring only. A regression file is not a passing test until an authorized test body executes it. Exact checkpoint identity is not automatically presentation work. Existing-owner source wiring is not runtime rendering proof. The five-argument speech gate is now consumed by `OperatorOverlayService` source, but that still does not prove Android execution or TalkBack behavior.

## Done for one source pulse
This skill may light only when dedupe/selection/contact/accessibility semantics, existing-owner source composition, viewport-contact policy, heartbeat-surface presentation policy, or their regression source materially change. If the only event is another poll, another invisible pulse id, or another unchanged CI failure, keep it dark.
