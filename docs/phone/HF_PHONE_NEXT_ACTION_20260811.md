# HF Phone Next Action - 2026-08-11

After merge and deployment:

1. Restart or recover the primary phone relay so it re-registers with `phone_diagnostics_readonly`.
2. Verify `phone_hands.devices` includes `phone_diagnostics_readonly`.
3. Queue `capability_snapshot`, `toolchain_probe`, and `cache_probe` diagnostics.
4. Decide whether HF on phone is catalog-only, GGUF runner, ONNX runner, or rejected for the specific model/task.
