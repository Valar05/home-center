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

- **structure identity** changes only when the ordered semantic light-id set changes. Stable structure means existing native child objects can be updated in place instead of destroyed/recreated, preserving keyboard/TalkBack focus opportunities.
- **render identity** changes when visible/touchable contact changes or when the exact interruption wound changes. Evidence/provenance/detail, label, state, consequence, and pulse-contact changes may refresh native content without automatically requiring child replacement.
- **announcement identity** changes only when transition semantics change or a new interruption wound appears. Evidence-only/provenance-only refreshes must not become unsolicited speech.

Do not use wall-clock timestamps as semantic identities. Do not rebuild, refresh, or announce merely because the service poll ran again.

### Current capability scar
`HeartbeatOverlayRefreshPlan` now exposes the structure/render split in durable source, but `OperatorOverlayService` still consumes the legacy `shouldRebuild(renderIdentity, plan)` compatibility path. Therefore **focus-stable in-place native updates are IMPLEMENTED AS SOURCE PLANNING ONLY, NOT EXISTING-OWNER SOURCE WIRED** until the service consumes `structureIdentity` and refreshes stable child objects in place.

## Cold-start, mute, and visibility rules
An empty previous announcement identity means **unknown history**, not a proven transition. The first model may render, but automatic speech must stay quiet until there is an established prior semantic baseline and a later announcement identity differs. Do not narrate stale persisted state as though the service just witnessed it happen.

Mute and overlay visibility are presentation gates, not semantic identities. When a transition arrives while muted or hidden, suppress speech **but still advance the remembered announcement identity**. Unmuting or restoring later must not replay the old transition as though it just happened.

Explicit touch detail must honor the same global heartbeat-speech mute gate. Muting may not silence automatic status while leaving touch detail unexpectedly vocal.

## Stable selection and focus preservation
Retain selection by semantic light `id`, never by focus index. Reordering the scene may move a control's focus position without changing which light the user selected. If the selected id disappears from the new accepted/preserved model, clear selection rather than silently selecting a different light.

Do not confuse stable selection with stable native focus. If the ordered semantic-id structure is unchanged, prefer updating existing child objects in place. Destroying and recreating the same buttons merely because evidence or state changed can discard keyboard or accessibility focus even though semantic selection survives.

## Contact preservation
Storage/parser/Base64 rejection inherits the existing scene preservation contract:

- show only last-good contact;
- expose the interruption wound separately;
- keep one-shot motion clamped off;
- never surface discarded attempted candidates as current controls;
- repeating the same wound must not earn repeated rebuild/refresh/announcement work.

A wound that preserves the same visible child identities should update interruption metadata without requiring child replacement.

## Accessibility contract
A fast refresh loop must not reset TalkBack focus every poll. Existing-owner source wiring already compares announcement identity before automatic status speech; source planning now also distinguishes child-structure replacement from content refresh.

Heartbeat child controls remain independently focusable native controls. A scrolling/container wrapper must not become a competing TalkBack destination. Each light honors the scene's minimum touch target on both width and height and exposes state by token + word rather than color alone.

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
- mute/hidden suppression without stale replay.

A regression file is source only until an authorized runner executes it.

## Evidence membrane
Keep these states separate:

`requested -> implemented source -> regression source -> tested -> existing-owner source wired -> runtime UI observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub source/readback proves only durable source presence and source wiring. A regression file is not a passing test until an authorized test body executes it. Existing-owner source wiring is not runtime rendering proof.

## Done for one source pulse
This skill may light only when dedupe/selection/contact/accessibility semantics, existing-owner source composition, or their regression source materially change. If the only event is another poll or another unchanged CI failure, keep it dark.
