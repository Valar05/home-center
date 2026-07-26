# Repository Agent Instructions

## Worker infrastructure

Any new or changed Cloud Run service, Cloud Run job, Cloud Function, Firebase Function, Blender worker, audio worker, video worker, browser worker, or long-running agent worker must use `ops/worker_profiles.v1.json`.

- Register a real deployment as a bound assignment, or add a narrow explicit exemption with a durable reason.
- Deployment scripts must resolve CPU, memory, concurrency, timeout, and scaling from the registry through `tools/worker_profile_contract.mjs`; do not duplicate or override resource numbers in environment variables.
- Validate resolved values before deployment and verify the live cloud configuration after deployment.
- Run `node tools/worker_profile_contract_test.mjs`.

CI is authoritative. These instructions route work to the contract; they do not replace mechanical enforcement.
