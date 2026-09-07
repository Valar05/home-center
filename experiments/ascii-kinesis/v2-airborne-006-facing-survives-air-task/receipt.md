# ASCII Kinesis V2 — Airborne 006 — Facing Survives Air Task

Status: READY_TO_PERSIST
Lane: JUMP / AIRBORNE / LANDING / VERTICAL FORCE
Repo path: `experiments/ascii-kinesis/v2-airborne-006-facing-survives-air-task/`

## Minimal-maximal unit

**FACING SURVIVES AIR TASK** — facing is a continuity channel separate from root vertical phase and local aerial task. The independently authored ASCII rig preserves a right-facing cue while an aerial task coils, reaches, recoils, then lands through contact/compression/rebound/return.

## Source / rights

- The Spriters Resource asset 10039 — Sonic the Hedgehog — Sonic Battle — Game Boy Advance
- Source: https://www.spriters-resource.com/game_boy_advance/sonicbattle/asset/10039/
- Whole-sheet evidence mode: `VERIFIED_HISTORICAL_EVIDENCE_REUSE`
- Evidence origin: `experiments/ascii-kinesis/v2-airborne-002-precontact-landing-window/{motion.json,manifest.json}`
- Historical pass is evidence only; no prior deliverable, ASCII rig, timing sequence, or media is reused as this specimen.
- Copyright boundary: No source pixels, palette, contours, exact silhouettes, costume/facial detail, frame layout, tracing, redistribution, or close imitation enter this specimen. Drew work was not used. The ASCII rig is independently authored.

## Evidence split

OBSERVED is limited to facts already anchored to the verified complete-sheet inspection: distinct Jumping/Falling/Landing families; multiple airborne task/attack families; broad facing continuity while limbs change; grounded/consequence/recovery anchors; and absence of source-authentic exposure timing.

INFERRED: the new generic rig, facing-channel abstraction, root arc, contact/compression/rebound grammar, and all decisive cadence. UNKNOWN: exact source sequence ordering, source frame exposure/hit-stop/runtime transitions, and world-space physics.

## Per-key timing

- A006-K0 READY: FOURS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K1 CROUCH_LOAD: FOURS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K2 LAUNCH: ONES / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K3 RISE: TWOS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K4 APEX_READ: FOURS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K5 AIR_TASK_COIL: TWOS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K6 AIR_TASK_REACH: ONES / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K7 AIR_TASK_RECOIL: TWOS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K8 DESCENT_OPEN: TWOS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K9 PRECONTACT_OPEN: TWOS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K10 CONTACT: ONES / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K11 LAND_COMPRESSION: FOURS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K12 REBOUND: TWOS / INFERRED / STREET_FIGHTER/CAPCOM
- A006-K13 RETURN_STABLE: FOURS / INFERRED / STREET_FIGHTER/CAPCOM

User shorthand `1s/2s/4s` means ONES/TWOS/FOURS, never seconds. No decisive timing is claimed OBSERVED.

## Motion Dungeon / media

Method: `AUTHORED ASCII KEYS -> EXPLICIT HOLDS/TIMING -> DETERMINISTIC CONNECTIVE MOTION -> ASCII-ONLY FRAME RENDER -> MP4 -> SPA`
Media: `facing-survives-air-task.mp4` embedded in the tracked SPA; source pixels used = false.
Media SHA-256: `28ce2bdeb507a858a9da335f09b7158095a906d386b0e4fac4c3d8fce55dd12e`
Media bytes: `8170`
Video: 480x270 H.264 yuv420p, 24 fps, 92 frames.
ASCII sheet SHA-256: `c957b076cb4231618478f2ff8da3a2cba3b198bfe9fa5e8562de8cc06f9ed7b6`

## Contract / test boundary

SPA primary tabs are exactly `ASCII | JSON | VIDEO`; ASCII is literal `<pre>` text with whitespace preserved and ligatures disabled; JSON carries rig/keys/timing/provenance/rights/compatibility/manifest/media identity; VIDEO embeds the real MP4 generated from this abstract ASCII rig only.

Repository-wide test boundary: Standard Chat has authenticated GitHub read/write but no authorized remote repository execution shell in this run. tools/test_ascii_kinesis_swarm_contract_v2.py will be read for presence; repository-wide execution is not callable through the authorized connector surface. Local construction checks are not used as completion proof.

## Persistence fields

Ship commit: PENDING
Repository readback: PENDING
Issue #343 receipt: PENDING
Blocker: NONE at construction stage; persistence and readback still required.
Correction hooks: KEEP, REJECT, EXAGGERATE, COMPRESS, RETIME, CHANGE SOURCE, PROMOTE, SPAWN VARIANT, FIX BLOCKER, RERUN
