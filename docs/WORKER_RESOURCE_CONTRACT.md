# Worker Resource Contract

Status: repository contract  
Registry: `ops/worker_profiles.v1.json`  
Validation: `node tools/worker_profile_contract_test.mjs`

Home Center sizes active workers by workload. The control plane remains small; each artifact worker owns one isolated job; independent artifacts scale across instances; direct deployment surfaces must be bound or explicitly exempt; CI and live readback are authoritative.

Active profiles are `control-plane`, `media-forge-light`, `media-forge-heavy`, and `browser-session`. The retired Codex-job profile and both retired worker assignments are deleted.

`fortress-model-foundry` is bound to `media-forge-light`: 4 vCPU, 4 GiB, concurrency 1, scale zero to eight, timeout 1800 seconds. It executes one direct-GLB compilation per instance. Safe internal library threading is allowed; unrelated jobs never share a namespace or mutable output path.

`home-center-mcp` is guarded by `control-plane`. `home-center-audio-render`, `home-center-video-render`, and `home-center-browser-worker` remain explicit targets and are not claims of deployment.

Bound deployments resolve values from `ops/worker_profiles.v1.json`, reject ad hoc resource overrides, validate before mutation, and read back live configuration. The Foundry release additionally requires clean current main and a queue pause across the worker/MCP swap.

A long worker must report immutable inputs, accepted/running/terminal state, bounded progress and logs, phase timings, output sizes and hashes, format validation, and publication readback. Exact replay reuses completed work. No heartbeat means unknown; ambiguous paid mutation means `needs_reconciliation`, never blind retry.
