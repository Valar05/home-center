# Chromium Throne

Chromium Throne is the bare-metal desktop bootstrap layer for Home Center. It does not call Codex or an inference API. It owns durable task state, repository file access, shell execution, verification receipts, and crash recovery locally. Ordinary logged-in ChatGPT web tabs are replaceable cognition workers reached through a dedicated Chrome/Edge profile over loopback CDP.

## What ships in v1

- Windows-local daemon on `127.0.0.1:17373`.
- Dedicated persistent Chrome/Edge profile on loopback CDP port `9231`.
- A local dashboard for commissioning repository tasks.
- A deterministic worker protocol: `list_files`, `read_file`, `write_file`, `shell`, `finish`.
- Repository-root path containment and a narrow host-destructive command guard.
- Readback verification after file writes.
- Durable `state.json` after every action; `running` tasks return to `queued` after a daemon restart.
- A per-task ChatGPT tab which is instructed to inspect, implement, test, and continue until completion or a genuine human-only gate.
- Windows scheduled-task startup and a Desktop shortcut.

This is deliberately not a cloud worker and does not use Home Center deployment profiles. It is owner-local desktop infrastructure.

## Install on the desktop

From an up-to-date `home-center` checkout in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\chromium-throne\windows\install.ps1
```

The installer copies the runtime to `%LOCALAPPDATA%\HomeCenter\ChromiumThrone`, installs the pinned `puppeteer-core` dependency, runs syntax/tests, registers `HomeCenterChromiumThrone` at logon, launches the daemon, verifies `/health`, and opens the dashboard.

On first use, click **Open ChatGPT profile**. If the dedicated Chromium profile is not signed into ChatGPT, sign in once in that browser window. Chromium Throne thereafter reuses that profile.

## Use

Open the `Chromium Throne` Desktop shortcut. Enter an absolute repository path and the outcome you want, then click **Commission task**.

The daemon sends the task to a normal ChatGPT tab with the Throne action contract. ChatGPT chooses one bounded action at a time. The daemon executes it locally, returns the result to the same tab, persists the receipt, and continues. `finish` is accepted only when the worker chooses it after its implementation and verification loop.

Task records live under:

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

1. Install.
2. Sign into the dedicated ChatGPT profile if required.
3. Commission a nontrivial task against a disposable test repository.
4. Confirm the worker reads the repo before editing, writes a file, runs a test/verification command, and records a `done` task.
5. While a second task is running, terminate the daemon process and run `%LOCALAPPDATA%\HomeCenter\ChromiumThrone\start-throne.ps1` again. The task must recover as queued and continue from its durable action history.

## Safety boundary

Chromium Throne binds file actions to the commissioned repository root. It blocks a small set of plainly host-destructive shell patterns such as shutdown, disk formatting, boot configuration, and obvious recursive deletion of system roots. It is still a developer tool: a ChatGPT worker can run normal repository shell commands, package managers, tests, Git commands, and project tooling as the signed-in desktop user.

CAPTCHA, account verification, or another browser gate that genuinely requires a human is reported as `human_gate`; the worker should not fabricate completion.
