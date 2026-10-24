# Ritsu Control: multi-tab, machine presets, agent-led script campaign

## User commission (2026-10-24)
The user confirmed their Ritsu Control (Connected) APK is signed in to actual Home Center and requested, before bed:
- multiple independent conversation tabs;
- a machine selector with preset choices; the selected machine changes each conversation's subsequent execution context;
- image/file retrieval **only when a user requests it**, never automatic;
- dedicated validated script running with receipts automatically returned to the agent;
- a repeated script/receipt/agent step loop, including on Instant, until the agent explicitly determines the job is complete;
- hands-free script staging/deployment and result round-tripping, avoiding repeated phone copy/paste.

## Branch
`campaign/ritsu-control-tabs-presets-runner-20261024` branched from the connected Android v0.11 work at `2331b6be197faeb09be1a8c85309f84261845ff6`. No production service or currently installed APK was modified.

## Implemented (local code, test-backed)
1. `RitsuWorkspace.java`: durable independent conversations, machine profiles (Termux Android; THECAULDRON Windows; Home Center cloud; other Windows), active-tab selection, 12-tab limit, per-tab script-campaign toggle; Instant as a **model preference**, not false control of the ChatGPT model.
2. `MainActivity.java`: top conversation dropdown, `+ Tab`, machine dropdown with explicit dark/light text contrast, active-tab message filtering, per-tab Script Campaign toggle in More, explicit owner-triggered image/file retrieval composer inserts. Image/file selection does not silently download any media.
3. `ConversationLedger.java`: backward-compatible `tabId` and `machineId` on persisted entries, per-tab filtering, route a verified reply back to the originating user-turn tab, not the currently visible tab.
4. `RitsuControlService.java`: spoken turns capture the selected tab/machine when speech is committed, not silently sent to the default tab.
5. `tools/ritsu-agent-loop/contract.mjs`: structured `run_script`, `complete`, `need_input` (dropdown options), and `request_asset` actions; machine/tab binding, content hash verification, time limits, workspace-relative path rule and authorization hooks.
6. `tools/ritsu-agent-loop/engine.mjs`: serialized agent -> script receipt -> agent continuation; explicit agent `complete` only ends a campaign. Failed scripts flow back to agent rather than being called complete; bounded worker slices emit `continue_required`; prompts and prompted assets yield to their correct control surfaces.
7. `tools/ritsu-agent-loop/journal.mjs`: append-only event log, durable latest JSON checkpoint, script receipt recovery, idempotent replay and owner stop latch.
8. Node tests cover multiple script requests before complete, failed-script continuation, replay, per-machine write gates, requested media, owner input options, journal recovery and stop. Android CI compiles the app and checks relevant source contracts.

## Security / authority
- **Never bake Home Center bearer/refresh credentials or a shared six-digit code into a distributable APK.** v0.11 sign-in continues using browser OAuth PKCE and encrypted Android Keystore.
- An agent script is data, not automatically safe. SHA validation and syntax parsing are not a sandbox. A real executor must use an owner-authorized, verified machine and file/identity boundary, approval for write-capable scripts, STOP/status/receipts.
- Image/file retrieval requires a trusted user-turn permission bit, not only an agent's self-asserted `requestedByUser`; this guard is still an unfinished integration requirement. **Do not connect the asset tool automatically until it exists.**
- Need-input options are rendered as bounded machine/preset choices in the existing Android UI pattern rather than requiring the owner to type hardware identifiers each time.

## Honest capability states at checkpoint
- CODE_WRITTEN: Android tabs/machine-picker, loop engine, journal and tests
- STATIC_TESTED: GitHub Actions Android Gradle + Node tests (use current commit check)
- INSTALLED_ON_PHONE: NO
- CLOUD_MULTI_TAB_TURN_TRANSPORT: NOT_DEPLOYED
- AUTOMATIC_AGENT_ROUNDTRIP: NOT_CONNECTED
- SANDBOXED_MACHINE_EXECUTOR: NOT_DELIVERED; a proposed executor mutation was blocked by host safety gate, not overridden
- SCRIPT_AUTODEPLOY: NOT_DELIVERED
- ON_DEMAND_MEDIA_BYTES: NOT_DELIVERED; explicit request UI only
- USER_ACCEPTED: NO

The current production `HomeCenterSync` still reports `Home Center cloud paired; conversation bridge not deployed`. Existing user conversations on the installed v0.11 app must be preserved. Do not silently replace or uninstall: debug APK signing changes between cloud runners.

## Next bounded slices
1. **Trust boundary**: require original user-turn `requestedAssets` for any file/image retrieval; an agent cannot authorize its own fetch. Finish safe validation/negative tests.
2. **Execution control**: build an isolated owner-approved host script-runner adapter with syntax check, staged script provenance, consistent machine identity, timeout/process-group kill, persisted STOP/RESUME, clipboard-first short failure/success receipts on Termux. Never bypass host safety approval.
3. **ChatGPT transport**: hook Home Center's OAuth-authenticated Android `turn/receipt/feed` to the existing ChatGPT Playwright/MCP retrieval path; receipt autopush should call the agent programmatically, not screen scrape or send a fake chat message. Preserve per-tab/model-preference/machine fields all the way through.
4. **Asset retrieval**: user-selected images/files only, with consent and bounded MIME/size/metadata; no unsolicited retrieval or secret data clipboard.
5. **Real-phone build**: solve repeatable signing/update strategy for `Ritsu Control (Connected)`, test Android machine dropdown/voice tab/PKCE sign-in and actual delivered agent turns end to end, then seek owner acceptance.

