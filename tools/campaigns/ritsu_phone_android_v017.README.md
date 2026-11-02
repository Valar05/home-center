# Ritsu Control v0.17, Android phone build campaign

## Current authority: GitHub Actions first (2026-10-25)

The owner's latest Campaign Etiquette Google Doc is authoritative. **GitHub
Actions is now the default for Android Ritsu builds.** The historical
Termux-private AAPT2 campaign documented below remains a *fallback only*,
not the expected user workflow. Do not ask the owner to run the pasted
Termux commands below when a GitHub Actions workflow can build the APK.
Do not execute the phone-local build unless GitHub is proven unavailable
and the owner specifically authorizes that exception.

Default cloud workflow is the existing registered `.github/workflows/build.yml`
manually dispatched at branch `campaign/ritsu-local-tailnet-20261024`.
It builds `-PritsuPhoneInstall=true` with SDK 35 and Gradle 8.11.1,
tests, verifies the application ID and debug APK signature, and publishes
artifact `ritsu-control-v017-phone-apk` with APK, SHA256 and receipt.
The owner must receive the actual verified APK as a chat attachment
instead of a ZIP-only workflow link when supported. Installation and
physical Android Downloads evidence remain a separate user/device gate.
Workflow run #40196443188 failed because full checkout changed malformed
unrelated LFS video files; subsequent workflow commit
`cdb33fa61cbd6c8a3e66b054cccc2641ef430827` uses Android-only sparse
checkout to prevent that unrelated failure.

