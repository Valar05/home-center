# Project Manifest: home-center

- Generated: 2026-06-20T17:00:50-05:00
- Workspace path: `/storage/emulated/0/Documents/GodotProjects/home-center`
- Git repository: yes
- Git remote: `https://github.com/Valar05/home-center.git`
- Orientation: `PROJECT_ORIENTATION.md`

## Purpose Snapshot
> # Home Center Orientation
> Home Center is a Java Android app built directly with Gradle from Termux. It is not a Godot project.
> ## Entry Points
> - App id: `com.dclar.homecenter`
> - Activity: `app/src/main/java/com/dclar/homecenter/MainActivity.java`
> - Voice parser: `app/src/main/java/com/dclar/homecenter/CommandParser.java`
> - Home Center sync client: `app/src/main/java/com/dclar/homecenter/HomeTaskClient.java`
> - Legacy TickTick client: `app/src/main/java/com/dclar/homecenter/TickTickClient.java`
> ## Build
> Use SDK 33 on this phone. Newer SDK resources have failed with the Termux ARM64 toolchain, so keep compatible dependency pins unless the local Android SDK/aapt2 setup changes.
> For the slice-one chat UI and Cartesia proxy, add the config to `local.properties`:

## Entrypoints And Validation Clues
- No standard entrypoint was detected. Inspect top-level files and add project-specific validation commands when known.

## Top-Level Inventory
- `.android-sdk/`
- `.firebaserc`
- `.firebaserc.example`
- `.gitattributes`
- `.githooks/`
- `.gitignore`
- `.gradle/`
- `.tmp/`
- `agent-tools/`
- `app/`
- `build/`
- `build.gradle`
- `docs/`
- `firebase/`
- `firebase.json`
- `gradle.properties`
- `local.properties`
- `PROJECT_ORIENTATION.md`
- `README.md`
- `settings.gradle`
- `tools/`

## Git Hygiene
- `.gitignore` contains a Codex workspace hygiene block for credentials, caches, and local build outputs.
- `.gitattributes` contains a Codex Git LFS block for common binary assets, models, audio, video, archives, fonts, and PDFs.
- `git lfs install --local` was attempted for this repository during the manifest pass.

