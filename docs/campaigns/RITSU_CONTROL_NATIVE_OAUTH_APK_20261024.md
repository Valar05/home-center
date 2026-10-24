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