**Fresh-read lock:** each agent/worker must fetch the current
[Campaign Etiquette document](https://docs.google.com/document/d/1wntegQjw7238dmGqbvs9TQmlsp4uXdXw7_wPciNx6sI/edit)
before new campaign work and after context/handoff changes. See AGENTS.md.
GitHub Actions usage may be subject to repo-plan minutes/storage; do not
promise unlimited free builds.


**Authority:** Campaign Etiquette in Google Drive, including the October 25 rules for repo-owned campaigns and self-locating entrypoints. Source: `Valar05/home-center`, branch `campaign/ritsu-local-tailnet-20261024`.

The **runnable campaign is in this repository**, at `tools/campaigns/ritsu_phone_android_v017.sh`. No downloadable ChatGPT launcher is a permitted execution path. The Android phone is the build machine; THECAULDRON is not a Gradle requirement.

## One stable repo-owned entrypoint

From any Termux working directory, invoke the actual repository file in the
**dedicated source checkout created by the 2026-10-25 one-shot command**:

```sh
bash "$HOME/.local/share/ritsu-campaigns/v017-home-center-repo/tools/campaigns/ritsu_phone_android_v017.sh" build
```

The earlier guess `/storage/emulated/0/Documents/GodotProjects/home-center`
was **not present** on the owner's phone. Never give that path as the default or
imply it was verified. On a new device, establish the dedicated checkout from
the pinned GitHub commit before invoking the repo-owned entrypoint. The script physically resolves its own path and detects the Git repository root without trusting the caller's `pwd`. Before any build mutation it validates the exact GitHub remote, active campaign branch, pinned Android source tree, and clean Git status. Prints `RESOLVED_REPO`, `EXECUTION_DIR`, `BRANCH`, `HEAD`. **It will not switch, reset, stash, or damage a dirty checkout.** If the existing checkout is on another branch or dirty, use a separate clean Git worktree for this campaign. Follow the same repo-relative invocation targeting that worktree instead. This one-time source checkout is permitted; downloading a script outside the repository is not.

Modes: `doctor`, `build`, `resume`, `status`. The separate repo-owned lint/test entrypoint is `bash tools/campaigns/ritsu_phone_android_v017.test.sh`. It invokes `bash -n` and validates fail-closed wrong-location behavior. Check `ritsu_phone_android_v017.contract.json` for source identity, writable surface, dependencies, and acceptance.

## Build and recovery

Only these paths are mutable: the isolated `$HOME/.local/share/ritsu-campaigns/v017-phone` build/cache/workspace and documented toolchain, Android SDK 35 if missing, and final phone Downloads APK. Git source files are SHA verified. Termux's older Play Store AAPT2 cannot link Android 35 framework resources. The script fetches newer signed upstream Termux aapt2 and ABI-matched Protobuf/Abseil dependencies into the campaign-local folder. `LD_LIBRARY_PATH` is set **only for AAPT2**, never globally, and an actual SDK35 resource-link smoke test must pass before Gradle. Preserve existing source/cache for reruns.

An APK is **not** proven by a shell syntax pass, verified source count, signed APT index, or a build task starting. Continue only when Gradle tests, assembly, APK signature, physical install, direct Tailscale Send/partial/final, and owner acceptance have separate receipts.

## 2026-10-25 failure and repair

The v6 ChatGPT Downloads launcher sourced an old canonical revision that contained a Bash syntax error: a `>>` redirection was split after the operator. That revision never reached dependency download. The repo-owned script has been corrected to place the redirection and destination together. Never hand out another standalone launcher; advance by updating the Git-owned campaign and read back the new exact revision. Do not assume the user's currently selected Godot project directory is the campaign checkout.

No physical APK acceptance has yet been obtained.

## 2026-10-25 ABI dependency-stage silent exit recovery

The owner ran the pinned repository-owned campaign and confirmed successful signed
APT retrieval of `abseil-cpp 20260817.0`, `libprotobuf 2:36.2-1`, and
`fmt 1:12.2.0`. The shell then exited without printing the next package
(`libc++`) or an error; the receipt remained `SOURCE_VERIFIED`. **The exact
failing command is not yet proven.**

The repair does not throw away those cached packages or switch to desktop.
It removes the early-exiting `awk` from the APT version-query pipe while
`pipefail` is active, captures complete APT policy output first, and reports
`AAPT2_ABI_RESOLVE`, `AAPT2_ABI_DOWNLOAD`, `AAPT2_ABI_EXTRACT`, and
`AAPT2_ABI_READY` stages. A top-level ERR handler writes the exit code,
line number, and named phase to the campaign receipt if any unhandled command
fails. The repo test suite guards against regressions in this error path.
Continue with the same pinned repo-owned campaign entrypoint after updating
its isolated clean checkout; always run `ritsu_phone_android_v017.test.sh`
before the build. Signed APK and physical test remain **unverified**.

## 2026-10-25 mandatory phone Downloads delivery + test assertion fix

The physical user run printed `BASH_SYNTAX=PASS` and `CONTRACT_JSON=PASS`,
then stopped before calling the Android build. Root cause was a stale brittle
`grep -Fq` assertion for an outdated literal AAPT download command in the
repo-owned test script; `set -e` caused an unexplained exit. The test now
reports named missing guards and checks semantically relevant ABI stage and APK
publication markers, instead of insisting on obsolete shell source spelling.

Gradle output under the private campaign workspace is **not acceptance**. After
unit tests and assemble pass, the campaign verifies `app-debug.apk` signature
and ZIP integrity, copies it to the Android **shared Downloads** directory via
`$HOME/storage/downloads`, verifies the copied SHA256 and signature, and only
then publishes `Ritsu-Control-v0.17.0-Phone-Local.apk` there. It reports
`DOWNLOADS_APK_VERIFIED`, `DOWNLOADS_APK_SHA256` and `DOWNLOADS_APK_BYTES`
before recording `BUILD_PASS`. Existing valid APKs are not replaced until the
incoming APK passes staging validation. If Downloads is unavailable, the run
fails explicitly instead of claiming a finished deliverable.

Visible in Android Files / Downloads as **Ritsu-Control-v0.17.0-Phone-Local.apk**.
The repository source remains pinned and the app's on-device acceptance remains
separate from successful binary delivery.
