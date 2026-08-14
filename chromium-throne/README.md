# Chromium Throne

Chromium Throne is the bare-metal desktop bootstrap layer for Home Center. It does not call Codex or an inference API. It owns durable task state, repository file access, shell execution, verification receipts, and crash recovery locally. Ordinary logged-in ChatGPT web tabs are replaceable cognition workers reached through a dedicated Chrome/Edge profile over loopback CDP.

The desktop does the work. The phone is a first-class command surface.

## What ships in v1

- Windows-local daemon on TCP `17373`.
- Dedicated persistent Chrome/Edge profile on loopback CDP port `9231`.
- Responsive desktop/mobile dashboard for commissioning repository tasks, reading status, and retrying failures.
- Authenticated private-LAN mobile operation using a persistent random bearer token.
- Windows Firewall rule limited to the Private network profile and the installed Node executable.
- A deterministic worker protocol: `list_files`, `read_file`, `write_file`, `shell`, `finish`.
- Repository-root path containment and a narrow host-destructive command guard.
- Readback verification after file writes.
- Durable `state.json` after every action; `running` tasks return to `queued` after a daemon restart.
- A per-task ChatGPT tab which is instructed to inspect, implement, test, and continue until completion or a genuine human-only gate.
- Windows scheduled-task startup and a Desktop shortcut.

This is owner-local desktop infrastructure. It is not a cloud browser worker and does not consume a Home Center cloud worker profile.

## Install on the desktop

From an up-to-date `home-center` checkout in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\chromium-throne\windows\install.ps1
```

The installer copies the runtime to `%LOCALAPPDATA%\HomeCenter\ChromiumThrone`, installs the pinned `puppeteer-core` dependency, runs the test suite, registers `HomeCenterChromiumThrone` at logon, requests one Windows elevation for the narrow Private-network firewall rule, launches the daemon, verifies the health contract, discovers private-LAN addresses, writes the tokenized phone URL to `mobile-url.txt`, and opens the local dashboard.

On first use, click **Open ChatGPT profile**. If the dedicated Chromium profile is not signed into ChatGPT, sign in once in that desktop browser window. Chromium Throne thereafter reuses that profile.

## Desktop use

Open the `Chromium Throne` Desktop shortcut. Enter an absolute repository path and the outcome you want, then click **Commission task**.

The daemon sends the task to a normal ChatGPT tab with the Throne action contract. ChatGPT chooses one bounded action at a time. The daemon executes it locally, returns the result to the same tab, persists the receipt, and continues. `finish` is accepted only when the worker chooses it after its implementation and verification loop.

## Phone use

Keep the desktop and phone on the same private LAN. The installer prints one or more `mobileUrls` and stores them at:

```text
%LOCALAPPDATA%\HomeCenter\ChromiumThrone\mobile-url.txt
```

Open one of those URLs in the phone browser. The responsive command surface can commission a desktop repository task, inspect current and previous tasks, see completion/failure/human-gate state, retry a failed task, and request that the desktop open its dedicated ChatGPT profile.

The mobile token is generated locally and stored at:

```text
%LOCALAPPDATA%\HomeCenter\ChromiumThrone\state\mobile-token.txt
```

Do not publish the tokenized URL. The LAN listener is intentionally plain HTTP for zero-friction private-network bootstrap, so the mobile lane is restricted to the Windows Private firewall profile. A future remote-access layer must add authenticated encryption rather than exposing this listener to the public Internet.

## Durable state

Task records:

```text
%LOCALAPPDATA%\HomeCenter\ChromiumThrone\state\state.json
```

Daemon log:

```text
%LOCALAPPDATA%\HomeCenter\ChromiumThrone\daemon.log
```

Dedicated browser profile:

```text
%LOCALAPPDATA%\HomeCenter\ChromiumThrone\state\chrome-profile
```

## Acceptance test

Chromium Throne is not accepted on desktop-only evidence.

1. Install successfully; `npm run check` must pass inside the installer.
2. Sign into the dedicated ChatGPT profile if required.
3. From the desktop dashboard, commission a nontrivial task against a disposable repository. Confirm the worker reads the repository before editing, writes a file, runs a test or direct verification command, and records `done`.
4. While a second task is running, terminate the daemon and run `%LOCALAPPDATA%\HomeCenter\ChromiumThrone\start-throne.ps1`. The task must recover as queued and continue from durable action history.
5. From the phone on the same private LAN, open the generated tokenized `mobileUrl`. Confirm the dashboard loads at phone width, shows the desktop task ledger, and can commission another repository task.
6. From the phone, confirm a failed task can be retried and its status updates without touching the desktop.
7. Confirm an un-tokened non-loopback request cannot access `/api/state` or task mutation endpoints.
8. Confirm the Windows firewall rule is scoped to `Private`, TCP `17373`, and the installed Node executable; Public-network exposure is not acceptance.

## Safety boundary

Chromium Throne binds file actions to the commissioned repository root. It blocks a small set of plainly host-destructive shell patterns such as shutdown, disk formatting, boot configuration, and obvious recursive deletion of system roots. It is still a developer tool: a ChatGPT worker can run normal repository shell commands, package managers, tests, Git commands, and project tooling as the signed-in desktop user.

CAPTCHA, account verification, or another browser gate that genuinely requires a human is reported as `human_gate`; the worker must not fabricate completion.
