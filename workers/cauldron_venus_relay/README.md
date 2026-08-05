# THECAULDRON VenusOS relay

This worker gives VenusOS a bounded OpenAI-compatible route to Ollama without exposing Ollama or a shell. THECAULDRON only makes outbound HTTPS requests to Helm Center; Ollama remains on `127.0.0.1:11434`.

## Security contract

- One-time ten-minute bootstrap code; the resulting worker token is stored only in the current Windows user's protected local directory.
- Exact model allowlist at registration and again on the worker.
- Chat messages only: no tools, functions, streaming, arbitrary URLs, file inputs, or commands.
- Strict request/response sizes, short ticket expiry, one worker lease, hashed credentials, and explicit failure receipts.
- `uninstall.ps1` removes the scheduled task and moves the install aside for recovery. Run the Helm Center revoke operation as the second half of removal.

## Installation gate

Do not install until the relay Cloud Function is deployed with `VENUS_CAULDRON_CLIENT_KEY` as a secret and `VENUS_CAULDRON_ALLOWED_MODELS` as an explicit environment value. Register the worker through `venus_relay.worker.register`, then run:

```powershell
.\bootstrap.ps1 -BootstrapCode '<single-use-code>' -Models @('qwen3.5:4b') -Start
```

Installation is not acceptance. Run a Venus-specific behavioral canary and inspect the provider disclosure before binding VenusOS.

