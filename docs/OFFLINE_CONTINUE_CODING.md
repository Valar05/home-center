# Offline Continue Coding Lane

Status: repository implementation present; local runtime acceptance still required
Owner: Drew
Execution surface: Continue + local Ollama on the Windows coding workstation
Mission: preserve useful coding capability when OpenAI and the public internet are unavailable

## Why this exists

The coding lane must not depend on OpenAI, another cloud model provider, remote MCP, or reconstruction from chat history. Continue supplies the coding-agent shell; local Qwen supplies model inference; the repository supplies doctrine through judgement jars; project-native tools supply deterministic execution and verification.

This is intentionally separate from Venice's social/creative role and from Home Center's strategic authority. A local coder may continue an authorized engineering trajectory. It does not invent a new mission.

## Known workstation model set

The durable model chain is:

- `qwen2.5-coder:7b` — already-installed base weights for local coding.
- `home-center-qwen-coder:7b-8k` — repo-defined local runtime model derived from those base weights with `num_ctx 8192`; this is the model Continue uses for chat/edit/apply.
- `qwen2.5-coder:1.5b` — fast local autocomplete model.

All are served by Ollama at `127.0.0.1:11434`. Creating the Home Center runtime model reuses the locally installed base layers; it is not a second model download.

The configuration deliberately contains no cloud provider and no remote model fallback.

## Repository anatomy

- `.continue/offline-config.yaml` — repo-pinned local-only Continue configuration.
- `.continue/models/Modelfile.qwen2.5-coder-7b-8k` — pins the Ollama runtime context to 8192 tokens so Continue validation and the actual Ollama runner agree.
- `.continue/rules/*judgement-jar*.md` — durable engineering judgement loaded as Continue rules.
- `tools/cn-offline.ps1` — explicit CLI launcher that verifies local Ollama/base-model availability, locally materializes the pinned runtime model when missing, injects every judgement jar, and starts Continue with the repo-pinned configuration.
- `tools/setup_offline_continue.ps1` — non-downloading setup/readiness script; prepares the pinned local runtime model and optionally backs up and installs the offline config as the user's default Continue config.
- `tools/test_offline_continue.ps1` — acceptance probe. It verifies local dependencies/configuration, model parameters, observed Ollama runtime context, local Continue inference, and a bounded edit. `-RequireInternetDown` additionally requires public-network reachability checks to fail.

## Windows Continue launcher trap

The npm-installed `cn` command resolves through `cn.ps1` in PowerShell, and that shim exits its caller. That is hostile to a composable acceptance harness because a nested Continue call can terminate the parent PowerShell before its `catch`/`finally` blocks write evidence.

The offline lane therefore resolves and invokes `cn.cmd` explicitly. It launches the same installed Continue CLI package as a child process while preserving the parent PowerShell evidence harness.

## Context-length contract

The installed Qwen2.5 Coder 7B metadata reports a 32,768-token native context, but Ollama on this workstation instantiated the base tag with a 4,096-token runtime context by default. Six judgement jars plus Continue's own prompt exceeded that window before useful generation.

The offline lane does not rely on Continue 1.5.47 to propagate its YAML `contextLength` into Ollama. Instead, the repo-defined runtime model pins `PARAMETER num_ctx 8192`. Acceptance is not satisfied by YAML alone: after inference, Ollama itself must report the Home Center runtime model loaded with at least 8192 tokens of context.

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

1. the Windows-isolated Continue launcher `cn.cmd` exists locally and its version is recorded;
2. Ollama is reachable through the configured local endpoint;
3. both exact Qwen base model tags are already installed;
4. the pinned Home Center Qwen runtime model is created from local base layers and declares `num_ctx 8192`;
5. the loaded Continue configuration declares no cloud provider or non-local model endpoint;
6. all judgement jars are present and loaded;
7. Continue returns the required inference token through the local configuration;
8. Ollama itself reports the Home Center coder loaded with at least 8192 tokens of runtime context;
9. a bounded coding fixture can be edited by Continue, verified deterministically, and restored/cleaned up;
10. the receipt records exact command output and result without treating local success as deployment of anything else.

For a literal air-gap acceptance, rerun the same contract with `-RequireInternetDown` while public networking is actually unavailable. A green connected-machine run proves the configured model path is local and cloud-free; it is not evidence that the network was physically absent.

## Git LFS recovery hazard

A fresh acceptance clone encountered a missing Git LFS payload in historical evidence and could not complete normal checkout. The source tree itself remained recoverable by setting `GIT_LFS_SKIP_SMUDGE=1` and retaining LFS pointer files.

For disaster recovery, do not make source checkout depend on every historical binary payload still existing upstream. Preserve critical LFS artifacts separately through Home Center's durable file layer, and use skip-smudge source recovery when the binary archive is incomplete.

## Resilience note

The offline lane should pin the final known-good Continue toolchain and preserve recovery artifacts through Home Center's durable file layer. Configuration in git is necessary but not sufficient for disaster recovery; the Continue package, Ollama installer/runtime, base model blobs/manifests, required compilers/toolchains, and any critical LFS artifacts must also survive the loss of the public network.
