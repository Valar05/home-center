# Heartbeat Refresh Deduplication

## Purpose
Keep a fast polling loop from becoming a fast UI rebuild loop or a TalkBack chatter loop. UI work is earned by semantic presentation change, not by poll frequency, timestamps, or invisible evidence churn.

## Ownership boundary
This skill owns source planning plus composition into the existing Operator Overlay owner. It does not create or own a second Android service, renderer, state store, transport, queue, phone executor, P0 recovery action, deployment, delivery, or acceptance lane.

Compose existing organs in this order:

`OperatorState persisted identity -> HeartbeatPersistedEnvelopeProjection -> HeartbeatSceneGraph.Frame -> HeartbeatOverlayViewModel -> HeartbeatOverlayRefreshPlan -> existing OperatorOverlayService child views`

Do not bypass the parser/scene gate and do not create a neighboring overlay controller.

## Four identities, four jobs
Keep exact evidence identity separate from UI-work identity:

- **contact/checkpoint identity** includes the accepted visible pulse id and full last-good contact surface. It is evidence/idempotence truth.
- **presentation identity** excludes the otherwise invisible accepted pulse id but includes the presented/touchable node surface. Semantic ids are case-folded only in this UI-work identity.
- **structure identity** changes only when the ordered semantic light-id set changes. Stable structure means the existing native child objects can be updated in place.
- **announcement identity** changes only for transition semantics or a new interruption wound.

Case-only semantic-id drift may advance exact checkpoint evidence while presentation/structure/announcement remain stable when every presented semantic field is otherwise identical. It earns no native rebuild, automatic speech, or Christmas-light motion.

## Interrupted-refresh diagnostic custody
`Frame.refreshBoundary` is exact evidence and remains exact. Exact diagnostic evidence is not permission to spend unbounded work in human-facing projection or dedup hashing.

Current SOURCE_WIRED behavior:

- `Frame.interruptedRefreshDescription()` checks `HeartbeatPlainTextBudget.MAX_SOURCE_CODE_UNITS` before whole-boundary semantic scanning; admitted boundaries continue through the existing hard returned speech budget, while max+1 becomes one fixed source-work stop.
- `HeartbeatOverlayRefreshPlan` derives a bounded `identityBoundary` before render/announcement SHA-256 materialization. At/below the throat, the exact boundary still distinguishes UI wounds. Above the throat, non-authoritative UI identity collapses to a deterministic marker keyed by Java `String.length()`; the exact frame evidence remains separate and unchanged.
- last-good contact stays visible and all rejected-refresh transition motion remains clamped off.

Therefore `renderIdentity` and `announcementIdentity` are **not** whole-source hashes of arbitrary exact interruption prose anymore. Do not regress doctrine back to “exact interruption boundary is always hashed.”

Applied provenance: `patches/try-forever-heartbeat-refresh-boundary-source-work-throat.patch`; scene base `021f4e6f672002762848b46c6ef42eb4d1d3f0a4` -> commit `da807bd09b2797b48cd31bf563a155d1d15baf1b` -> blob `4012d09b10b72956a546276175f16504882148eb`; refresh-plan base `483257e1d1aca72610dc632a8343a96f0262e0d6` -> commit `e32217ed58d630126d1056a3a9466113a1089458` -> later owner blob `e75d4c01650f5afd9e09ceba3ebdceb1e5f8f5f6` after the independent direct-selection repair. Regression source is UNEXECUTED; TESTED remains NO.

## Stable selection, focus, and viewport contact
Retain selection by semantic light id, never by focus index. Reordering may move focus position without changing which light is selected. If the selected id disappears, clear selection rather than silently selecting another light.

Direct refresh-plan adapters are source boundaries too. `fromFrame(..., selectedControlId)` and `viewportAnchorId(selectedControlId, keyboardFocusedControlId, model)` now cross `HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS` before adapter `trim()` and downstream case-fold lookup. Safe `Model.controlById(...)` did not retroactively bound the adapter work that preceded it. This seam is **SOURCE_WIRED / APPLIED_SOURCE / regression source UNEXECUTED**.

