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


## Copy-paste runnable GitHub cloud campaign (owner handoff)

The script itself is checked in at `tools/campaigns/ritsu_sticky_cloud_dispatch.sh`.
It verifies the committed Android source, campaign script and registered workflow
against known Git blob IDs, checks `gh` authentication, avoids duplicate
successful same-commit runs, and dispatches `.github/workflows/build.yml`.
It does NOT build locally and does NOT uninstall an app.

To dispatch the cloud workflow from **any** authenticated shell with GitHub CLI
(there is no local checkout prerequisite):

```bash
gh workflow run build.yml --repo Valar05/home-center \
  --ref campaign/ritsu-local-tailnet-20261024
```

The direct command is runnable, but it deliberately omits the additional
source-provenance/idempotence safeguards in the checked-in dispatcher. When a
user specifically asks for a script, provide the entire copyable, executable
source-equivalent code block in the chat response rather than only a link.
The cloud script executes the repo-owned doctor, Gradle unit tests and
`assembleRelease`; the APK remains **unsigned** and no installable upgrade
will be published until signing identity matches the installed Android app.

## One-paste dirty-worktree-safe bootstrap (2026-10-25 owner correction)

**Never ask the owner to `cd` into `GodotProjects/home-center` or `git pull` in it.** That checkout already has three unrelated modified scripts. They stay untouched.

The repository-owned `tools/campaigns/ritsu_sticky_onepaste.sh` uses a verified immutable commit supplied through `RITSU_STICKY_PIN`. It creates or safely reuses an isolated sparse checkout at `$HOME/.local/share/ritsu-campaigns/sticky-<sourceSHA-prefix>`, verifies origin and exact Git HEAD, rejects dirty private campaign checkouts, and executes `ritsu_sticky_campaign.sh doctor`. It requires only Termux Bash, Git, network access to the public GitHub repository, and ordinary private home storage. It assumes nothing about current working directory.

The **one-paste command in the handoff is the source of this repo-owned bootstrap provided inline via Bash heredoc**, not a second external/downloaded launcher. The script's default `doctor` mode **is real and useful** for verifying exact source and platform-independent contracts; it does not compile, sign, install, or publish an APK. The release signing identity remains unresolved, so no installable in-place upgrade is promised.

Cloud CI test job `isolated-bootstrap` in `.github/workflows/build.yml` tests this exact repo-owned launcher against a synthetic preexisting owner's file fixture, from unrelated directories and on rerun, and verifies it never changes those bytes. The existing `sticky-android-compile` job separately assembles unsigned Android v0.18 and executes JUnit tests in GitHub. No owner's local Android SDK or Gradle is required for the default doctor invocation. Physical phone run remains a separate acceptance gate.


## Contingency-tree gate (2026-10-25, owner escalation)

The campaign's actual completion goal is a **compatible, signed, installable v0.18 APK that preserves an existing Android Ritsu install's local data, then passes real phone acceptance**. Source-check and unsigned compile are intermediary engineering receipts, not a deliverable. The owner ran the one-paste script and obtained only STICKY_PREFLIGHT=PASS and APK_RELEASE=BLOCKED_PENDING_EXISTING_SIGNING_IDENTITY. That blockage was foreseeable and should have been accounted for before the handoff, not imposed as a new task on the owner.

**Authoritative machine-readable plan:** tools/campaigns/ritsu_sticky_contingency_plan.json. It explicitly enumerates 15 identified branches including dirty repository, LFS, GitHub or network unavailability, SDK and lint errors, protected signing key availability and mismatch, version or package mismatch, missing/recoverable/irrecoverable signer, migration and re-pairing, non-destructive installation failure, rollback, device/runtime test, and partial run reconciliation. Every branch contains detection, safe automated recovery, responsibility, and fail-closed behavior. Test tools/campaigns/validate_ritsu_sticky_contingencies.py is part of build.yml's release-contract gate.

**Current evidence:** GitHub compile, Android tests and isolation/bootstrap succeeded; **installed package signing metadata, compatible retained signing key, installable upgrade, APK delivery and phone data retention remain UNKNOWN/NOT_RUN.** Do not ask the owner to run the old doctor again. The operator first attempts to verify existing signing authority via connected GitHub protected secret metadata, earlier signing provenance and approved phone device information; if matching key exists use a persistent secure signer, then build and sign cloud APK and verify before direct handoff. If key only exists on an authorized device, request approval for a narrowly scoped device signing operation, without exporting secrets through ChatGPT. If irrecoverably unavailable, keep existing app untouched; offer a deliberately separate signed package plus explicit, consent-based import/export or re-pairing, clearly noting that Android Keystore secrets cannot silently migrate to a new package.

**No fake end-to-end:** Until the signer or an owner-authorized migration route is resolved, label this campaign COMPLETION_BLOCKED. Preflight passed, but the original objective did not. Never represent a basic diagnostic script as its replacement.

## 2026-10-25 copy-only Downloads handoff (owner field correction)

The native phone build and local signing are separate completed stages. **Do not rerun Java/Gradle, rebuild, re-sign, fetch source or open the Android package viewer merely to save a finished APK.** The owner specifically wants the signed `.apk` deposited in Android's actual Download directory; `termux-open` is not a save operation and did not provide a usable file handoff.

Canonical entrypoint: `tools/campaigns/ritsu_sticky_copy_to_downloads.sh`, invoked from any shell directory. It locates the signed local artifact in `$HOME/.local/share/ritsu-sticky-release/Ritsu-Sticky-v0.18.0.apk` (or the historical `$HOME/.cache/ritsu-sticky-v018/Ritsu-Sticky-v0.18.0-<sha>.apk`, or explicit `RITSU_STICKY_SIGNED_APK`), validates archive/integrity, checks signing and Android manifest when corresponding tools are available, and copies to `$HOME/storage/downloads` or `/storage/emulated/0/Download`. It uses a temporary file, checks sizes and SHA256 after copying, preserves any differently hashed existing file with a distinct hashed filename, and prints the **actual Downloads path and COPY_VERIFIED=PASS**. It never opens, installs, deletes, clears data or touches the original Git worktree. Existing key/cert remain private. If the shared Downloads directory is not accessible, report Termux storage permission rather than claiming the file was saved.

The signing helper `ritsu_sticky_install_real.sh` has been updated to call this copy-only delivery script instead of auto-launching `termux-open`. The copy script is independently runnable against **already-produced** signed APKs. Cloud regression tests `ritsu_sticky_copy_to_downloads.test.sh` exercise repeat copy, preexisting filename conflict, missing source and SHA mismatch without needing access to the owner's phone. A green cloud test still does not establish a file has been placed on the physical phone. Owner can open Files > Downloads on Android after COPY_VERIFIED=PASS.

Full observed incident and lessons are in the live [Campaign Etiquette](https://docs.google.com/document/d/1wntegQjw7238dmGqbvs9TQmlsp4uXdXw7_wPciNx6sI/edit), section **Ritsu Sticky End-to-End Android Campaign Incident and Downloads-Only Handoff**.
