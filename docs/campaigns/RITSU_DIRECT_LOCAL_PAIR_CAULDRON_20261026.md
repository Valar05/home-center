# Ritsu direct Tailscale pairing on THECAULDRON

## What this is

The current Ritsu phone app uses a **direct authenticated Tailscale connection**, not the older Home Center cloud pairing or its gateway token. The app's More → Pair THECAULDRON dialog requires:

- Origin: `http://100.68.37.106:19646` (pinned in `RitsuPairing.java`).
- Token: a 64-character lower-case hex device secret stored on Windows at `%USERPROFILE%\.ritsu-control\local-link\device-token` and created by the existing `tools/ritsu-local-server/server.mjs` when that server starts. The secret is never in Git, ChatGPT, a log, or an artifact.

The backend accepts authenticated GET `/v1/ritsu/status` and returns `ok=true,transport=tailscale-sse,cloudOps=0`. Older `ritsu-control-pair.ps1` uses the **wrong** endpoint and token location for this edition. Do not use it for Direct Local Link.

## Reusable alias on the Windows host

Repository-owned helper: `tools/campaigns/ritsu_local_pair_cauldron.ps1`.

One-time installation on THECAULDRON using the exact checked-in file:

```powershell
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File .\tools\campaigns\ritsu_local_pair_cauldron.ps1 -Mode Install
```

Run the above only **inside the pinned isolated checkout**; do not navigate into a dirty working repository or pull it. The installation copies the script to `%LOCALAPPDATA%\HomeCenter\RitsuLocalPair`, verifies byte hashes, and appends a marker-bounded `ritsupair` function to the owner's Windows PowerShell 5.1 CurrentUserCurrentHost profile (MyDocuments\WindowsPowerShell\Microsoft.PowerShell_profile.ps1). It refuses any unrelated existing alias or modified managed block and preserves other profile entries. A fresh Windows PowerShell terminal is required to load newly written profile functions. Existing open shells are not silently modified.

Use in a new Windows PowerShell:

```powershell
ritsupair
ritsupair -Mode Status
ritsupair -Mode Doctor
```

`ritsupair` verifies THECAULDRON's own Tailscale address, reads the **existing** local-link device token without printing it, checks the correct service with a bearer health request, then opens a **masked** local Windows Forms dialog. Only the user can reveal the token locally and enter it in the installed Android app. No password/token is copied to clipboard, regenerated, sent to cloud, or placed in receipts. `Status` does a bounded authenticated service check without showing the token. `Doctor` checks wiring and presence without touching credentials. `-Mode Remove` (run on the original helper) removes only the owned profile block, preserving other profile content.

## Operational boundaries

- If the device token file is missing, stop and examine/start the **approved existing local-link server**; never invent a substitute token or rotate credentials to make the helper pass.
- If the authenticated endpoint fails, check Windows Tailscale IP, listener and managed service route with read-only observations before changing any firewall, Serve rule or runtime. No automatic reconfiguration of unrelated services.
- THECAULDRON pairing UI closing is not proof the Android phone connected. After entering the credentials in Android, check the app's Direct link status and send a real turn to verify server/phone reply.
- Existing APK, private pairing data, local conversations and other live services remain intact.
- PowerShell profile aliases don't automatically appear in existing interactive shells or in other shells such as CMD.
- Windows CI contract: `tools/campaigns/ritsu_local_pair_cauldron.test.ps1`; tests PowerShell syntax, install/reinstall idempotence, refusal to overwrite a foreign function, profile-preserving removal and no-secret doctor mode. These CI tests don't prove a live desktop dialog or Android pairing.

## Source of truth

The [live Campaign Etiquette](https://docs.google.com/document/d/1wntegQjw7238dmGqbvs9TQmlsp4uXdXw7_wPciNx6sI/edit) is required at each campaign checkpoint. This document describes the direct-local Ritsu app only.
