# Worker Resource Contract

Status: repository contract  
Registry: `ops/worker_profiles.v1.json`  
Validation: `node tools/worker_profile_contract_test.mjs`

## Outcome

Home Center sizes workers by workload, not by whichever deployment command an agent happened to type.

The control plane stays small. Long-running CPU work gets a dedicated forge. Independent artifacts scale across instances. Ordered work inside one artifact uses the native application's threads. Every promotion is measured against an immutable input and the same acceptance checks.

## Profiles

### `control-plane`

Use for authentication, dispatch, registries, status, and short provider operations.

- 1 vCPU
- 512 MiB
- request concurrency
- scale to zero

Do not move Blender, FFmpeg, browser sessions, or long agent execution into this profile to avoid creating another service.

### `codex-job`

Use for one bounded agent job with its own workspace.

- 2 vCPU
- 4 GiB
- one task per execution
- no automatic retry
- up to eight independent jobs may run in parallel

Scale out separate jobs. Do not give one Codex process eight cores without evidence that its child processes can use them.

### `media-forge-light`

Use for audio mixing, encoding, and similar native media work.

- 4 vCPU
- 4 GiB
- concurrency 1
- zero to eight instances
- native threads may use all available CPUs

One final codec stream remains ordered. Scenes, chapters, stems, or alternate outputs may run on separate instances when they are independently retryable.

### `media-forge-heavy`

Use for Blender and video work that needs a larger filesystem and resident working set.

- 4 vCPU
- 8 GiB
- concurrency 1
- zero to four instances
- native threads may use all available CPUs

Parallelize independent frames, shots, scenes, or render jobs across instances. Let Blender, Cycles, ImageMagick, or FFmpeg own safe intra-artifact threading. Do not split a stateful simulation or codec stream at arbitrary byte or frame boundaries.

### `browser-session`

Use for an isolated browser session.

- 2 vCPU
- 2 GiB
- concurrency 1
- zero to four instances

A browser session owns mutable cookies, pages, and process state. Never multiplex unrelated users or jobs into one browser instance merely because Cloud Run permits request concurrency.

## Current assignments

`command-center-blender-render` is bound to `media-forge-heavy`.

`command-center-codex` is bound to `codex-job`.

`home-center-mcp` is guarded by `control-plane`; it must not inherit forge sizing.

`home-center-audio-render`, `home-center-video-render`, and `home-center-browser-worker` are declared targets. A target is not a claim that the migration is deployed. Each target carries an explicit promotion gate in the registry.

## Scale up, scale out, or stop

Scale up one worker when:

- the measured phase is CPU-bound;
- the native program can use additional cores;
- more memory prevents a proven spill, OOM, or repeated full-buffer copy;
- the same-input benchmark lowers elapsed time enough to justify the cost.

Scale out when:

- artifacts are independent;
- each job has its own immutable input and idempotency key;
- failure and publication are isolated per job;
- the queue enforces the assignment's instance cap.

Stop increasing resources when:

- CPU utilization is low;
- the phase is waiting on provider or storage I/O;
- the application is single-threaded;
- 4 to 8 vCPU promotion produces less than 25% elapsed-time improvement;
- cost rises faster than the user's wait time falls.

Eight vCPU is a benchmarked exception, never a default. The repository contract rejects profiles above four vCPU unless the policy and evidence are deliberately revised.

## Long-work evidence

Every long worker must report:

- immutable request and input hashes;
- accepted, running, completed, failed, or quarantined state;
- lease heartbeat during every long phase;
- phase name and bounded progress;
- phase timings in the terminal receipt;
- output byte count and hash;
- decode or format validation appropriate to the artifact;
- publication readback from every claimed destination.

No heartbeat means unknown, not failed. An expired lease plus absent artifact means stale. Paid provider ambiguity means quarantine, never automatic retry.

## Promotion workflow

1. Capture a real baseline with phase timings.
2. Change one resource or execution variable.
3. Run the same immutable input.
4. Apply the same acceptance checks.
5. Compare elapsed time, estimated cost, CPU, and memory.
6. Promote only if the result materially reduces human wait or repairs a proven capacity failure.
7. Record the result beside the profile assignment.

The user's time is an explicit optimization target. Scale-to-zero and bounded instance caps control idle and runaway cost; they do not justify making a fourteen-minute artifact wait eleven minutes to save pocket lint.

## Acceptance

The contract is healthy when:

- CI validates the registry and every bound deployment marker;
- Blender defaults to 4 vCPU, 8 GiB, concurrency 1, scale to zero, and at most four instances;
- Codex jobs default to 2 vCPU and 4 GiB with no automatic retry;
- the MCP control plane remains outside forge profiles;
- target assignments cannot be described as deployed;
- resource promotions carry same-input runtime evidence.
