# Ritsu Conversation Usability v1.3.3

Same campaign lineage. This fixes **upstream ChatGPT reply visible but absent from Ritsu** by adding a guarded original-turn browser-to-journal recovery lane and an Android client that requests it by original immutable turn ID and SHA-256. This packet also includes the old, fast exact-file Android `termux-media-scan` immediately after publishing the signed APK to shared Downloads.

## Operator handoff

After downloading the immutable versioned launcher to Termux Downloads, the **one invocation** is:

    bash "$HOME/storage/downloads/ritsu-conversation-usability-v1.3.3.sh"

A separate sha256 guard is supplied in the user-facing handoff. The launcher prints its exact source/version/hash before any mutation. It unpacks a cryptographically verified manifest, runs its bundled host tests, and independently stages all changes. The target source is the previously verified code22 v1.3.1 build; `com.ritsucontrol.fresh` and the approved cert remain pinned.

## Execution order

1. Verify immutable packet; run unit tests and preflight.
2. Isolate the exact accepted Android source and patch in read-only original-turn reconciliation. Build and sign **code24, version 0.19.4**, using the approved existing signer.
3. Through the **existing** Termux `cauldron` command only, stage a checksum-verified Windows packet; validate the uniquely identified running Node service, preserve a source backup, and add authenticated `/v1/ritsu/recover`. The browser helper reads only already rendered signed-in ChatGPT pages/known URL and matches the original prompt's SHA-256. It never clicks Send. Only a uniquely verified complete response is **appended** to the journal with the original turn ID and tab. Windows source/service rollback is attempted if restart or endpoint validation fails.
4. After verified Windows recovery endpoint, publish the already-signed APK atomically to `~/storage/downloads`, verify source/copy SHA-256, run `termux-media-scan "$PUBLIC_PATH"` for the exact APK, and report `COPY_VERIFIED`, `MEDIA_REFRESH`, and `INSTALLATION=NOT_ATTEMPTED` separately.

No user messages are automatically resent. No journal rewrite, pairing/token reset, unrelated repo edit, GitHub write, Home Center, Computer Hands, additional SSH lane, or Android auto-install. If no unique browser reply can be matched (including a response visible only in the separate ChatGPT mobile application), the turn stays unresolved. User-visible recovery acceptance remains pending until device verification.

## Tested vs not tested

Locally tested: Bash parser, archive verification, Python AST/compilation, 20+ bundled host regressions including Java stubs, Node --check of synthetic source patch, simulated cauldron packet transfer boundaries, Downloads copy/scan readback, collision and no-install behavior. **Not live-tested here:** Cauldron transport, PowerShell/Node service restart on Windows, Android code24 Gradle build and signer, Files app visibility, or recovery of the historical waifu/Entourage answer. No success is claimed until the owner obtains runtime receipts.
