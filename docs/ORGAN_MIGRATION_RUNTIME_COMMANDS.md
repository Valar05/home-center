# Organ Migration Runtime Commands

This is the memory sheet for the Organ migration on THECAULDRON. It records existing scripts and the safe order for using them. It does not create a new control plane.

For the full liveness thresholds, restart procedures, and receipt requirements, use [HOME_CENTER_LIVENESS_AND_RECOVERY.md](HOME_CENTER_LIVENESS_AND_RECOVERY.md) before dispatching work.

## Runtime topology

`Drew phone -> Home Center -> windows-hands-01 -> THECAULDRON -> Chromium Throne -> Gemini`

The phone-facing product lane is Home Center. Tailscale/SSH is a recovery and inspection lane for the already-installed THECAULDRON carrier. ChatGPT Work mode, Browser Nerve, a phone browser, and arbitrary phone shell are not substitutes for Chromium Throne.

## Home Center scripts

| Path | Remember it for |
| --- | --- |
| `computer-hands/windows/repair.ps1` | Repair the existing `windows-hands-01` worker without rotating its token. Recreates and starts `HomeCenterComputerHands` and `HomeCenterComputerHandsWatchdog`. |
| `computer-hands/windows/install.ps1` | First install or explicit token refresh only. Do not use merely because a task is unhealthy when `worker-token.dpapi` still exists. |
| `computer-hands/windows/rebootstrap.ps1` | Rebootstrap only when the existing token is proven missing or invalid and a new authorized bootstrap code exists. |
| `computer-hands/windows/launch.ps1` | Scheduled-task entrypoint. Normally invoked by `HomeCenterComputerHands`, not manually. |
| `computer-hands/windows/home-center-hands.ps1` | Windows worker loop: polls Home Center, leases one ticket, heartbeats, executes, and posts bounded evidence. |
| `computer-hands/windows/watchdog.ps1` | Restarts a stale worker using the existing task and progress contract. |
| `computer-hands/windows/README.md` | Computer Hands boundary, supported actions, and acceptance checks. |
| `tools/workload_phone_control_recovery_handoff.sh` | Commissioned phone-relay recovery handoff. Run only through the verified `windows-hands-01` carrier and preserve its receipts. |
| `functions/computer_hands_api.js` | Home Center operation contract for worker status, request creation, request status, and cancellation. |
| `functions/phone_hands_relay.js` | Cloud-side phone relay implementation and pairing contract. |
| `tools/android_phone_home_center_relay.py` | Android relay agent. It is the phone-side Home Center poller, not a replacement for the desktop carrier. |
| `tools/setup_android_phone_home_center_relay.sh` | Install/setup for the existing Android relay. Use only when the phone relay is the active recovery target. |

## Chromium Throne scripts

| Path | Remember it for |
| --- | --- |
| `tools/install_chromium_throne.ps1` | Install/update the dedicated Chromium Throne profile and extension on THECAULDRON. Verify the install receipt afterward. |
| `browser-porch/relay.mjs` | Local Throne relay schema and provider boundary. Organ remains authoritative; provider output is untrusted. |
| `browser-porch/throne-client.mjs` | Client for the existing Throne relay. |
| `browser-porch/throne-relay-runner.mjs` | Runner for the local Throne relay process. |
| `browser-porch/README.md` | Throne topology, evidence ladder, and deployment limits. |

The current THECAULDRON host-local phone bridge is outside this repository:

`C:\Users\dclar\bin\throne.ps1`

From a phone on Tailscale, the known working recovery lane is:

```sh
ssh dclar@100.68.37.106 hostname
ssh dclar@100.68.37.106 "powershell -ExecutionPolicy Bypass -File C:\\Users\\dclar\\bin\\throne.ps1 status"
ssh dclar@100.68.37.106 "powershell -ExecutionPolicy Bypass -File C:\\Users\\dclar\\bin\\throne.ps1 launch"
ssh dclar@100.68.37.106 "powershell -ExecutionPolicy Bypass -File C:\\Users\\dclar\\bin\\throne.ps1 open https://www.qmee.com/en-us/surveys"
```

