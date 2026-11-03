# Ritsu Conversation-First Usability v1.3.1

One versioned release packet, one Termux invocation, one terminal receipt. This packet is a *source-backed campaign implementation*, not evidence of installation or owner acceptance.

## Contract

- Preserve the owner-accepted Ritsu Fresh v0.19.1/code21 APK signing identity and all existing data, OAuth callback, pairing and conversation ledger.
- Find **exact** source associated with signed 0.19.1 SHA-256 `9d825b5471e9b13cf9d3ba1bdd50d7c3cf647f7076f289bb2729791ba0f710bf`. No silent fallback to the old 0.18 project.
- Stage Android source changes in an isolated copy. Keep previously accepted CampaignActivity and supervisor engine.
- Replace enormous dashboard with compact header, single horizontally scrolling tab strip and one vertically scrolling chat. Drawer contains conversation library and existing advanced controls. Close UI tab != archive != delete != remote Chrome tab. Store per-chat reading anchor and composer draft; never resend an uncertain turn.
- `Discover recent` attempts only positive, read-only non-project recent ChatGPT sidebar links from the signed-in Playwright context. On uncertain DOM, return no suggestions. `Add URL` supports exact personal `https://chatgpt.com/c/...` URL binding, which validates a writable editor without sending. Preserve browser state and provenance. Local archive is local only.
- Implement optional per-chat Pocket speech for *future* verified complete turns through **existing** pinned Windows sender and 19643 phone relay. Speaker requires exactly installed sender SHA-256 `3dda464df8d5e24d29db471df7c7b8d70d28741c98866996a980afe5443c6ad8`. Only 1 complete <=450-character unit per existing sender invocation; never slice, truncate, silently drop or re-send an uncertain ticket. Long arbitrary replies must be marked **not fully speakable** until the author/agent can provide complete semantic units. This release does **not** claim full long-form speech acceptance.
- All Windows changes pass through the already installed `cauldron` Termux command string. The Windows backend is patched only after isolated source syntax and Android release build succeed. Back up backend source, reconcile journal, restart only the verified original Ritsu Node process using its exact executable, script, port and bind identity, following the previously accepted SSE v4 restart method, and roll back on restart failure. Never use Home Center, Computer Hands, GitHub writes or a new SSH route.
- Print startup/version/progress/heartbeat/final diagnostics from the first run. Publish a signed APK only after source, Node and Android guards pass. Owner separately approves installing the APK. Do not install or replace installed apps automatically.

## Evidence truth

Tested here: Python AST, Bash syntax, Node syntax, synthetic anchored Android and backend source patches, generated packet transport command size for every chunk, packet manifest and self-extractor. **NOT tested here**: Android Gradle on the actual phone, the *real installed* v0.19.1 source (may differ from historical GitHub), actual Windows PowerShell/Playwright DOM, Tailscale/paired binder, Pocket HEARD or phone screenshot. No green host-test badge replaces these gates.

## Canonical research

- Campaign Etiquette https://docs.google.com/document/d/1wntegQjw7238dmGqbvs9TQmlsp4uXdXw7_wPciNx6sI/edit
- Plan v1.2 https://docs.google.com/document/d/1GFI1RXCk9K0MWInwTAGd57i4J7iXhkki_fGLaFpDqQA/edit
- Ritsu master https://docs.google.com/document/d/17wtsd0OaIl_ia7P2ga_67hRAImQvDc3bjO1Xt_9Sz14/edit
- Pocket continuity https://docs.google.com/document/d/1okcl-v7CcaEnZruG10n5as-3UjgPpqrdb8ZBS5c30mk/edit
- Latest audio laws https://github.com/Valar05/home-center/blob/main/docs/RITSU_PHONE_AUDIO_LAWS.md
- Historical code reference branch `Valar05/home-center@campaign/ritsu-local-tailnet-20261024`. Historical source is an anchor guide, not proof of exact running source.

## Acceptance

1. `BUILD_SIGNED=PASS`, source and signer verified and APK copied to Downloads with readback SHA.
2. Server Node syntax, browser exact-URL binding, journal preservation, and auth gate on 19647 verified from Windows. No second send.
3. Owner installs APK and physically checks tab close/reopen, long scroll retention and touch navigation.
4. Owner adds one existing ChatGPT URL and verifies continuing that *same* URL, with no duplicate send or wrong-tab reply.
5. Owner enables Pocket per-chat voice and hears a verified <=450-character reply in the existing receiver, including background playback. Long replies remain BLOCKED until explicit semantic-unit protocol is accepted.

Tests 3–5 are human/device acceptance, not part of host mocks. Never claim COMPLETE before them.
