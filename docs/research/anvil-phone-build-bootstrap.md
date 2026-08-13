# Anvil Shell primary-phone build bootstrap research

Date: 2026-08-13  
Scope: the typed `PHONE_MAINTENANCE` build/install operation for `Valar05/continue-continue@7e0e949ba3e3aefa8df608226086b6273cfb16ca`.

## Ruling

The phone executor must not depend on whatever Gradle or Android SDK happens to be present. It now uses fixed source identities and rejects caller-controlled commands, argv, URLs, and paths.

## Pinned inputs

| Input | Identity | Digest |
|---|---|---|
| Gradle binary distribution | `https://services.gradle.org/distributions/gradle-8.13-bin.zip` | SHA-256 `20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78` |
| Android SDK Platform 36 revision 2 | `https://dl.google.com/android/repository/platform-36_r02.zip` | SHA-256 `37607369a28c5b640b3a7998868d45898ebcb777565a0e85f9acf36f29631d2e`; Google repository SHA-1 `2c1a80dd4d9f7d0e6dd336ec603d9b5c55a6f576` |
| Android packaging binary | signed Termux `aapt` package, phone-local `aapt2` | exact package metadata and bootstrap-output digests recorded by the terminal receipt |
| APK signer reader | signed Termux `apksigner` package | exact package metadata and signer digest recorded by the terminal receipt |
| Java | signed Termux `openjdk-21` package | version and package metadata recorded by the terminal receipt |

## Structural findings

- The current official Termux Gradle package tracks Gradle 9.7 and depends on OpenJDK 21. Anvil's repository checkpoint is tested with Gradle 8.13, so the maintenance executor downloads the exact Gradle 8.13 distribution and verifies its SHA-256 instead of accepting the moving package version.
- Google's platform archive is pure Java/XML and can be used on ARM64 Android. The executor installs it under its owned toolchain root and verifies the published transparency-log SHA-256 before extraction.
- Android Gradle Plugin normally selects a Maven-hosted desktop `aapt2`. The executor passes the phone-native Termux `aapt2` path through the fixed `android.aapt2FromMavenOverride` property.
- Silent package install may be denied to the Termux UID. The executor tries ordinary `pm`, then a fixed Shizuku/rish `pm install` against a source-head-derived shared APK path, then fixed `adb install`. It does not open an installer UI or silently cross into `PHONE_INTERACTION`.
- A build is not accepted until the built APK hash, certificate digest, installed APK hash, package id, version name, rollback observation, and package-manager readback agree.

## Primary sources

- Termux Gradle package: https://github.com/termux/termux-packages/blob/master/packages/gradle/build.sh
- Termux Android packaging tools: https://github.com/termux/termux-packages/blob/master/packages/aapt/build.sh
- Termux APK signer package: https://github.com/termux/termux-packages/blob/master/packages/apksigner/build.sh
- Gradle distributions and checksum publication: https://services.gradle.org/distributions/
- Gradle checksum guidance: https://docs.gradle.org/current/userguide/best_practices_security.html
- Android platform package identity: https://github.com/dotnet/android/blob/main/Documentation/workflow/HowToAddNewApiLevel.md
- F-Droid Android SDK transparency log: https://gitlab.com/fdroid/android-sdk-transparency-log/-/raw/master/checksums.json
- Termux on-device build constraints: https://github.com/termux/termux-packages/wiki/Build-environment

## Capability state

This research justifies implemented bootstrap source. It is not a phone toolchain receipt, build receipt, deployment receipt, installation receipt, delivery, or acceptance.
