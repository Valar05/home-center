# Ritsu Control v0.17, Android phone build campaign

**Authority:** Campaign Etiquette in Google Drive, including the October 25 rules for repo-owned campaigns and self-locating entrypoints. Source: `Valar05/home-center`, branch `campaign/ritsu-local-tailnet-20261024`.

The **runnable campaign is in this repository**, at `tools/campaigns/ritsu_phone_android_v017.sh`. No downloadable ChatGPT launcher is a permitted execution path. The Android phone is the build machine; THECAULDRON is not a Gradle requirement.

## One stable repo-owned entrypoint

From any Termux working directory, invoke the actual file in a **clean, verified** `home-center` checkout:

```sh
bash /storage/emulated/0/Documents/GodotProjects/home-center/tools/campaigns/ritsu_phone_android_v017.sh build
```

This path was an owner-verified Android checkout in August 2026; verify it remains the relevant checkout. The script physically resolves its own path and detects the Git repository root without trusting the caller's `pwd`. Before any build mutation it validates the exact GitHub remote, active campaign branch, pinned Android source tree, and clean Git status. Prints `RESOLVED_REPO`, `EXECUTION_DIR`, `BRANCH`, `HEAD`. **It will not switch, reset, stash, or damage a dirty checkout.** If the existing checkout is on another branch or dirty, use a separate clean Git worktree for this campaign. Follow the same repo-relative invocation targeting that worktree instead. This one-time source checkout is permitted; downloading a script outside the repository is not.

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
