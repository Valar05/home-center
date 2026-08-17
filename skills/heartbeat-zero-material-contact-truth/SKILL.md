# Heartbeat Zero-Material Contact Truth

## Purpose
Keep **accepted heartbeat contact** distinct from **material-light count**. A complete accepted pulse may contain zero material lights. If the scene retains a non-empty `visiblePulseId`, the heartbeat has contact even when `frame.nodes` / native controls are empty.

This skill was harvested after source review found a contradiction: the persisted-poll doctrine correctly established `visiblePulseId` as contact identity while one later chrome bullet still called a non-interrupted zero-control model `HEARTBEAT • waiting`. A later owner review found a second seam: correct collapsed heartbeat text existed only inside the `details` subtree, which becomes `GONE` when the overlay collapses. Source truth therefore counts only when it reaches an accessibility-reachable surface that actually survives the collapsed composition.

## Canonical states
Use the accepted/preserved scene, never raw candidate count, as the authority:

- no accepted visible pulse + no interruption -> `HEARTBEAT • waiting`;
- accepted non-interrupted visible pulse + zero material controls -> `HEARTBEAT • 0 LIGHTS`;
- accepted non-interrupted visible pulse + material controls -> `HEARTBEAT • N LIGHTS`;
- interrupted refresh + accepted/preserved visible pulse + zero controls -> `HEARTBEAT • CONTACT HELD`;
- interrupted refresh + accepted/preserved visible pulse + controls -> count plus `CONTACT HELD`;
- interrupted refresh before any accepted visible pulse -> `HEARTBEAT • REFRESH BLOCKED`.

`waiting` therefore means **no accepted/preserved visible heartbeat contact**, not “the current material selection is empty.”

## Accessibility projection
Collapsed TalkBack must preserve the same distinction:

- accepted current zero-material frame -> `Heartbeat accepted with no material skill lights.`;
- interrupted frame preserving zero-material last-good contact -> state that the last complete heartbeat has no material lights, then append the bounded interruption description;
- no visible contact -> do not claim acceptance or held contact.

Do not make routine speech read the full pulse identity merely to prove contact; `visiblePulseId` is the internal source predicate. Exact pulse identity remains checkpoint/evidence truth and is already bounded when interruption speech needs to expose it.

A correct string assigned only to a descendant that is `GONE` in collapsed mode **does not satisfy collapsed accessibility**. At least one surviving, visible, accessibility-reachable existing-owner control must carry the bounded heartbeat truth while the details subtree is collapsed.

## Existing-owner composition
The existing source chain remains authoritative:

`HeartbeatSceneGraph.Frame -> HeartbeatFrameAccessibility + HeartbeatOverlayViewModel -> HeartbeatCollapsedOwnerAccessibility -> OperatorOverlayService.dragHandle`

`OperatorOverlayService` remains the sole Android owner. Expanded mode keeps the ordinary drag/expand action description because the heartbeat details are visible. Collapsed mode composes the accepted model onto the already-existing `dragHandle`, which survives while `details == GONE`. Presentation-state changes, heartbeat-model chrome changes, and recovery back to ordinary waiting must refresh that same surviving description.

Do not create a neighboring renderer, accessibility service, overlay controller, state store, poller, or recovery path.

## Motion and announcement discipline
Changing chrome truth is not permission to invent repeated motion or speech. Accepted zero-material contact is still an accepted semantic frame. The existing checkpoint/render/announcement identities decide whether UI work, one-shot motion, or automatic speech is warranted. Node count must not be used as a shortcut for contact or event identity.

A pure removal that transitions from one or more lights to zero may still legitimately earn the existing summary fallback motion once because the scene transition semantics changed. A stable zero-material accepted pulse does not earn repeated motion merely because the poll runs. Updating a collapsed control's `contentDescription` is accessibility state, not permission to call `announceForAccessibility(...)` on every poll.

## Regression source
At minimum pin:

- accepted complete zero-material pulse has non-empty `visiblePulseId`, zero nodes, and contact=true;
- its visible summary is `HEARTBEAT • 0 LIGHTS`, never waiting;
- its collapsed accessibility summary explicitly says the heartbeat was accepted with no material lights;
- the surviving collapsed-owner projection exposes that truth on the existing drag handle contract, not only on a `GONE` descendant;
- the same collapsed-owner surface distinguishes accepted-zero contact from ordinary waiting, `CONTACT HELD`, and `REFRESH BLOCKED`;
- expanded mode restores the ordinary overlay action description rather than duplicating heartbeat prose where the detail subtree is already visible;
- interrupted zero-material last-good contact reports `CONTACT HELD` and names the last-complete-heartbeat condition rather than current acceptance;
- a pre-contact storage/read wound remains `REFRESH BLOCKED` and cannot claim accepted zero-material contact;
- null scene remains unavailable.

Regression source is not TESTED until an authorized runner actually executes it.

## Evidence membrane
Keep these states separate:

`requested -> source repaired -> exact GitHub readback -> regression source -> tested -> existing-owner runtime observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

Remote GitHub source/readback can prove only the source-side states. Existing-owner source wiring is not Android/TalkBack runtime proof. Do not claim phone delivery from repository artifacts.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone execution, queue/relay probe, Home Center recovery mutation, Nightcore/Pocket TTS/Chromium/Context Organ action, physical acceptance, or P0 coordination. Those surfaces remain under their canonical owners.

## Done for one pulse
Light this skill only when the zero-material contact distinction, its surviving collapsed-owner source composition, its regression evidence, or runtime proof materially changes. Once source truth is stable, keep it dark rather than polishing it into another office carpet.
