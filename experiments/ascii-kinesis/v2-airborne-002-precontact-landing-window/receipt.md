# ASCII Kinesis V2 — Airborne 002 — Precontact Landing Window

Status: RENDERED_PHONE_CANONICAL / PENDING_REPOSITORY_SPA_PERSISTENCE

Source: The Spriters Resource — Sonic the Hedgehog — Sonic Battle — Game Boy Advance — asset 10039
Source page: https://www.spriters-resource.com/game_boy_advance/sonicbattle/asset/10039/
Whole-sheet visual evidence: https://www.spriters-resource.com/media/assets/10/10039.png?updated=1755472454
Reported source: PNG, 1150×2660, 268.03 KB, uploader QuadFactor, Animations (0).

Rights boundary: copyright-restricted commercial-game sprite art was inspected only as evidence. No source pixels, palette, exact silhouette, sheet layout, traced contour, redistribution, or close imitation is in this specimen. Drew work was not used.

Observed: the complete sheet visibly separates Jumping / Falling / Landing families; it also contains named airborne attack/power/trap families and grounded/consequence/recovery anchors. Source-authentic timing is unavailable.

Minimal-maximal principle: LANDING BEGINS BEFORE CONTACT. PRECONTACT_OPEN keeps support NONE while the limbs target the base; CONTACT authors ground reacquisition; LAND_COMPRESSION authors the force consequence afterward.

Decisive timing (all INFERRED / STREET_FIGHTER-CAPCOM):
- A002-K0 LOAD — FOURS
- A002-K1 LAUNCH — ONES
- A002-K2 RISE — TWOS
- A002-K3 APEX_READ — FOURS
- A002-K4 AIR_TASK_ORIENT — TWOS
- A002-K5 FALL — TWOS
- A002-K6 PRECONTACT_OPEN — TWOS
- A002-K7 CONTACT — ONES
- A002-K8 LAND_COMPRESSION — FOURS
- A002-K9 REBOUND — TWOS
- A002-K10 RETURN_STABLE — FOURS

`1s/2s/4s` means ONES/TWOS/FOURS, never seconds. No source-authentic duration is claimed.

Motion Dungeon: authored ASCII keys -> explicit holds/timing -> semantics-preserving deterministic midpoint connectors only when support/contact are unchanged -> ASCII-only frame rendering -> H.264 MP4 -> self-contained three-tab SPA.

Canonical Standard-Chat phone compile: embedded MP4 (builder output name `precontact-landing-window.mp4`) — 51386 bytes — SHA-256 `b59b6af02263ab1341e93ac0146d1f7b8b8e4000068ecb9ecdba02d56d0d9436` — 72 frames @ 24 fps.
ASCII authority SHA-256: `c548bc67e92053438ac781cbb8e6bfb6ae1722c347226c8c5b5183d4ba6794c7`.
Repository path: `experiments/ascii-kinesis/v2-airborne-002-precontact-landing-window/`
Ship commit: PENDING_FIRST_PERSISTENCE

Correction hooks: KEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN

Packaging note: the MP4 is authoritative inside the tracked self-contained SPA; `build.py` deterministically reconstructs the standalone MP4 from `motion.json`. No source pixels enter either render.
