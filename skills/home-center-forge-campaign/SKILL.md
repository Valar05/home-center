# Home Center Forge Campaign

Use this skill whenever Drew asks to leverage the free-tier always-online server, establish SSH control, recover the cloud forge, or stop drip-feeding forge terminal commands.

## Product contract

The free-tier forge is a Home Center organ. It is not a pile of shell snippets and Drew is not its transport layer.

Stable operator surface: `home-center-forge`.

Operations:
- `home-center-forge run` / `resume`: advance the same durable campaign;
- `home-center-forge status`: read current durable state without mutation;
- `home-center-forge recover`: retry the governed campaign;
- `home-center-forge ssh [COMMAND]`: execute a bounded explicit SSH command against the proven forge identity.

## Mandatory campaign behavior

1. Snapshot repo Judgment Jars into the phone-kernel SQLite/WAL database with body, SHA-256, source commit, and import time.
2. Run the real `adam_planned_venice` preflight and require `PLAN_ALLOWED` before provisioning/bootstrap mutation.
3. Reuse the canonical `provision_gcp_free_forge_vm.sh` and `bootstrap_free_cloud_forge.sh`; do not invent a second forge architecture.
4. Preserve the free-tier/no-paid-IPv4 contract of those scripts.
5. Establish SSH control from the phone and prove it with an explicit canary plus host/user/uptime/Gitea evidence.
6. Persist append-only receipts and latest state under `~/.local/state/home-center/forge-campaign`.
7. Retry transient failures with bounded exponential backoff. Failure is a recoverable campaign state, not a request for Drew to paste another diagnostic command.
8. Install as a persistent Termux service with runit when available, nohup fallback otherwise, plus Termux:Boot recovery.
9. Never claim deployed/callable from repository implementation. The campaign becomes callable only after phone installation and fresh SSH receipt.

## Human boundary

Ask Drew only for a genuinely unavoidable OS/account gesture that existing authenticated tooling cannot perform. After the gesture, resume the same durable campaign automatically.

## Continuing value

A successful first run must leave a permanently callable SSH/status/recovery organ and accumulated receipts. Installation by itself is not success.