Use `100.68.37.106` or the current Tailscale address. The stale `thecauldron` hostname previously aborted; do not treat that failure as proof that THECAULDRON is offline.

## Home Center operation snippets

These are authenticated Home Center operations, not shell commands. JSON pasted into an SSH shell will be interpreted as separate commands.

Worker status:

```json
{
  "operation": "computer_hands.worker.status",
  "args": {"workerId": "windows-hands-01"}
}
```

Create a bounded request:

```json
{
  "operation": "computer_hands.request.create",
  "args": {
    "requestId": "stable-request-id",
    "ticketId": "stable-ticket-id",
    "workerId": "windows-hands-01",
    "laneId": "organ-migration-20260915",
    "action": "shell.exec",
    "arguments": {
      "command": "existing commissioned command",
      "workingDirectory": "C:\\Users\\dclar\\workspace\\home-center"
    },
    "approved": true,
    "highRiskApproved": true
  }
}
```

Cancel a queued or running request only when the exact ticket is authorized for cancellation:

```json
{
  "operation": "computer_hands.request.cancel",
  "args": {
    "requestId": "stable-cancel-id",
    "ticketId": "exact-ticket-id",
    "reason": "bounded operator reason"
  }
}
```

## Evidence checklist

A task state is not a heartbeat. Before dispatching migration work, require:

- `workerId=windows-hands-01`;
- `online=true` with a fresh `lastSeenAtMs`;
- `fileLayer=drive_sync`;
- queue depth and active lanes understood;
- no duplicate worker identity;
- request status reaches `completed` or a typed failure with stdout/stderr.

The registration record is not enough. Require a fresh timestamp and a bounded marker completion. The full restart and anti-silent-drop contract is in [HOME_CENTER_LIVENESS_AND_RECOVERY.md](HOME_CENTER_LIVENESS_AND_RECOVERY.md).

For the Organ migration, do not advance beyond the phone gate until the handoff produces its own recovery evidence. `queued`, `running`, a Windows task state, or a source-only test is not completion.

## Known failure boundaries

- The Windows worker can fail before `worker.log` exists if PowerShell cannot load `Microsoft.PowerShell.Security` because duplicate type data is already present. Capture `startup.log` before changing credentials.
- The Windows checkout can give the Bash handoff CRLF input (`set: pipefail\\r`). Stream-normalize line endings for execution; do not rewrite the commissioned source file.
- The worker shell may not have Node, Git Bash, `sed`, `python3`, or `gcloud` on `PATH`. Supply paths to already-installed executables through the existing request; do not install a new runtime as a workaround. On this host, the installed Python interpreter is `C:\\Users\\dclar\\AppData\\Local\\Programs\\Python\\Python313\\python.exe`.
- The recovery handoff's temporary clone can fail on an unrelated missing Git LFS object. `GIT_LFS_SKIP_SMUDGE=1` is an execution-time checkout workaround; it does not repair or delete the missing artifact.
- The phone relay contract now includes the `overlay_heartbeat` implementation and is deployed with the queue repair. Preserve the source label and verify the phone heartbeat before treating the relay as callable.
- A running Computer Hands ticket serializes the physical desktop. Inspect and cancel only the exact authorized ticket before dispatching migration work.
- If the handoff reports `WORKLOAD_INGRESS_BLOCKED`, preserve that receipt and stop. Do not replace the phone lane with arbitrary SSH, Browser Nerve, or another browser architecture.

## Organ migration gate

The authoritative Organ state is `codex/organ-state-canary-20260915`, currently `CANARY_ONLY` until the primary phone canary passes. Only after that gate may the work proceed to the Organ-Throne schema repair, Gemini browser session, story continuity proof, code-generation proof, and release evidence.
