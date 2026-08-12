# Judgement Jar: Offline Toolchain Freeze

Status: active
Scope: dependencies required for no-network coding

## Judgement

An offline-critical tool is not durable merely because it is installed today. Its known-good version, configuration, required local models, and recovery artifacts must be identifiable and preservable without a network dependency.

## Operating rule

- Prefer pinned, known-good versions for the offline coding lane.
- Do not auto-update Continue, Ollama, local models, compilers, or project toolchains during an offline-critical task.
- Record the Continue CLI version and exact Ollama model tags in acceptance evidence.
- Keep configuration and judgement jars in the repository so a replacement local model can inherit the same engineering doctrine.
- Treat installers/model archives as resilience artifacts; preserve them through the Home Center durable file layer when available.
- A newer version is a candidate until it passes the same offline acceptance test.

## Recovery rule

If an update breaks the coding lane, restore the last accepted tool version/configuration rather than weakening the jars or adding a cloud dependency.

## Evidence that can change this judgement

A newer pinned toolchain that passes the complete offline acceptance contract.
