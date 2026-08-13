# state.md

Project: Home Center
State owner: Adam under Drew's authority
Updated: 2026-08-13 America/Chicago
Scope: current authenticated-user-scoped autocorrect-noise feature transition. This file does not pretend to backfill every historical repository lane.

## Current commission

Build a durable Home Center feature that learns recurring autocorrect/noise corrections per authenticated user and separates gold from good. The feature is general to Home Center users, not scoped to Drew and not globalized across users.

## Locked boundaries

- Owner: Home Center.
- Execution lane: Valar05/home-center, isolated feature branch, Home Center-audited GitHub mutations.
- Runtime surface: stable drive_operation registry.
- Persistence: Firestore scope derived only from authenticated Home Center user identity.
- Exclusions: global shared dialect; caller-supplied user scope; raw-message retention; silent good-tier rewrites; unprotected mutation of commands, filenames, identifiers, URLs, paths, handles, or protected vocabulary.
- Evidence: deterministic tests, actual diff review, Regnet QA, Venice completion review, PR checks, and later deployed MCP readback.
- Delivery: reviewed GitHub PR. Deployment and callable acceptance remain separate transitions.

## Durable plan gate

PLAN_ALLOWED receipt: https://github.com/Valar05/home-center/issues/277

Selected Jars:

- Charles Darwin × Charles Xavier — Living Sanctuary.
- Aegis × Dyonisis — Boundary or Permission?

## Capability state

- Requested: yes.
- Implemented: yes, on draft PR #278.
- Tested: yes for deterministic module behavior and JavaScript syntax at source commit `336a751a700d393fec7f8109b19188df0443b72e`.
- Deployed: no.
- Callable: no.
- Delivered: durable draft PR checkpoint only; release delivery remains no.
- Accepted: no.

## Test evidence

Computer Hands ticket `hands-autocorrect-pr278-fresh-tests-336a751-v2` verified the exact source commit, ran `node --test autocorrect_noise.test.js`, and ran `node --check` against both `autocorrect_noise.js` and `home_center_mcp.js`.

Result: 8 tests passed, 0 failed; both syntax checks exited successfully.

GitHub Actions did not execute repository code. Workflow run `31716947595` / check run `94503949281` was stopped before runner allocation because an Actions budget is preventing further use.

## Active gate

Obtain Regnet QA PASS, then obtain Venice STOP_ALLOWED before stopping. Do not merge or deploy under this commission without a separately evidenced transition.
