# Repository Agent Instructions

## Worker infrastructure

Any new or changed Cloud Run service, Cloud Run job, Cloud Function, Firebase Function, Blender executor, audio worker, video worker, browser worker, or long-running worker must use `ops/worker_profiles.v1.json`.

- Register a real deployment as a bound assignment, or add a narrow explicit exemption with a durable reason.
- Deployment scripts resolve CPU, memory, concurrency, timeout, and scaling through `tools/worker_profile_contract.mjs`; do not duplicate resource numbers in environment variables.
- Validate before deployment and verify live configuration afterward.
- Run `node tools/worker_profile_contract_test.mjs`. CI is authoritative.

## Mechanical authoring

Blender is the only active modeling, topology, modifier, hierarchy, pivot, constraint, animation, UV, material, render, and GLB-export kernel. Use persistent `blender.workspace.*` operations through Home Center. The `.blend` revision is editable source truth. Foundry is retired and must never be selected.

`blender.workspace.render` is deprecated and retained only for compatibility. Do not select it for new work; use exact revision inspection and exported scene/validation artifacts instead. Inspect the exact scene revision before and after meaningful changes. Author openings and manufactured transitions as real topology. Plan named hierarchy, origins, pivots, constraints, and animation before export. Forbid primitive soup, detached coplanar detail, regeneration masquerading as iteration, homegrown mesh algorithms, and acceptance based on receipts. Human visual review is authoritative.
