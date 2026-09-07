# ASCII Kinesis V2 — Airborne 004 — Drag Capture Descent

Status: REPO_VERIFIED_WITH_GLOBAL_TEST_BOUNDARY (pending repository readback at construction time)

Source: The Spriters Resource — Green Army Man — Toy Story — Sega Genesis — asset 500827
Source page: https://www.spriters-resource.com/sega_genesis/toystory/asset/500827/
Reported source: PNG, 576×720, 44.01 KB, uploader Chipper_52; source page exposes Fall, Jump, Parachute, Soldier descends by parachute, climb, hand-up, and walk animation families.

Rights boundary: copyright-restricted commercial-game sprite art was inspected only as whole-sheet evidence. No source pixels, palette, exact silhouette, sheet layout, traced contour, redistribution, or close imitation is in this specimen. Drew work was not used.

Whole-sheet evidence split:
- OBSERVED: complete sheet visually inspected in Standard Chat; grounded/non-airborne soldier states coexist with compact/extended airborne silhouettes and long deployed-parachute bands; source page independently labels Fall / Jump / Parachute / Soldier descends by parachute; facing/read direction remains broadly coherent across long airborne bands; static sheet does not establish source-authentic duration or world-space root trajectory.
- INFERRED: one generic rise/apex/descent arc; drag-surface deployment/capture as a local airborne task change without support or relaunch; generic landing contact/compression/rebound/return; all decisive timing.
- UNKNOWN: exact source chronology, world-space root positions, drag magnitude, source-authentic exposure/hit-stop/landing timing.

Minimal-maximal principle: **DRAG CAPTURE CHANGES DESCENT READABILITY WITHOUT RESETTING THE AIRBORNE ARC.** The authored drag surface can enter DEPLOYING/COUPLED states while support remains NONE and the root continues the same descent. Motion Dungeon connectors hard-cut any support/contact/drag-state change so interpolation cannot invent the causal transition.

Decisive timing — all INFERRED / STREET_FIGHTER-CAPCOM:
- A004-K0 READY — FOURS
- A004-K1 LOAD — FOURS
- A004-K2 LAUNCH — ONES
- A004-K3 RISE — TWOS
- A004-K4 APEX_READ — FOURS
- A004-K5 FALL_OPEN — TWOS
- A004-K6 DRAG_DEPLOY — ONES
- A004-K7 DRAG_CAPTURE — FOURS
- A004-K8 CONTROL_DESCENT — TWOS
- A004-K9 PRECONTACT_OPEN — TWOS
- A004-K10 CONTACT — ONES
- A004-K11 LAND_COMPRESSION — FOURS
- A004-K12 REBOUND — TWOS
- A004-K13 RETURN_STABLE — FOURS

`1s/2s/4s` means ONES/TWOS/FOURS, never seconds. No source-authentic duration is claimed.

Motion Dungeon: authored ASCII keys -> explicit holds/timing -> semantics-preserving midpoint connectors only while support/contact/drag state are unchanged -> literal ASCII-only frame rendering -> H.264 MP4 -> self-contained three-tab SPA.

Compiled embedded MP4: 13009 bytes, H.264 yuv420p 480×270, 24 fps, 90 frames, 3.75 s, SHA-256 `081250e1aabac7abccda1d7fa63b0c36264d345783f88ff31c06877270282979`.
ASCII authority SHA-256: `6c0fad394953a4f1cee1bc96385c95d2604134215576e3cf64f50b720d0f33d0`.
Repository path: `experiments/ascii-kinesis/v2-airborne-004-drag-capture-descent/`
Ship commit: PENDING

Test boundary: `tools/test_ascii_kinesis_swarm_contract_v2.py` exists and was read. This Standard Chat runtime has no repository execution shell; a local GitHub clone attempt failed at DNS resolution. Current exact GitHub readback shows the deterministic global suite's pre-existing first blocker remains `v2-defense-001-guard-support-fork: expected exactly one tracked *.motion.html SPA`. This new specimen was checked against the same structural predicates and its MP4 decoded successfully with ffprobe.

Correction hooks: KEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN
