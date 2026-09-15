# Home Center Liveness and Recovery Runbook

This is the restart and proof contract for the phone-to-desktop lane. Keep this document in the Home Center Drive-backed repository. It is intentionally operational: a registration record, a scheduled-task state, or a queued command is not proof that a carrier is alive.

## What must stay alive

`Drew phone -> Home Center phoneHandsRelay -> Android relay -> Home Center Computer Hands -> THECAULDRON -> Chromium Throne`

There are four independent liveness points:

| Component | Positive proof | Silent-drop detector | Restart authority |
| --- | --- | --- | --- |
| Home Center relay | `phoneHandsRelay` is `ACTIVE` and source label is expected | deployment state or label mismatch | authorized Home Center deployment lane |
| Android phone relay | `phone-relay-heartbeat.json` is fresh and device `lastSeenAtMs` is fresh | no successful `/pull` within 90 seconds | existing Termux command on the phone |
| Windows Computer Hands | Home Center worker `online=true`, fresh `lastSeenAtMs`, and fresh progress file | no worker heartbeat/progress for 240 seconds | `repair.ps1`, scheduled task, and watchdog |
| Chromium Throne | `throne.ps1 status` reports `state=running`; browser/profile evidence is present | process missing or stale launch state | `throne.ps1 launch` over Tailscale SSH |

The relay and workers are separate. A green Home Center service health response does not prove that either device is connected.

## Proof standard

Call a component **healthy** only when all of its required proofs are true at the same time:

1. The control plane reports the component as registered and authorized.
2. The component has a fresh timestamp, not merely an old `status=online` value.
3. A bounded no-op or marker command completes through the same lane.
4. The result is recorded with a timestamp, command/request ID, exit code, and source/version where available.

Call a component **silent** when its last successful heartbeat is older than the threshold above, even if its registration still says `online`.

Never treat these as completion: `queued`, `running`, `registered`, a scheduled task in `Ready` state, a process count, or a source-only test.

## Standard desktop proof

From the phone over Tailscale, use the stable address rather than the stale hostname:

```sh
ssh -o ConnectTimeout=10 dclar@100.68.37.106 hostname
ssh -o ConnectTimeout=10 dclar@100.68.37.106 "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\dclar\\bin\\throne.ps1 status"
```

The first command must return `TheCauldron`. The second must show the dedicated profile and `state=running` before a Throne action is dispatched.

For the Home Center carrier, use the authenticated Home Center operation, not JSON pasted into SSH:

```json
{
  "operation": "computer_hands.worker.status",
  "args": {"workerId": "windows-hands-01"}
}
```

Require `online=true`, `fileLayer=drive_sync`, a fresh `lastSeenAtMs`, and an understood queue/active-lane list. Record the response before and after a restart.

## Restart: Windows Computer Hands

This preserves the existing worker identity and DPAPI token. It is the normal recovery path.

### From Tailscale SSH

```sh
ssh -o ConnectTimeout=10 dclar@100.68.37.106 "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\dclar\\workspace\\home-center-organ-migration\\computer-hands\\windows\\repair.ps1 -RepoPath C:\\Users\\dclar\\workspace\\home-center-organ-migration"
```

If the repository is at a different path, pass that actual authenticated Home Center clone with `-RepoPath`. Do not use `install.ps1` or `rebootstrap.ps1` while `worker-token.dpapi` exists; those are token/bootstrap paths, not ordinary restarts.

### Verify the restart

Run the Home Center worker status operation twice, 20-30 seconds apart. Both responses must show `online=true` and a newer `lastSeenAtMs`. On THECAULDRON, the repair output must also show:

```text
taskState=Running
watchdogState=Running
tokenDecrypt=ok
workerId=windows-hands-01
```

For a hard failure, inspect these files before changing credentials:

```text
C:\Users\dclar\AppData\Local\HomeCenter\ComputerHands\startup.log
C:\Users\dclar\AppData\Local\HomeCenter\ComputerHands\worker.log
C:\Users\dclar\AppData\Local\HomeCenter\ComputerHands\watchdog.log
C:\Users\dclar\AppData\Local\HomeCenter\ComputerHands\progress.json
```

The Windows watchdog is configured to restart a non-running task and to restart a stale worker after 240 seconds without progress. That is a recovery mechanism, not proof that recovery succeeded: the next fresh worker status and progress timestamp are still required.

