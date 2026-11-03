# Ritsu Conversation Usability v1.3.5

Same immutable campaign lineage. Reconciles code24 source and Windows delivery through one guarded Termux launch, not a diagnostic ladder. **This source packet is a field candidate, not a claim of a repaired app on the user's phone.**

## Corrections

1. The MainActivity conversation view scrolls to the newly created user bubble when the owner explicitly presses **Send**, even when Gboard changes the viewport. Unsolicited replies continue preserving a reader's scroll anchor.
2. RitsuConversationLinks accepts both standard `/c/uuid` and the exact owner-copied `/c/local-chatgpt%3Auuid` as *candidates*. It does not blindly treat either as writable. The approved laptop Chrome page must retain that exact URL, remain signed in and expose the composer before the immutable tab binding is saved. No guessed ID or cross-account fallback.
3. The old `IllegalStateException` collapses into human-readable `CATALOG_HTTP_<status>_<safe_reason>`. A guarded catalog route now supplies top-level verified, non-project sidebar recents only. When the Chrome DOM cannot prove this, it returns a specific error instead of a fabricated empty recent-chats list.
4. Android `LOCAL_UNCERTAIN` journal audits no longer block the **outgoing message executor**. They run independently. A verified server `no_server_receipt` plus unchanged complete journal may accurately show an original turn as not accepted; no automatic resend.
5. The Windows stage can add `/v1/ritsu/recover` if it is absent and catalog/bind routes even when the earlier recovery patch is already present. It never uses hidden ChatGPT APIs or resubmits any existing prompt. Only a unique browser-rendered completed answer may be *appended* to the immutable original journal.
6. Code25 is compiled and signed with the existing Fresh cert from the prior signed code24 source. After successful validation the APK is atomically copied to Android Downloads, SHA-verified, and scanned via **`termux-media-scan "$PUBLIC_PATH"`**, one published file at a time. The script **never** invokes the Android installer.

## One launch, after acquiring the exact versioned file

`bash "$HOME/storage/downloads/ritsu-conversation-usability-v1.3.5.sh"`

Use the exact SHA-256 provided in the final handoff for a first-invocation guard. Source packets under `~/.local/share/ritsu-usability-packets/v1.3.5` are immutable by digest, and the campaign retains all prior receipts in `~/.local/state/ritsu-conversation-usability/runs`.

## Limitations that must remain visible

- Actual Phone/Termux Gradle build, Windows PowerShell, already-authenticated Chrome profile, Files index and any recovered waifu/Manny result cannot be field-tested from this chat. Host fixtures are not physical proof.
- A Drive request works only if the exact signed-in ChatGPT browser session can actually access the document. The campaign does not fabricate a Google Drive connector or cross-account file permissions. Browser worker tool calls or remote document failures may remain unresolved, with original turns preserved and no automatic repost.
- Existing `local-chatgpt` URLs may be local session identifiers with no persistent equivalent on the laptop. The client now permits the *candidate* but the browser must verify it before showing a linked chat.
- The current Pocket voice/Termux receiver is preserved. This revision does not claim full >450-character speech-unit support or owner HEARD acceptance.
- No GitHub repository write was authorized. This packet is not claimed to be committed, and does not modify the owner's dirty checkout. Only the approved `cauldron` command-string execution lane is used for Windows.
