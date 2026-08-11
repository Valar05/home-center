# HF Phone Debug Plan - 2026-08-11

Status: branch-local diagnostic plan.

## Goal

Debug why Hugging Face does not install or run on Drew's primary Android phone without turning the phone into a hot desktop clone or pretending provider inference is local runtime.

## Required capability

`primary-phone` must register `phone_diagnostics_readonly` through the Home Center phone relay before Adam can run strict no-overlay diagnostics. The diagnostic plane uses fixed-field actions only. It cannot run shell commands, write files, install packages, use network, touch UI, build, or call microphones/cameras.

## Diagnostic sequence after deployment and phone relay restart

1. `capability_snapshot` - architecture, Python runtime, storage, memory, load.
2. `toolchain_probe` - presence and hashes for Python, git, node, npm, clang, cmake, ninja, ollama, continue, vlad, and dungeon without executing them.
3. `cache_probe` - bounded cache presence for pip, npm, Gradle, and Ollama.
4. Optional `repo_status` / `file_manifest` only inside the registered GodotProjects root.

## Likely Hugging Face ruling

Hugging Face on phone should be treated as a catalog and artifact source, not as a full `transformers`/`torch` desktop runtime. Phone-acceptable lanes are GGUF, ONNX, TFLite, Piper/PocketTTS, and small quantized local runners. Provider-side Hugging Face inference remains quota/billing-bound and must not be described as phone-local or indefinitely free.

## Stop gates

- If phone battery, storage, thermal state, or memory is tight, park heavy installs and use catalog-only mode.
- Do not run `pip install torch transformers` on phone unless Drew explicitly authorizes that pain test.
- Do not download GB-scale models without explicit size and model identity approval.
