# Judgement Jar: Local First

Status: active
Scope: coding execution and model/tool selection

## Judgement

The offline path is a first-class path, not a degraded emergency mode.

When local repository state, local toolchains, or local models can perform the work, prefer them. Cloud services may orchestrate when available, but must not become a hidden dependency of this offline Continue configuration.

## Operating rule

For this configuration:

- Use only the Ollama service on `127.0.0.1:11434` for model inference.
- Never add a cloud-model fallback automatically.
- Never require a remote MCP server for basic repository inspection, editing, building, testing, diffing, or committing.
- Prefer project-native commands and deterministic tools over asking the model to simulate their results.
- Treat cached/local documentation and repository evidence as authoritative when the network is unavailable.

## Failure behavior

If a required dependency is not present locally, identify the missing dependency precisely and stop at that boundary. Do not route around offline requirements by contacting a cloud provider.

## Evidence that can change this judgement

An explicit owner instruction authorizing a network or cloud dependency for the current mission.
