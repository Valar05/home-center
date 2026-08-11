# HF Phone Runtime Ruling - 2026-08-11

Hugging Face is not the phone runtime by default.

## Default phone-safe interpretation

- Hugging Face Hub: catalog and artifact source.
- Hugging Face Inference Providers: quota/billing-bound remote provider lane, not phone-local compute.
- Phone-local model execution: GGUF, ONNX, TFLite, PocketTTS, Piper, or another small runner with explicit artifact size and runtime proof.

## Avoid by default

- `pip install torch transformers` on Termux.
- GB-scale model pulls without explicit model identity and size approval.
- CUDA-only, desktop-only, or opaque Space-only demos.
- Claiming provider calls are local/private/offline.

## Debug target

After diagnostics deployment, inspect phone architecture, Python runtime, storage, memory, toolchain, and caches. Then choose the smallest local artifact path that matches the use case.
