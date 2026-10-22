# Ritsu Warm v1: Home Center typed speech operation

**Status:** Source implemented on `feature/ritsu-typed-voice-v1`, CI integration pending, not yet deployed or commissioned on THECAULDRON.

## Mission

Replace chat → Computer Hands `shell.exec` with one narrow Home Center operation, `ritsu.voice.speak`.

    ChatGPT → Home Center typed voice ticket → dedicated outbound THECAULDRON voice worker
             → immutable Ritsu | Warm | v1 Qwen local API via ritsu_say.py
             → existing Windows relay → existing Tailscale Termux receiver

No direct SSH, PowerShell or arbitrary command is accepted through this voice operation. The Windows worker executes only a pinned script with a private temp `--text-file`, never injected shell text. It does not replace the approved voice profile, reference recording or relay.

## Chat-facing commands

`ritsu.voice.speak` with `{requestId, text, voice:"warm-v1", delivery:"phone"}`. Optional `chunks` constrains expected relay receipts. Max 5000 characters, no shell/action/engine fields, idempotent request IDs with immutable transcript hash.

`ritsu.voice.status` with `{requestId}` returns queued, leased, enqueued, failed or maintenance. Enqueued is **never** equivalent to Android ACK or HEARD.

`ritsu.voice.worker.register` with a unique requestId issues a single-use 10-minute bootstrap. Pass this secret directly to THECAULDRON using a private operator path, **never** paste it into ChatGPT. The Windows worker stores its bearer credential in a local ACL-protected file.

## Maintenance: Turbo ASMR

`C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\RITSU_WARM_ASMR_MAINTENANCE` prevents voice generation. The dedicated voice worker never starts or restarts Qwen, never loads a fallback model, and never competes with intentional Turbo ASMR GPU use. A separate relay watchdog is independent of model availability.

## Kokoro retirement and cleanup

The old `local_voice.ticket.create` operation is a separate **Kokoro** fixed `af_heart` pipeline. It is not, and must never be, a Ritsu Warm v1 fallback. This branch's deterministic integration removes old `local_voice` operations from Home Center's advertised/dispatchable MCP operation registry.

For safety, the legacy Kokoro HTTP endpoint, Firestore tickets, older worker files, and historical artifacts remain intact until a dependency audit proves nothing else relies on them. This is a *quarantine and deprecation*, not destructive blanket deletion. After Warm v1 ticket success, separately retire Kokoro startup/worker and deploy removal if confirmed unused.

## Deployment gates

1. CI validates source and integration patch. Review PR; merge only after green tests.
2. Deploy updated Home Center MCP dispatcher **and** HTTPS `ritsuVoice` function. Read back capabilities to confirm `ritsu.voice.speak` exists. No capability claim before deployment.
3. Bootstrap worker privately; install it as an outbound-only THECAULDRON supervisor only **after** a canary and explicit clearance of Turbo ASMR maintenance.
4. Verify fixed text, sequence, synth receipt, relay enqueue, Android download and ACK, and user-confirmed HEARD.
5. Test failure/retry/idempotency, simultaneous chats, lease expiry, reboot/login, paused model, worker downtime. Lease is 20 minutes; ambiguous crash after enqueue before cloud completion still needs a durable local receipt journal to prevent re-delivery. Do not claim exactly-once or fully hardened until tested.
6. Remove obsolete Kokoro assets only after dependency inventory and a backup/rollback receipt.

## Sources

- `docs/RITSU_PHONE_AUDIO_LAWS.md` governs the exact Warm v1 identity and current phone relay.
- `functions/ritsu_voice_api.js` is the narrow cloud dispatcher and outbound-worker ticket API.
- `workers/ritsu_warm_ticket_worker.py` is the fixed Windows voice worker.
- `tools/apply_ritsu_voice_patch.mjs` adds operation and HTTPS export, deprecates Kokoro MCP exposure.
- `.github/workflows/ritsu-typed-voice-integrate.yml` tests and stages integration wiring, no automatic production deployment.

## Deployment and Windows staging checkpoint, 2026-10-22

- PR #386 merged to main. Dedicated GitHub Actions run `39848810751` passed, deploying both `ritsuVoice` HTTP endpoint and `homeCenterMcp`. Home Center `capabilities` confirmed exactly `ritsu.voice.speak`, `.status`, and `.worker.register` advertised, with legacy Kokoro operations removed.
- Live Windows Computer Hands worker `windows-hands-01` is online. The `process.start` request `ritsu-worker-stage-source-20261022` was accepted/completed and launched a short-lived PowerShell process to fetch the reviewed GitHub `workers/ritsu_warm_ticket_worker.py` into `%LOCALAPPDATA%\\RitsuWarmTicketWorker\\worker.py` and compile it. **Only process launch is attested, not the child command exit status or actual file hash; verify locally before claiming installed.**
- Independent `process.start` request `ritsu-typed-worker-protect-asmr-20261022` launched PowerShell to create the `RITSU_WARM_ASMR_MAINTENANCE` sentinel if absent. This is intended to prevent the new worker from consuming GPU while ASMR is active. Again, only process start is attested, not file readback.
- **Pending private bootstrap:** Never put the one-time registration code or bearer token into GitHub commits, ChatGPT transcripts or Computer Hands tickets. The current `ritsu.voice.worker.register` operation creates a 10-minute single-use secret and the local Python worker `--bootstrap` asks for it via `getpass`. A secure out-of-band enrollment transfer or an explicit user-led private Windows entry is required. Registration has **not** been initiated to avoid exposing a secret without that channel. Worker is **not running/polling** and no voice ticket has been submitted.
- Before the first audible canary, reconcile user-selected whisper reference and the -1 semitone setting with the pinned approved speaker. Current worker explicitly requests original Warm v1. No approval has been given to silently switch voice identity.

## Windows registration and maintenance canary (2026-10-22)

- User confirmed `REGISTERED: token saved privately, not printed` from Windows worker `--bootstrap-clipboard`. Private token remains on THECAULDRON. Never publish or read it back to chat.
- GitHub `workers/ritsu_warm_ticket_worker.py` was hardened with a Windows named mutex to prevent duplicate worker pollers (commit `0a8c915a46b21805fb5e9b8958068b596fcb81f0`). The deployment command fetched that pinned source into the local worker path, verified compilation, created the `RITSU_WARM_ASMR_MAINTENANCE` safeguard if absent, and launched the Python worker. Windows process listing afterward showed a new Python process (PID 25992), but PID identification alone is not identity proof.
- **Real cross-system receipt:** Home Center `ritsu.voice.speak` request `ritsu-worker-maintenance-canary-20261022` was accepted as queued and then `ritsu.voice.status` reported terminal `maintenance`, `relayIds: []`, `heard: not_verified`. This proves the authenticated Windows worker polled, processed, and completed the ticket in maintenance mode without voice generation. It does not prove phone audio or startup after Windows reboot.
- Remaining acceptance: install/review persistent startup if desired; clear ASMR maintenance only upon user consent; reconcile newly chosen voice and -1-semitone pitch with original Warm v1 without overwriting backups; send real speech ticket; inspect relay download/ACK and obtain user HEARD confirmation; test reboot and failure recovery.
