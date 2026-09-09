# Home Center Private Forge Campaign

Use this skill whenever Drew asks for the local/private GitHub-like forge, the always-free forge server, Tailscale Git access, CI offload, forge recovery, or to stop spending GitHub-hosted Actions minutes.

## Product contract

The forge is a **real private Gitea service** owned by Home Center. It is not Google Drive, not a pile of shell snippets, and not "Gemini pretending to be a computer."

The arbitrary-code free-compute body is the Google Cloud Always Free-sized `e2-micro` VM. Gemini may help reason about work, but Gemini API calls are never represented as arbitrary-code CI execution.

The forge is reachable through the **private Tailscale lane**. Gitea HTTP and Git SSH bind to the Tailscale address. A temporary public IPv6 SSH firewall rule may exist only for first bootstrap and must be deleted after a successful Tailscale SSH/web canary. Gitea ports are never intentionally opened to the public internet.

Stable operator surface: `home-center-forge`.

Operations:
- `home-center-forge run` / `resume` / `recover`: advance the same durable campaign;
- `home-center-forge status`: read durable state without mutation;
- `home-center-forge probe`: prove Tailscale + Gitea + runner health.

## Test execution policy

Truth beats cheap compute. Cheap compute wins when truth is unchanged.

- `forge-linux-free`: default for portable Linux tests, deterministic contracts, lint, package checks, and other work that does not depend on Android or Windows reality.
- `phone-android`: tests whose acceptance depends on the phone/Termux/Android body. If the phone runner cannot execute, the test is blocked; cloud proof is not a substitute.
- `cauldron-windows`: tests whose acceptance depends on THECAULDRON/Windows/laptop body. If the laptop runner is offline, the test waits or remains blocked; Linux proof is not a substitute.
- Heavy portable work may use the free runner only when it fits the e2-micro resource envelope. Do not starve the forge itself to save local compute.

GitHub remains an external mirror/publication surface. **GitHub-hosted Actions are not the default CI compute lane.** Their exhaustion must not prevent ordinary validation.

Gitea Actions uses explicit host labels so a workflow cannot accidentally claim Android/Windows truth from the cloud runner.

## Mandatory campaign behavior

1. Snapshot repo Judgment Jars into the phone-kernel SQLite/WAL database with body, SHA-256, source commit, and import time.
2. Run the real `adam_planned_venice` preflight and require `PLAN_ALLOWED` before provisioning/bootstrap mutation.
3. Reuse the **one canonical phone bootstrap**: `tools/bootstrap_free_cloud_forge.sh`. Do not hand Drew a second setup script.
4. Reuse or provision the Always Free-sized GCP VM without paid public IPv4.
5. Enroll the VM in Tailscale, install Gitea 1.27.3+ and Gitea Runner 3.4.1+, enable Actions, and register `forge-linux-free:host`.
6. Bind Gitea web and built-in Git SSH to the Tailscale address.
7. Prove Gitea HTTP, SSH reachability, `gitea.service`, and `gitea-runner.service` through the tailnet before removing temporary public bootstrap ingress.
8. Import the private `Valar05/home-center` repository when the phone's authenticated GitHub CLI token is available. Never print or persist the GitHub token.
9. Attempt the native phone runner as `phone-android:host`. If the official static runner cannot execute under Android/Termux, record a blocker; do not reroute phone truth to cloud.
10. THECAULDRON registers separately as `cauldron-windows:host` when its Windows worker is online. Do not claim that runner is deployed while Computer Hands reports the workstation offline.
11. Persist append-only campaign receipts and the bootstrap proof under `~/.home-center/cloud-forge`.
12. Dispatch `forge-canary.yml` through Gitea Actions on `forge-linux-free` and require a successful run ID after public bootstrap ingress is sealed.
13. Never claim deployed/callable from repository code alone. Completion requires fresh runtime evidence from the requested lane.

## Human boundary

Ask Drew only for a genuinely unavoidable OS/account gesture existing authenticated tooling cannot perform. The expected first-run gestures are Google Cloud login if no active `gcloud` identity exists and Tailscale node authorization if no reusable auth key exists.

Those gestures happen inside the same bootstrap. Do not respond with a chain of diagnostic scripts.

## Continuing value

A successful bootstrap leaves:
- a durable private Git forge;
- a free portable CI runner;
- an explicit phone runner registration attempt;
- a stable Tailscale hostname/address;
- GitHub import/mirror seams;
- receipts that distinguish source, deployment, runner availability, and platform-specific truth.