## Restart: Android phone relay

Home Center cannot wake a phone process that is no longer polling. When `lastSeenAtMs` is stale and a command remains queued, the phone-side relay must be restarted on the phone.

Use the existing Termux session on the phone. This is the normal foreground recovery command:

```sh
REPO=/storage/emulated/0/Documents/GodotProjects/home-center
mkdir -p "$HOME/.local/state/home-center"
pkill -f android_phone_home_center_relay.py 2>/dev/null || true
nohup python "$REPO/tools/android_phone_home_center_relay.py" \
  >>"$HOME/.local/state/home-center/phone-relay-console.log" 2>&1 &
echo $! > "$HOME/.local/state/home-center/phone-relay.pid"
```

If the checkout is in the Termux home directory, use:

```sh
REPO="$HOME/home-center"
```

The relay must retain these existing files; do not delete or recreate them during a restart:

```text
~/.config/home-center/codex-hub.json
~/.config/home-center/phone-relay.json
```

Those files hold the existing Home Center pairing and device token. Re-pairing is only allowed when the files are proven missing or invalid.

### Verify the phone restart

On the phone:

```sh
cat "$HOME/.local/state/home-center/phone-relay.pid"
stat "$HOME/.local/state/home-center/phone-relay-heartbeat.json"
cat "$HOME/.local/state/home-center/phone-relay-heartbeat.json"
tail -n 50 "$HOME/.local/state/home-center/phone-relay-console.log"
```

The heartbeat JSON must have `schema=home-center-phone-relay-heartbeat-v1`, the expected `deviceId`, `state=poll_ok` or a completed command state, and a recent `lastSuccessAtEpoch`. Then repeat the authenticated Home Center devices operation:

```json
{
  "operation": "command_center.phone_hands.devices",
  "args": {}
}
```

Require `deviceId=primary-phone`, `status=online`, and a newly advanced `lastSeenAtMs`. Only then issue a marker command and wait for `status=completed` with the marker in the result. A command that remains `queued` is proof that the phone is not consuming the queue.

## Restart: Chromium Throne

This is the existing dedicated Chromium profile on THECAULDRON:

```sh
ssh -o ConnectTimeout=10 dclar@100.68.37.106 "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\dclar\\bin\\throne.ps1 status"
ssh -o ConnectTimeout=10 dclar@100.68.37.106 "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\dclar\\bin\\throne.ps1 launch"
ssh -o ConnectTimeout=10 dclar@100.68.37.106 "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\dclar\\bin\\throne.ps1 status"
```

The second status response must show `state=running` and the same dedicated `profileDir`. To open a target:

```sh
ssh -o ConnectTimeout=10 dclar@100.68.37.106 "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\dclar\\bin\\throne.ps1 open https://www.qmee.com/en-us/surveys"
```

Do not substitute a phone browser, Browser Nerve, or ChatGPT Work mode. SSH/Tailscale is only the phone-facing recovery/control transport to the already-installed Throne.

## Recovery order

When the lane goes quiet, use this order:

1. Check Home Center service health and the phone/worker status records.
2. Check fresh timestamps, not labels.
3. Restart only the first stale component: phone relay, Windows worker, or Throne.
4. Recheck its timestamp twice.
5. Run a bounded marker through that same component.
6. Preserve the command ID, request ID, timestamps, exit code, and source/version in the receipt.
7. Resume the commissioned workload only after the marker completes.

## Canary receipt minimum

Every recovery canary must record:

```text
component
deviceId or workerId
commandId/requestId/ticketId
requestedAt
startedAt or leasedAt
completedAt
status
exitCode
marker or typed error
lastSeenAt before and after
source/version label
```

This is the minimum evidence needed to distinguish “it was registered” from “it was alive, restarted, received work, completed it, and remained observable.”

## Known limits

No watchdog can guarantee a battery-dead, powered-off, force-stopped, or network-isolated phone will restart itself. The contract prevents silent success claims by detecting stale heartbeats and preserving a single documented human recovery action: open the existing Termux relay and run the restart command above. The desktop watchdog can recover the Windows worker once THECAULDRON is powered and reachable; it cannot repair a powered-off host or a broken Tailscale path.