## Exact acceptance
One live paired phone launches two chat tabs, picks Termux for tab A and THECAULDRON for tab B, asks for a file only in tab B, sees independent replies, and runs a script-campaign in tab A. The Home Center agent issues script 1; the correct approved host validates and runs it; full bounded stdout/stderr receipt returns without manual copy/paste; agent sends script 2; loop proceeds until explicit final `complete`. Closing the launcher doesn't stop the campaign, and a second terminal can query/stop/resume it. Failure never silently becomes success.

## v0.12 Campaign APK release checkpoint, 2026-10-24
- Explicit user request: continue campaign until new APK delivered.
- Source revision for build: `c81cb398a7da429e317e8daffeb1de995e410143`.
- CI: https://github.com/Valar05/home-center/actions/runs/40091890147 **SUCCESS**, Android Java unit tests + Node loop/journal tests + full Gradle build + Campaign package and callback verification.
- GitHub Action artifact name: `ritsu-control-v0.12-tabs-machines-campaign-apk`, artifact ID `12559248000`.
- Produced APK SHA-256: `9da1e8eaaa79fc7b3298bb433fe70c3fa6c209b99f5bb6aebdbef309a6a42136`, 69,913 bytes.
- **Unique Android identity**: `com.homecenter.ritsucontrol.campaign`, title `Ritsu Control (Campaign)`. This package installs alongside `com.homecenter.ritsucontrol.connected` without uninstalling or overwriting its stored credentials/chat.
- **Unique OAuth redirect**: `ritsucontrolcampaign://oauth/callback`, includes required app-side check of scheme and manifest intent filter, avoiding collision with the owner's already-connected v0.11 app.
- Owner installation/sign-in on physical device remains UNVERIFIED. Fresh Campaign installation has separate app-private credentials; owner should connect Home Center account through app browser sign-in again.
- Campaign features actually in APK: per-tab UI, machine preset selection, per-tab script toggle and user-triggered asset request composer. Runner/journal protocols are tested source only; cloud turn/feed and autonomous script execution remain NOT DELIVERED. No fake completion or shell claims.


## Physical Android message-delivery failure, 2026-10-24

**Owner report:** The v0.12 Ritsu Control (Campaign) application successfully completed Home Center browser OAuth. User submitted the spoken/typed message **"hello darling"** and saw no ChatGPT conversation appear, no new answer upon returning to the ChatGPT Android app. This is the first real-phone conversation-delivery acceptance check and it **failed**.

**Root cause verified in source:** `android/ritsu-control/app/src/main/java/com/homecenter/ritsucontrol/HomeCenterSync.java` `syncOnce()` deliberately only loads/refeshes Home Center OAuth and assigns `status="Home Center cloud paired; conversation bridge not deployed"`; it does not iterate pending `ConversationLedger` turns or POST them anywhere. The messages are local `WAITING_FOR_HOME_CENTER` outbox rows. Existing `functions/ritsu_chat_callback_api.js` `ritsu.chat.prepare` explicitly does *not* start a model or open ChatGPT, and `ritsu.chat.result` works only after a model-origin `ritsu.chat.publish` call. No inbound push or native ChatGPT turn creation exists.

**Critical platform boundary:** OpenAI Responses/Conversations API stores its own API conversations and does not provide evidence of writing into the user's native ChatGPT app conversation list. That is a different product surface. A Home Center MCP tool can publish/retrieve a response but cannot spontaneously initiate a ChatGPT native chat just because the phone sent an MCP write. The user expected actual new native ChatGPT threads. No hidden API-key substitution, chargeable API routing, or unapproved screen scraping is authorized.

**Truth states**:
- Android OAuth ACCOUNT CONNECTED = user confirmed.
- LOCAL MESSAGE STORED = source path supports; exact row pending still needs readback, but no delete/reinstall.
- CLOUD MESSAGE DELIVERED = NO.
- CHATGPT NEW CHAT = NO.
- CHATGPT ANSWER = NO.
- AUTOMATIC RETURN = NO.
- SCRIPT RUNNER END TO END = NO.

**Implementation priority**:
1. Prove an authorized native ChatGPT conversation ingress and result retrieval channel (Work browser control or other supported method), with nonfaked end-to-end canary and trace. Do not claim a mock result is a native ChatGPT chat.
2. Build owner-authenticated Home Center turn/enqueue/ack/feed with exact tab, turn and machine IDs; durable, idempotent and preserving queued user turns. The backend returns receipt states only.
3. Connect worker ChatGPT ingress + model-origin response callback. No new build labeled "chat enabled" until user sees `hello darling` or another explicit canary in ChatGPT chat history and receives authentic response.
4. Make unsent state prominent: `Saved on phone; NOT sent to ChatGPT` with durable outbox controls. Don't call it "paired and ready" when only OAuth is paired.
5. Never uninstall or clear v0.12 private storage: the existing unsent message is user data and must be preserved.

**Stop criterion:** An owner-accepted canary proves Ritsu Control phone text is delivered to native ChatGPT as a visible new turn, assistant replies and the actual reply returns to the originating Ritsu tab, with both directions' receipts. Anything less stays INCOMPLETE.
