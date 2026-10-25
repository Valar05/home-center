# Ritsu Control APK continuity and cloud release

## Safety status (2026-10-25)

The GitHub debug APK for v0.17.0 (`com.homecenter.ritsucontrol.phone`, versionCode 18) was built and verified on run 40196659002, but that runner used a disposable debug signer. It was NOT an in-place upgrade release. Do not uninstall any existing Ritsu app to work around an Android signing rejection. The older package identities (`.live`, `.connected`, `.bridge`, `.campaign`, `.outbox` or base package) can coexist with the `.phone` package, but Android does not transfer their private preferences, AndroidKeyStore-protected pairings or messages across package IDs.

**The stable release is NOT READY yet.** The protected reusable Ritsu keystore, its locked fingerprint, and the actual installed phone application's package/certificate/version are not yet established. The release script is committed at `tools/campaigns/ritsu_release_cloud.sh`, with offline syntax/guard tests and a JSON contract, but has not yet passed a full cloud release and cannot truthfully be advertised as a tested data-preserving upgrade. The existing successful `build.yml` trial workflow still publishes disposable debug-signed APKs; it must not be presented as the stable updater. Do not dispatch an upgrade until the stable workflow wiring and authorized protected signing identity are confirmed.

## Required release workflow

Use the current live Campaign Etiquette document first (October 25 Cloud-First and APK Update Continuity gates). Commit the actual runnable release script and contract into this Git repository. GitHub Actions is the executor. The signed release uses a durable keystore stored in protected GitHub Actions credentials, not plaintext repository content or Actions artifacts. The protected signer fingerprint is public provenance and must be locked; mere reuse of package ID is insufficient.

The release entrypoint checks the actual package, installed certificate SHA-256 and versionCode before claiming an upgrade. For an existing app, the output must retain the same package ID and signing certificate or valid lineage, and have higher versionCode. The build uses an unsigned Android release output and signs only with the retained key. The script records the SHA of the Git source, APK digest, signing fingerprint, version and the unverified physical-device data-retention status. Any missing signer, mismatch, version regression or unknown installed identity stops release; it never instructs the owner to erase app data.

After GitHub completes tests and APK verification, deliver the actual APK as a ChatGPT attachment so it can be saved to Android Downloads. Physical no-uninstall installation plus persistence of pairings, saved messages, outbox and settings remains owner/device acceptance. If another package ID is installed, plan an explicit authorized migration or preserve the previous app unchanged. Do not imply an automatic migration of Android Keystore-sealed data.

## Genuine remaining prerequisites

1. Establish the signing certificate and versionCode of the specific installed Ritsu app to be updated, without uninstalling or exposing connection tokens.
2. Secure one durable signing key that matches that existing certificate. If unavailable, acknowledge that seamless in-place upgrading that package is not currently possible; a separate package or explicit migration is required.
3. Wire the protected signing identity into the registered GitHub Actions release workflow and run its syntax/contract preflight and signed APK build. Never silently fall back to debug signing.
4. Deliver the verified APK and preserve the source commit, signing identity, hash, install and retention receipts.

**Avoid a false success claim:** the script/contract are committed, but the stable release job and physical data-continuity acceptance are not yet complete.
