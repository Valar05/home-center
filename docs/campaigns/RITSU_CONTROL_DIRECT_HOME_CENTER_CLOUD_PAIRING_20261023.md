# Ritsu Control: Direct Home Center cloud pairing (2026-10-23)

## Owner's corrected target
**Pair the NEW Ritsu Control Android app to the ACTUAL Home Center cloud service, NOT to THECAULDRON / Windows / Tailscale port 19646.** Earlier replies repeatedly misinterpreted the target. An older Home Center Android app can approve owner-initiated Home Center pairing challenges.

## Authoritative existing cloud contract (verified source)
- Deployed Home Center cloud base `https://us-central1-home-center-dclar.cloudfunctions.net`.
- `functions/index.js`: `termuxPairingStart` (creates pairingId + 6-digit code; 10-minute TTL), `termuxPairingApprove` (requires signed-in Home Center owner, approves code), `termuxPairingPoll` (returns Home Center bearer/access + refresh credential after approval), `termuxTokenRefresh`, `termuxHubTools` (authenticated readback).
- Older app's UI calls pairing approval `Pair Termux Codex`, though request now identifies itself as clientKind `ritsu-control-android`; no PC or Tailscale required.
- Cloud Home Center reports owner-scoped `primary-phone` and `primary-phone-rescue-v1` registrations, but heartbeats are **stale**. An old registration is not Ritsu Control's cloud pairing.
- Existing Home Center OAuth pairing grants the owner-approved safe groups `drive/docs/github`, not a new restricted Ritsu chat scope. Re-evaluate least-privilege before promoting cloud conversation features.

## Implementation staged
- `android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/HomeCenterCloudPairing.java`: direct fixed HTTPS pairing start/poll, authenticates with Home Center `termuxHubTools`, keeps separate AES-GCM Android Keystore encrypted bearer + refresh credentials and refreshes via the deployed cloud endpoint.
- `MainActivity.java`: **More → Pair with Home Center (cloud)**; displays pairingId/code for owner approval in the existing Home Center app; bounded asynchronous poll; cancel/disconnect stops poll.
- `HomeCenterSync.java`: **cloud only**; never auto-falls back to the legacy desktop gateway and never falsely announces a delivered conversation. States distinguish `cloud not paired`, `cloud paired; conversation bridge not deployed`, and `cloud session needs re-pairing`.
- `android/ritsu-control/app/build.gradle`: version 0.10.0 / versionCode 10.
- `.github/workflows/ritsu-control-contract.yml`: Android Gradle unit build/assembleDebug and cloud-pair/no-PC source checks; `ritsu-control-v0.10-home-center-cloud-pairing-debug-apk` as artifact.
- Latest source commit for the pairing patch: `c07a788ad5813754038d38f3780661ddc4a9b428` on `feature/ritsu-command-bridge-scavenge-20261022`. Earlier commit `2f17424d4a889ff0828574668acca8721a9af859` passed CI but lacks a last-minute cancel-before-poll guard; prefer the latest source's CI-produced APK.
- NO user-side pairing attempt was made and NO production cloud or Windows gateway was modified. Physical-device approval is a required user consent action and proof is pending.

## Usage after v0.10 APK installation
1. Open Ritsu Control → More → **Pair with Home Center (cloud)**.
2. It shows the Home Center pairing ID and six-digit code.
3. In the already-installed OLD Home Center app, choose **Pair Termux Codex**, enter pairing ID and code, approve the request.
4. Return to Ritsu Control; it verifies the cloud credential and stores it with Android Keystore. Check the distinct status `Home Center cloud paired; conversation bridge not deployed`.
5. **Do not call a Git SHA, a CI APK build, a localhost gateway health result, or an approval code paired.** Only a physical-app acknowledgment after Home Center cloud verification counts. Cloud ChatGPT turn/feed transport is not deployed by this pairing patch.

## Important installation caveat
GitHub-hosted Android debug builds may use different debug signing keys from prior runs. A device with v0.9 already installed may reject v0.10 as an update due to signing certificate mismatch. **Do not automatically uninstall or clear Ritsu Control's existing local conversations/preferences.** Preserve data first or establish compatible update signing.

## After owner approval
The next slice is a cloud-owned Ritsu Control conversation API/relay that binds Home Center to the already proven Playwright reply path, with explicit delivery receipts, rather than routing the Android app to THECAULDRON's IP directly. Pairing and chat delivery are separate milestones.
