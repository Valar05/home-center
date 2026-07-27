# Command Center Codex Worker Discovery Tombstone

Status: permanent
Effective: 2026-07-27
Owner: Command Center MCP control plane

## Decision

Command Center must not discover, provision, route, wake, register, lease, supervise, or resume Codex workers. This is a product boundary, not a temporary feature flag. The constant in `functions/command_center_mcp.js` is intentionally hard-coded and has no environment-variable override.

A future change must not silently reactivate this subsystem. Reintroduction requires a new explicit user command, a replacement architecture contract, removal of this tombstone in a separately reviewed change, credential reprovisioning, and new live acceptance evidence.

## Disabled Surfaces

The canonical disabled-operation set is `COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS`. It covers:

- execution job creation, follow-up creation, queued dispatch, resume, and answer-driven resume;
- Codex agent activation creation, resume packets, execution artifacts, Codex refs, and completion mutation;
- worker and host listing, inspection, registration, wake, retirement, reconciliation, restart, and capability lookup;
- cloud Codex worker provisioning and provisioning inspection/reconciliation;
- machine-image and Codex-session registration, allocation, inspection, and reconciliation;
- routing explanation, worker-pool health, and multi-worker/multi-session proof operations;
- every `/agent/*` and `/worker/*` HTTP route;
- the Cloud Codex worker deployment script.

Disabled operations are removed from direct Command Center MCP tool discovery and from the Home Center Command Center operation registry. Stale dispatcher clients receive HTTP-style status `410` with code `command_center_codex_worker_discovery_permanently_disabled`. Worker HTTP clients receive the same structured code.

## Preserved Systems

The following are separate capabilities and remain operational:

- non-agent Blender render submission;
- Command Center render queues and specialized render workers;
- project records and read-only historical job/agent evidence;
- managed knowledge buckets;
- app-control and browser operations;
- Home Center Drive, Calendar, SMS, audio, and other non-Codex integrations.

Firestore worker, lease, activation, session, provisioning, and job records are historical audit evidence. Cleanup retires active-looking records and revokes worker-token credentials; it does not erase audit history.

## Verification

Run:

```sh
node tools/command_center_codex_worker_discovery_disabled_test.mjs
sh tools/home_center_ci_validate.sh
```

Post-deployment checks must prove:

1. health reports `codexWorkerDiscovery.state=permanently_disabled`;
2. capabilities do not advertise a disabled tool;
3. stale dispatcher calls fail with the structured tombstone;
4. `/agent/*` and `/worker/*` return `410`;
5. non-agent render tools remain advertised;
6. no Command Center Codex Cloud Run jobs or active worker credentials remain;
7. no unrelated Cloud Run service, render worker, queue, or deployment is deleted or orphaned.

## Rollback

There is no operational rollback. Do not redeploy a prior revision to restore worker discovery. Ordinary service rollback may only target a revision that preserves this tombstone. Reintroducing Codex worker discovery is a new product decision and architecture change under the gate described above.
