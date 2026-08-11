# Offline Continue Coding Lane

Status: repository implementation present; local runtime acceptance still required
Owner: Drew
Execution surface: Continue + local Ollama on the Windows coding workstation
Mission: preserve useful coding capability when OpenAI and the public internet are unavailable

## Why this exists

The coding lane must not depend on OpenAI, another cloud model provider, remote MCP, or reconstruction from chat history. Continue supplies the coding-agent shell; local Qwen supplies model inference; the repository supplies doctrine through judgement jars; project-native tools supply deterministic execution and verification.

This is intentionally separate from Venice's social/creative role and from Home Center's strategic authority. A local coder may continue an authorized engineering trajectory. It does not invent a new mission.

## Known workstation model set

The accepted target model tags are:

- `qwen2.5-coder:7b` — primary local coding model for chat/edit/apply
- `qwen2.5-coder:1.5b` — fast local autocomplete model

Both are served by Ollama at `127.0.0.1:11434`.

The configuration deliberately contains no cloud provider and no remote model fallback.

## Repository anatomy

- `.continue/offline-config.yaml` — repo-pinned local-only Continue configuration.
- `.continue/rules/*judgement-jar*.md` — durable engineering judgement loaded as Continue rules.
- `tools/cn-offline.ps1` — explicit CLI launcher that verifies local Ollama/model availability, injects every judgement jar, and starts `cn` with the repo-pinned configuration.
- `tools/setup_offline_continue.ps1` — non-downloading setup/readiness script; optionally backs up and installs the offline config as the user's default Continue config.
- `tools/test_offline_continue.ps1` — acceptance probe. It verifies local dependencies/configuration and obtains a response from Continue through local Qwen. `-RequireInternetDown` additionally requires a failed public-network reachability test.

## Judgement jars

### Mission Boundary

Preserves requested outcome, owner, tool, execution lane, exclusions, evidence standard, and delivery surface. Boundary-changing improvements remain proposals.

### Local First

Forbids hidden cloud fallbacks in the offline configuration and prefers deterministic project-native tools over simulated results.

### Repository Truth and Evidence

Requires reading before writing, deterministic validation after writing, and explicit separation of documented, observed, inferred, and open claims.

### Change Discipline

Biases the smaller local model toward bounded patches and specifically treats failed filepath resolution as a path-discovery problem rather than permission to guess or rewrite broadly.

### Failure Recovery

Turns errors into evidence, permits one bounded repair tied to an observed mechanism, and stops repeated identical failures instead of burning cycles.

### Offline Toolchain Freeze

Treats installed tools as insufficient resilience by themselves. Known-good versions/configuration/model tags must be preserved, and updates must re-pass offline acceptance.

## Authority model

Continue is Hands, not the strategic owner.

The local model may:

- inspect the repository;
- implement an authorized code change;
- run project-native build/test/lint commands;
- inspect diffs and failures;
- make bounded repairs inside the commissioned mission.

It may not silently:

- change the mission;
- change owner, repository, tool, or execution lane;
- replace a requested architecture with an adjacent one;
- add a cloud dependency to escape local limitations;
- weaken verification to obtain a green result;
- report deployment or physical behavior without matching runtime evidence.

## Offline acceptance contract

Do not call this lane deployed solely because the repository files exist.

A fresh workstation acceptance receipt must show:

1. `cn` exists locally and its version is recorded;
2. Ollama is reachable only through the configured local endpoint;
3. both exact Qwen model tags are already installed;
4. the loaded Continue configuration declares no cloud provider or non-local model endpoint;
5. all judgement jars are present and loaded;
6. with public internet unavailable, Continue returns a response through the local configuration;
7. a bounded coding fixture can be edited by Continue, verified deterministically, and restored/cleaned up;
8. the receipt records exact command output and result without treating local success as deployment of anything else.

The acceptance result is green only when the no-network inference and bounded edit both pass.

## Resilience note

The offline lane should pin the final known-good Continue toolchain and preserve recovery artifacts through Home Center's durable file layer. Configuration in git is necessary but not sufficient for disaster recovery; installers/model artifacts must also survive the loss of the public network.
