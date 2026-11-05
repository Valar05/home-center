# Ritsu Control native Home Center sign-in (2026-10-24)

## User's requirement
Stop asking the owner to paste a six-digit code between ChatGPT, Termux, and Ritsu Control. The code is short lived but **embedding a shared pairing code inside any distributable APK does not protect it from extraction within its ten-minute window**. The app should initiate and finish its own Home Center authorization, with normal owner sign-in.

## Implementation: version 0.11.0
- `android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/HomeCenterOAuth.java`: native public OAuth client registration with Home Center, PKCE S256, one-time state, ephemeral code verifier, ten-minute login window, system browser, callback parsing, Home Center `/oauth/userinfo` identity verification, no reusable token in source or APK, optional refresh using owner-specific client ID.
- `MainActivity.java`: **More → Connect Home Center account**. Opens the system browser, waits for `ritsucontrol://oauth/callback`, validates PKCE-bound state and credentials, verifies the Home Center owner and saves via Android Keystore. No legacy old-app/Termux steps. Cancelled browser logins are retryable.
- `HomeCenterCloudPairing.java`: Keystore AES/GCM encrypted credentials now retain per-install OAuth client ID and native refresh path.
- `AndroidManifest.xml`: exported BROWSABLE callback with application-private state+PKCE guard, cleartext disabled.
- `app/build.gradle`: v0.11.0, standard appId `com.homecenter.ritsucontrol`; opt-in parallel build uses `-PritsuParallelInstall=true` and alternate appId `com.homecenter.ritsucontrol.connected`, launcher name `Ritsu Control (Connected)`.
- `.github/workflows/ritsu-control-contract.yml`: compile and test standard Android app; verify callback, security boundaries and no manual code UI; upload standard APK; build and verify the separate-package APK with Android aapt; upload separate artifact.

## Live Home Center OAuth server preflight
Read-only confirmation on THECAULDRON of the public Home Center OAuth authorization metadata:
- Issuer `https://homecentermcp-vxybsaualq-uc.a.run.app`
- `/oauth/register`, `/oauth/authorize`, `/oauth/token`
- `code_challenge_methods_supported` includes `S256`
- `/oauth/userinfo` exists in deployed source and authenticates bearer with per-install client ID.

## Boundaries and statements NOT to overclaim
- Android Gradle compilation and GH Actions tests validate code, not owner browser completion on a real handset.
- Native OAuth account sign-in is distinct from Home Center → ChatGPT reply delivery. `HomeCenterSync` currently displays `Home Center cloud paired; conversation bridge not deployed` and does not forward conversation traffic.
- Older debug APKs use different signing keys. The **standard** v0.11 APK cannot upgrade older debug builds in place when signatures differ. Never instruct uninstallation without checking whether the owner needs preserved conversations/settings.
- **Parallel** v0.11 APK installs alongside the old package, preserves old private data on disk, but does not automatically import it. Its separate app identity prevents an Android signature collision.

## Owner verification after installing
Open `Ritsu Control (Connected)` if using parallel APK. More → Connect Home Center account → complete browser login → return to the app. It should show `Home Center connected` and clarify conversation reply channel remains to be deployed. A successful build is not proof that the owner logged in or the phone has exchanged a ChatGPT turn.

## Security
No private Home Center access token, refresh token, Google OAuth client secret or owner password baked into APK. Callback code, client ID and S256 verifier bind the one-time OAuth state. Long-lived refresh token only after owner sign-in, encrypted with Android Keystore and stored in app-private preferences. A ten-minute expiry is for the pending login, not the lifecycle of the renewable session.

## Final verified Android build
- GitHub Actions build **PASS**: https://github.com/Valar05/home-center/actions/runs/40059842092 (source commit `111aea3e06516fe0c38941194cb2dd747ac0bf7d`)
- Default `com.homecenter.ritsucontrol` APK artifact `12547365270`.
- Parallel `com.homecenter.ritsucontrol.connected` APK artifact `12547160921`; aapt package readback PASS, actual APK manifest contains UTF-16 encoded package ID and launcher label `Ritsu Control (Connected)`.
- Parallel APK SHA-256 `267128d00f33594da7383913715854d98aac7dc296860b95cc348a27c02aa0e6`, 63,365 bytes, APK V2 signature present.
- Original v0.10.1 debug signer fingerprint `01cb5ea5f3ff303330740a95f226e738edc5906754e2ad82906ca67505f62ce2`; v0.11 standard initial build signer `0994610dc28d8336018e50c42bbb3d66e35cbf9036bf968f1dbd8b05df6a4175`. Existing v0.10.1 cannot upgrade in place; **parallel edition** is the safe installation choice.
- Live OAuth metadata preflight on THECAULDRON confirmed issuer, register, authorize, token paths and PKCE S256. Physical device browser login/receipt is still **unverified**.
