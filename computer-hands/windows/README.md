# Home Center Computer Hands — Windows

This is the outbound Windows execution worker for the Home Center MCP `computer_hands.*` operation surface.

## Boundary

- **Drive sync is the file layer.** Computer Hands does not expose a second remote filesystem.
- The worker opens no inbound network port. It polls the owner-scoped Home Center `computerHands` HTTPS function for leased tickets.
- The worker runs in the signed-in user's interactive Windows session so screenshots, window focus, keyboard, mouse, and clipboard target the real desktop.
- The worker bearer token is stored with Windows DPAPI for the current user.
- Cloud-side action gates remain authoritative: ordinary writes require `approved=true`; `shell.exec` and `process.stop` additionally require `highRiskApproved=true`.
- Uninstall removes the scheduled task and local Computer Hands state only. It does not touch Drive-synced files.

## Supported actions

Read: `system.status`, `screen.capture`, `window.list`, `process.list`, `clipboard.get`.

Write: `window.focus`, `input.type`, `input.key`, `input.mouse`, `process.start`, `process.stop`, `shell.exec`, `clipboard.set`.

## First install

1. Through Home Center MCP, call `drive_operation` with `computer_hands.worker.register` and a stable `requestId`. The returned bootstrap code expires after ten minutes.
2. In a normal Windows PowerShell window, execute the one-shot installer from `main` and pass the bootstrap code.

```powershell
$code='PASTE_BOOTSTRAP_CODE'; $src=Invoke-RestMethod 'https://raw.githubusercontent.com/Valar05/home-center/main/computer-hands/windows/install.ps1'; & ([scriptblock]::Create($src)) -BootstrapCode $code
```

After installation the worker is registered as the `HomeCenterComputerHands` scheduled task and starts immediately.

## Repair / update

The installer is idempotent. Once a DPAPI token exists, rerun it without a bootstrap code to refresh the worker and scheduled-task definition:

```powershell
$src=Invoke-RestMethod 'https://raw.githubusercontent.com/Valar05/home-center/main/computer-hands/windows/install.ps1'; & ([scriptblock]::Create($src))
```

Use `-ForceRefreshToken -BootstrapCode <new-code>` only to rotate the worker credential.

## Uninstall

```powershell
$src=Invoke-RestMethod 'https://raw.githubusercontent.com/Valar05/home-center/main/computer-hands/windows/uninstall.ps1'; & ([scriptblock]::Create($src))
```

## Acceptance evidence

A green installation is not merely “the scheduled task exists.” Verify through the same Home Center MCP lane ChatGPT will use:

1. `computer_hands.worker.status` reports `online: true` and `fileLayer: drive_sync`.
2. Queue `system.status`; the returned ticket reaches `completed` with the expected Windows machine/session evidence.
3. Queue `screen.capture`; the returned ticket reaches `completed` with a bounded JPEG evidence envelope.
4. Queue `window.list`; it returns visible interactive-session windows.
5. Only after the read path is green, test a harmless approved write such as focusing an already-open window.

Do not claim computer control is deployed until the owner-side status and at least the read-only acceptance path have passed through Home Center MCP.