Stable native object identity is not stable viewport contact. Existing-owner source wiring may preserve a semantic anchor and bounded viewport offset across in-place refresh/rebuild, but runtime keyboard-focus and TalkBack-focus behavior remain unproven until an authorized Android body observes them.

## Remaining direct previous-identity wound
The public decision helpers still accept arbitrary caller Strings for previous structure/render/announcement identities and currently call `clean(...)` before equality. Generated identities are tiny, but public direct callers do not inherit that fact automatically.

`patches/try-forever-heartbeat-refresh-plan-previous-identity-source-throat.patch` is an exact existing-owner proposal against blob `e75d4c01650f5afd9e09ceba3ebdceb1e5f8f5f6`. It reuses the broad direct-source ceiling before trim/equality. `tools/test_try_forever_heartbeat_refresh_plan_previous_identity_source_work.py` pins the desired order. This seam is **RED SOURCE / PROPOSED_NOT_APPLIED / UNEXECUTED / TESTED_NO**.

Do not green-paint this wound merely because normal service callers feed generated 64-hex identities.

## Cold-start, mute, visibility, and contact rules
An empty previous announcement identity means unknown history, not a proven transition. The first model may render, but automatic speech stays quiet until a prior semantic baseline exists.

Mute, whole-overlay visibility, and heartbeat-surface visibility are presentation gates, not semantic identities. Suppressed speech still advances remembered announcement identity so later unmute/restore/expand does not replay a stale transition.

Storage/parser/Base64 rejection inherits the existing scene preservation contract: show only last-good contact, expose the interruption wound separately, clamp motion, never surface discarded attempted candidates, and do not repeat identical wound work.

## Accessibility contract
A fast refresh loop must not reset accessibility contact every poll. Stable structure should keep native child identity; visible/touchable content refreshes are separate from structure replacement; semantic announcement identity is separate from rendering; and exact diagnostic evidence is separate from bounded human-facing speech/dedup work.

Heartbeat child controls remain independently focusable native controls. State must be communicated by token + word rather than color alone. Existing source-level minimum touch semantics remain authoritative; runtime TalkBack is not claimed.

## Regression source
At minimum cover:

- cold start: structure/content work, no automatic transition speech;
- exact retry: no structure/content/speech work;
- invisible new pulse id with identical presentation: checkpoint may change, UI identities stay stable;
- evidence-only refresh: stable structure, content refresh, no speech;
- state/consequence transition: content + announcement identity change;
- reorder/membership change: structure replacement required;
- case-only semantic-id drift: exact evidence may change without UI work;
- interrupted refresh: exact boundary preserved, last-good contact held, no motion;
- over-ceiling boundary speech stops before whole-source semantic scan;
- over-ceiling boundary UI identity stops before whole-source UTF-8/SHA work;
- two over-ceiling equal-length boundaries may share non-authoritative UI identity while exact evidence remains distinct;
- direct selected/focused ids cross the broad source-work throat before adapter trim;
- previous structure/render/announcement direct identities remain RED until their proposed pre-trim throat is applied;
- mute/hidden/collapsed suppression does not create stale replay.

Regression files are source only until an authorized runner executes them.

## Evidence membrane
Keep these states separate:

`requested -> implemented source -> regression source -> tested -> existing-owner source wired -> runtime UI observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

Current state: refresh-boundary speech/dedup source-work custody **SOURCE_WIRED / APPLIED_SOURCE**; direct refresh selection/focus adapter custody **SOURCE_WIRED / APPLIED_SOURCE**; previous refresh-identity direct source-work custody **NO / RED SOURCE / PROPOSED_NOT_APPLIED**; regression execution **NO**; TESTED/runtime/TalkBack/deployed/callable/executed/delivered/accepted **NO**.

## Done for one source pulse
Light this skill only when dedupe/selection/contact/accessibility semantics, source-work custody, existing-owner composition, or their regression doctrine materially changes. Another poll, unchanged failure, or invisible equivalent pulse alone is not work.
