# Ritsu Control Pairing Campaign: durable Windows operator handoff (2026-10-23)

## Owner correction
The original `tools/campaigns/ritsu-control-pair.ps1` is a **local masked credential viewer**, not a proper script campaign. It is now an internal pairing UI/health subroutine, called by the durable controller `tools/campaigns/ritsu-control-pair-campaign.ps1`. The helper no longer terminates the host PowerShell worker on failure; it propagates a blocked result.

## Pinned, tested source and authority
- Source commit: `27b9b384dcb3ebea4890ef42217f4b02e1016c0c`
- Branch: `feature/ritsu-command-bridge-scavenge-20261022`, PR #387.
- Installed pinned Windows worktree: `%LOCALAPPDATA%\HomeCenter\RitsuPairCampaignSource\source-27b9b384dcb3`
- Entrypoint: `tools\campaigns\ritsu-control-pair-campaign.ps1`
- Helper: `tools\campaigns\ritsu-control-pair.ps1`
- Durable state and append-only receipts: `%LOCALAPPDATA%\HomeCenter\RitsuControlPairCampaign\latest.json` and `history.jsonl`.
- Public CI contract passed for source commit (Windows parser, isolated worker canary, independent STOP, missing-token fail-closed): https://github.com/Valar05/home-center/actions/runs/40049014979
- THECAULDRON exact-Git-SHA clean isolated worktree parse, Plan, Canary, Status all passed; receipt `canary_passed`, out-of-band kill verified, lastActionAgeSec near one second. An earlier isolated missing-token test verified a blocked receipt and no phone action.

## Stable operator commands

Run these in Windows PowerShell **on THECAULDRON** (not in Termux):

```powershell
$pair = "$env:LOCALAPPDATA\HomeCenter\RitsuPairCampaignSource\source-27b9b384dcb3\tools\campaigns\ritsu-control-pair-campaign.ps1"
$sha  = "27b9b384dcb3ebea4890ef42217f4b02e1016c0c"
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File $pair -Mode Plan
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File $pair -Mode Apply -Revision $sha
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File $pair -Mode Status
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File $pair -Mode Receipts
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File $pair -Mode Stop
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File $pair -Mode Resume -Revision $sha
```

`Apply` persists the run and launches a separate owned Windows PowerShell worker, returning control to the operator immediately. `Status` reports worker liveness, last phase, elapsed time and receipt location. `Stop` targets only the owned worker and its process tree after identity readback; `Resume` explicitly clears a prior stop latch. `Canary` demonstrates isolation and stop without reading a token or sending to a device. `Follow` displays append-only receipts; Ctrl-C detaches only the viewer.

## Pairing ownership, trusted boundaries
- Source of phone-only credential: `HOME_CENTER_RITSU_PHONE_CAPABILITY_FILE` or the existing canonical `%LOCALAPPDATA%\HomeCenter\RitsuE2E\phone-capability.txt`, or operator selects an **existing** token file via local Windows picker. No rotation/generation.
- The GUI shows endpoint `http://100.68.37.106:19646` and a masked phone-only token. The operator can reveal it locally to type into the **Ritsu Control** Android app's **More → Connect Home Center (Tailscale)** dialog. The token never goes into ChatGPT, output, clipboard or campaign receipts.
- The helper validates existing token against the private gateway health endpoint, refuses other host IPs, and does not restart the live gateway. The console may show only a redacted receipt.
- Saving local Android pairing is distinct from verifying physical phone receipt or feedback. A closed Windows dialog records `awaiting_device_verification`, not `paired`.
- Browser-to-Home Center Playwright HTTP smoke remains proven server-side, but real physical Android pairing, Ritsu Control message readback, and sound HEARD verdict remain **NOT VERIFIED**. The live port-19646 service remains unchanged. Do not silently switch the live transport or claim installed/paired phone.

## Test and release states
- Implemented: Yes.
- Exact source staged on Windows: Yes.
- Windows script syntax and process-isolation canary: PASS.
- GitHub Actions Windows contract: PASS.
- Interactive local pairing GUI plus **real phone**: NOT VERIFIED. Requires owner action.
- Playwright live service promotion/Android conversation success: NOT PERFORMED.

## Next bounded action
Owner launches `-Mode Apply` on THECAULDRON, observes the local credential dialog, and enters its values into the actual installed Ritsu Control app. Retrieve `-Mode Status` and `-Mode Receipts` in the same campaign, then verify app connection independently before any change to live Playwright gateway. User confirmation is required for physical app pairing and heard audio.
