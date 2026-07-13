# She-Raw Security

Current slice:

- OAuth-protected MCP transport through Home Center metadata and bearer validation.
- Per-client identity from existing Home Center MCP OAuth token records.
- Secret redaction before persistence for bounded context and corrections.
- Audit events for invocations, corrections, feedback, command-state changes, and validations.
- No external repository mutation from She-Raw tools.

Production gaps:

- Add rate limits.
- Add backup verification.
- Add alerting for execution-lockout violations and invalid model output spikes.
- Replace token-backed GitHub helper use for corpus promotion with a least-privilege GitHub App.
- Add key rotation documentation for the GitHub App private key and model provider keys.
