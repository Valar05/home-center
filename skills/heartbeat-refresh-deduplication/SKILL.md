# Heartbeat Refresh Deduplication

## Purpose
Keep a fast polling loop from becoming a fast UI rebuild loop or a TalkBack chatter loop. The existing Operator Overlay may poll persisted heartbeat state frequently, but UI work is earned only by semantic change.

## Ownership boundary
This skill owns **pure source planning only**. It does not own an Android service, renderer, state store, transport, queue, phone executor, P0 recovery action, deployment, delivery, or acceptance.

Compose existing organs in this order:

`persisted byte/SHA identity -> HeartbeatPersistedEnvelopeProjection -> HeartbeatSceneGraph.Frame -> HeartbeatOverlayViewModel -> HeartbeatOverlayRefreshPlan`

Do not bypass the parser/scene gate and do not create a neighboring overlay controller.

## Two identities, two consequences
Use separate deterministic identities for separate work:

- **render identity** changes when visible/touchable contact changes or when the exact interruption wound changes. Provenance/evidence/detail changes therefore may rebuild the native detail surface.
- **announcement identity** changes only when transition semantics change or a new interruption wound appears. Evidence-only/provenance-only refreshes must not become unsolicited speech.

Do not use wall-clock timestamps as semantic identities. Do not rebuild or announce merely because the service poll ran again.

## Stable selection
Retain selection by semantic light `id`, never by focus index. Reordering the scene may move a control's focus position without changing which light the user selected. If the selected id disappears from the new accepted/preserved model, clear selection rather than silently selecting a different light.

## Contact preservation
Storage/parser rejection inherits the existing scene preservation contract:

- show only last-good contact;
- expose the interruption wound separately;
- keep one-shot motion clamped off;
- never surface discarded attempted candidates as current controls;
- repeating the same wound must not earn repeated rebuild/announcement work.

## Accessibility contract
A fast refresh loop must not reset TalkBack focus every poll. Native UI wiring should compare the previous render identity before rebuilding child controls and compare the previous announcement identity before any automatic status announcement.

Explicit user-requested detail remains separately available through the existing compact/detail descriptions. Never replace exact evidence with a speech projection.

## Evidence membrane
Keep these states separate:

`requested -> implemented source -> regression source -> tested -> existing overlay wired -> runtime rendered -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub source/readback proves only durable source presence. A regression file is not a passing test until an authorized test body executes it.

## Done for one source pulse
This skill may light only when dedupe/selection/contact semantics or their regression source materially change. If the only event is another poll or another unchanged CI failure, keep it dark.
