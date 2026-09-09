# Chekhov Kinesis Engine

Status: active
Scope: Chekhov Arsenal intake, automated conversation mining, Story Simulator handoffs, embodied mechanics
Authority: Drew correction 2026-09-08
Executable: `python tools/chekhov_kinesis_engine.py`

## Purpose

Turn aggressively collected Chekhov candidates into a deterministic, provenance-preserving kinesis graph without converting a high-recall miner into a high-confidence physics oracle.

## Core law

**Over-collect the Arsenal. Under-invent the mechanics.**

A candidate enters when violence is used, threatened, afforded, intended, imagined, opinionated, coercive, defensive, refused, or explicitly asserted by an upstream miner.

A kinetic primitive enters only when a structured tag or deterministic lexical witness supports it.

Thus a coffee pot with homicidal opinions belongs in the Arsenal even when every mechanical channel is still `unknown`.

## Stable transform

The engine is content addressed.

Input:

- a JSON array of candidate objects; or
- `{items:[...]}` / `{records:[...]}` with optional Story Simulator `projectId`, `frameId`, `frameVersion`, or `sourceHash`.

Output schema: `home-center.chekhov-kinesis-graph.v1`.

Each record contains:

- stable id;
- high-recall evidence states;
- preserved source refs;
- canonical kinetic primitives;
- six-channel kinetic compression;
- evidenced Fourth Door classes;
- record SHA-256.

The graph contains `engineVersion`, `inputSha256`, and `graphSha256`.

Same normalized input + same engine version must produce the same graph independent of input order. Duplicate ids fail closed.

## Kinetic compression

Fixed channel order:

`body_interface -> contact -> load -> constraint -> transfer -> terminal`

Do not fill holes for aesthetics. `unknown` is a valid and important result.

## Required joins

### Conversation miners

Conversation miners should be aggressively inclusive. If they already decided something belongs in the Arsenal, set `chekhov: true` and retain the excerpt/source refs that caused admission.

The deterministic engine is the shared downstream sorter. Do not make each miner maintain its own private kinetic taxonomy.

### Embodied Kinesis Voices

The existing character-specific embodied-kinesis grammar remains independent. Its verbs may overlap the primitive lattice, but character voice is not mechanical evidence about an Arsenal object.

### Grounded Motion

Grounded Motion may provide witnessed support/contact/body mechanics. Unknown Grounded Motion evidence remains unknown here. Never manufacture body contact from a noun such as `sword`, `axe`, `rifle`, `coffee pot`, or `door`.

### Story Simulator / Fourth Door

Preserve continuity/status/provenance. Derived mechanics and Fourth Door classes are evidence/hypothesis layers, not canon promotion.

## Runtime requirement

The `chekhov-kinesis-engine` Judgment Jar must remain in the default phone packet. Live intake and automated mining/backfill jobs must use the same admission law and downstream engine contract.

## Minimal commands

```bash
python tools/chekhov_kinesis_engine.py --input candidates.json --pretty
python -m pytest -q tools/test_chekhov_kinesis_engine.py tools/test_chekhov_kinesis_runtime_contract.py
```

## Failure policy

Fail closed on duplicate identity or malformed input. Preserve unsupported mechanics as `unknown`. Never remove a miner-admitted Chekhov candidate solely because the shortened downstream excerpt no longer contains the original violent trigger.
