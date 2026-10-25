# Ritsu Control Sticky Snippets campaign

## Feature semantics

Each conversation tab has a persistent editable Sticky text field. The Sticky button appears in the conversation selector row. The text stays tied to the tab ID; changing machine, channel, or switching tabs does not replace it. Every typed AND spoken turn snapshots the currently saved tab text before it is durably queued. The direct Tailscale outbox sends those exact queued bytes on the existing local route; retrying a turn does not duplicate sticky context. This is explicit user context repeated on each turn, not higher-priority system text and not a guarantee an AI or browser worker obeys it.

Quick named snippets are stored in the application and available from the Sticky dialog's Insert saved menu; inserting appends to the editor rather than replacing existing text. Save quick adds a named reusable entry. Save the current sticky text to a user-picked .txt document with Export .txt, or append contents of a user-picked text file with Import .txt. Android's Storage Access Framework lets the owner select Documents or Downloads, with an independent file surviving an app uninstall. Quick library entries themselves remain in app storage until exported. No migration of protected app pairings is claimed.

## Repository-owned campaign

- Script: tools/campaigns/ritsu_sticky_campaign.sh
- Compile action: .github/workflows/build.yml (manual workflow dispatch, GitHub cloud).
- Existing safe signing contract: tools/campaigns/ritsu_release_cloud.sh and its contract/test. This is not a substitute for protected signer enrollment.
- Tests: android/ritsu-control/app/src/test/java/com/homecenter/ritsucontrol/StickyTextTest.java.
- Build target: Android 35, Java 17, Gradle 8.11.1, app ID com.homecenter.ritsucontrol.phone, versionCode 19, versionName 0.18.0.

The operator reads the current live Campaign Etiquette document first, authors and verifies GitHub source, dispatches build.yml using the connected GitHub admin tool, reads the job logs, and handles the APK when a durable compatible signing identity has been proven. No owner Termux command or standalone file download launcher is needed to compile.

## Release and identity protection

The campaign builds and tests an unsigned release package to validate source without publishing a misleading installable update. The installed Ritsu app package and signer fingerprint are currently unknown. In-place upgrades require matching package and signing certificate (or valid signing lineage), plus a higher versionCode. The runner-generated v0.17 debug signer is not known to be durable. The owner must not uninstall any old app as a workaround. A future installable v0.18 APK is blocked until a protected signer matching the actual target app has been established and the signer-gated GitHub release job has passed. Android phone install, data retention and actual speech/streaming remain separate human/device evidence.

## Scope and acceptance

Cloud evidence can prove compilation and unit tests, not runtime UI interaction or whether an AI followed the repeated context. On a real phone verify tab switch isolation, editing/clearing/persisting sticky text, app restarts, import/export, repeated typed and voice sends, no double-appending on retries, and no lost pairing/history. Independent export files can be recovered with Android Files. Review URL: no hosted native Android preview exists for this feature.
