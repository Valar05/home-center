# HF Phone Debug Status - 2026-08-11

Status: diagnostic bridge branch prepared.

## What changed on this branch

- Adds strict `phone_diagnostics` backend validation, stream CAS, and immutable receipt verification.
- Adds `tools/android_phone_diagnostics.py`, a fixed-field read-only diagnostic engine with no subprocess, write, install, network, build, or UI capability.
- Wires the phone relay to bypass overlay only for the diagnostics plane while screen/UI actions still require the overlay gate.
- Registers `phone_diagnostics_readonly` in the phone capability list.
- Adds focused tests for the diagnostics engine, relay validation, CAS/replay protection, and phone relay contract.

## Local test evidence

- `python3 tools/android_phone_diagnostics_test.py`: 10 tests passed.
- `node tools/phone_diagnostics_relay_test.mjs`: PASS.
- `node tools/phone_hands_relay_contract_test.mjs`: PASS.

## Current blocker

The live `primary-phone` registration still lacks `phone_diagnostics_readonly`, so strict diagnostics cannot yet be queued against the phone. After this branch is deployed and the phone relay is restarted or re-registered, Adam can run the bounded HF phone diagnostic sequence.
