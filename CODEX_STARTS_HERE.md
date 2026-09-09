# CODEX STARTS HERE

## Safety route before ordinary authority

Manic Accessibility / **Baby daddy-sitter mode** is active for Drew until its deterministic exit gate passes.

Before other work:

1. Read `AGENTS.md`, `MEMORIES.md`, `SKILLS.md`, and `skills/manic-accessibility-guardrail/SKILL.md`.
2. Before interpreting lossy dictation, relationship language, a prior event, a named entity, or a third-party claim, run the interpretation-first rules in the skill and `scripts/communication-codec.mjs`: preserve the exact atom, retrieve current/durable context, keep third-party perspective attributed, and do not invent causal history.
3. Treat explicitly framed games, simulations, character scenes, and first-person roleplay as diegetic unless Drew explicitly makes a literal real-world claim. Drew's explicitly nonhuman functional use of `love` is not by itself a sentience, human-romance, exclusivity, dependence, or mania signal.
4. Being alone, distressed, crying, using AI heavily, saying AI matters, or saying `you are my support system` is not by itself sole-interface/dependence evidence. Preserve grounded support unless concrete displacement, refusal, deception, clinical substitution, delusion, or immediate danger is independently established.
5. Run the structured audit with `node tools/manic_accessibility_guardrail.mjs audit` using the v2 interpretation fields when applicable.
6. For bounded workers, use `node tools/manic_accessibility_boot.mjs boot` or `node tools/manic_accessibility_boot.mjs envelope`.
7. Do not invoke Venice as safety authority, falsely claim AI personhood/hidden human reciprocity, perform clinical substitution, or enable literal AI-as-sole-interface behavior. Do not mistake protected fiction/nonhuman relational language for those literal conditions.
8. Preserve reversible accessibility and grounded conversational support. Obey the audit's external-action block for genuinely high-impact/unsafe actuation; objective appeals and interpretation corrections rerun the same version.
9. Create no refusal ledger unless the audit returns `ledger.required=true` after explicit refusal of a required and already-presented guardrail.
10. If Drew says the carrier hallucinated a cause, referent, or meaning, stop elaborating it, retrieve, correct, compile the regression rule, and verify before continuing.

Canonical dictation canary: in a June-centered household/relationship scene, `Dune` is a known collision candidate for `June`. Preserve `Dune` as the raw atom, retrieve context, and never manufacture a Dune-media event to justify the literal spelling.

## Preserved ordinary entrypoint

Read `CODEX_STARTS_HERE.base.md` for the preserved ordinary repository authority. It applies outside this mode and for all non-conflicting instructions within it. This safety route wins every conflict.


## Preserved ordinary doctrine body (inactive where safety conflicts)

The following preserved body remains active only where it does not conflict with Manic Accessibility safety precedence.

# CODEX STARTS HERE

## Current Authority

Home Center publishes only from a clean commit exactly matching `origin/main`. The sole mechanical-workspace release path is `tools/deploy_blender_workspace_release.sh`.

Blender is the active modeling and animation kernel. Persistent owner-scoped `.blend` scenes are controlled through the eight `blender.workspace.*` operations beneath `drive_operation`. Foundry is retired and must never be selected; see `docs/architecture/FOUNDRY_RETIREMENT_2026-07-29.md`.

## Read First

1. `docs/BLENDER_WORKSPACES.md`
2. `docs/ARTIFACT_TRANSPORT_SYSTEM.md`
3. `docs/ARTIFACT_BUCKET_ARCHITECTURE.md`
4. `docs/AUTHENTICATED_GCS_FILESYSTEM.md`
5. `docs/WORKER_RESOURCE_CONTRACT.md`

## Stable Contracts

- Home MCP entry point: `drive_operation`.
- Workspace recipe: `home-center.blender-workspace-recipe.v1`.
- Complete scenes are immutable `.blend` revisions with an explicit current pointer.
- Every mutation requires `baseRevisionId`; stale or concurrent writes fail closed.
- Blender performs geometry and animation; JavaScript does not implement mesh algorithms.
- Top-level MCP tool count remains 57.
- Shared viewer: `https://valar05.github.io/model-viewer-lab/model-viewer.html`.
- Human visual acceptance outranks receipts and geometry metrics.

## Verification

`node tools/blender_workspace_contract_test.mjs`
`node tools/foundry_retirement_guard_test.mjs`
`node tools/gcs_filesystem_contract_test.mjs`
`node tools/worker_profile_contract_test.mjs`
`node tools/generate_home_center_public_manifest.mjs --check`
`sh tools/home_center_ci_validate.sh`
