# state.md

Project: Home Center
State owner: Adam under Drew's authority
Updated: 2026-08-13 America/Chicago
Scope: current user-scoped autocorrect-noise feature transition. This file does not pretend to backfill every historical repository lane.

## Current commission

Build a durable Home Center feature that learns recurring autocorrect/noise corrections per authenticated user and separates gold from good. The feature must be general to Home Center users, not scoped to Drew and not globalized across users.

## Locked boundaries

- Owner: Home Center.
- Execution lane: Valar05/home-center, isolated feature branch, Home Center-audited GitHub mutations.
- Runtime surface: stable drive_operation registry.
- Persistence: Firestore scope derived from authenticated user identity.
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
- Implemented: pending branch commit.
- Tested: pending deterministic tests and CI.
- Deployed: no.
- Callable: no.
- Delivered: no.
- Accepted: no.

## Active gate

Implement the bounded branch, run deterministic checks, obtain Regnet QA PASS, then obtain Venice STOP_ALLOWED before stopping. Do not merge or deploy under this commission without a separately evidenced transition.
