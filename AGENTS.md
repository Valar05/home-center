# Repository Agent Instructions

## Worker infrastructure

Any new or changed Cloud Run service, Cloud Run job, Cloud Function, Firebase Function, Blender worker, audio worker, video worker, browser worker, or long-running agent worker must use `ops/worker_profiles.v1.json`.

- Register a real deployment as a bound assignment, or add a narrow explicit exemption with a durable reason.
- Deployment scripts must resolve CPU, memory, concurrency, timeout, and scaling from the registry through `tools/worker_profile_contract.mjs`; do not duplicate or override resource numbers in environment variables.
- Validate resolved values before deployment and verify the live cloud configuration after deployment.
- Run `node tools/worker_profile_contract_test.mjs`.

CI is authoritative. These instructions route work to the contract; they do not replace mechanical enforcement.

## Purposeful geometry economy

Every topology-producing Foundry operation must fail closed unless every generated vertex is covered by an explicit purpose ledger and bounded by operation, component, asset, and commissioned-scene ceilings. Valid purposes are silhouette, manufactured-form transition, mechanical interface or articulation, necessary closure, stable edge highlight, or a demonstrated shading correction that cannot be achieved more cheaply.

- Treat global geometry limits only as crash fuses, never production budgets.
- Preflight predictable growth and build destructive topology transactionally.
- Keep unique source vertices, unique source triangles, and expanded scene cost separate.
- Require remove-or-merge evidence before `purposeValid` can pass.
- Report `topologyValid`, `budgetValid`, and `purposeValid` independently; none implies human acceptance.
- Reject evenly dense grids, decorative sections, Boolean debris, invisible tessellation, and any topology group whose removal causes no accepted-view regression.

`node tools/foundry_contract_test.mjs` is the executable gate. CI is authoritative; prose does not waive it.
