# Mute Capability Eviction — P0 Regression Lock

Status: RED / PHYSICAL DELIVERY REQUIRED

## Evidence split

Current `fortress/night-core-beard` source still constructs `muteButton = button("Mute speech")`, adds it to `actionRow`, and toggles `OperatorState.setMuted(...)`.

Drew's physical overlay screenshot does **not** show the mute control.

Therefore this is not a missing-source-feature problem. It is a **source → build/install/presentation capability eviction** until proven otherwise.

## Required repair

1. Preserve the existing mute implementation; do not invent a replacement control plane.
2. Determine why the physical installed overlay does not expose the source control (stale build/install, collapsed/presentation regression, branch drift, or another evidenced cause).
3. Build/install through the existing authorized phone lane.
4. Prove on the physical phone that Mute is visible/reachable in normal overlay use.
5. Tap Mute and prove `muted=true` through overlay/state receipt.
6. Tap Unmute and prove `muted=false`.
7. Mute must remain immediately reachable when automatic conversational speech is later enabled; user interruption outranks synthesis/playback/queue continuation.

## Non-eviction law

Once a user-facing safety/accessibility control is physically accepted, subsequent overlay evolution may move or improve it but may not make it unreachable without explicit owner approval and a proven replacement.

## Truth rule

Source presence earns zero physical-delivery credit. The screenshot outranks the source when the question is what Drew can actually touch.
