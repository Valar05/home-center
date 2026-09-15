# Home Center Capability Inventory

This inventory is the planning surface for the phone-first Home Center foundation. It separates source evidence from live runtime evidence. A capability is not considered deployed merely because its files or tests exist.

## Decision rule

Prefer the smallest existing capability that gives Drew useful information or a copy-ready draft before adding mutation authority. Every row should eventually have a live receipt, a restart path, and a clearly named boundary.

## Inventory

| Capability | What it provides | Phone-callable | Drive/context-aware | Mutation level | Current evidence | Cheapest integration |
| --- | --- | --- | --- | --- | --- | --- |
| Home Center conversation gateway | Natural-language turns, tool routing, evidence finalization, working memory | Existing Android/Home Center path; phone relay separately proven | Yes: Drive, Docs, memory, evidence, conversations | Mixed; broad tool registry exists | Source and historical runtime evidence; current foundation needs a fresh phone conversation canary | Add an explicit read-only `inform` route before action routing |
| Drive and Docs context | Search/read source material, recover context, support writing and evidence packets | Yes through Home Center conversation/tool path | Native | Read-first; document writes are separate explicit tools | Existing tool and audit surfaces | Make source-backed answer/draft the default response shape |
| Remembered writing context | Voice, corpus, prior writing context, draft/rewrite support | Available through conversation context when routed | Yes | Read/draft first; writes require explicit document operation | Existing working-memory and writing-context code/docs | Add `draft`, `outline`, `rewrite`, and `copy-ready` intent routing |
| Deterministic command parser | Handles known commands without requiring a model planner | Existing app path; not yet the preferred top-level route | Limited, command-specific | Usually low-risk CRUD/readback | `CommandParser` exists; audit says normal submit still calls GPT first | Route obvious read/status/navigation requests locally |
| Adam body router | `text`, `chat`, `continue`, `terminal`, `vlad`, and `radio` modes with bounded receipts | Phone CLI/overlay path exists in source | Partly; text mode uses Home Center operations | Terminal is explicit; model-generated shell is restricted | Source contracts and acceptance scripts exist; live phone acceptance is a separate gate | Use Adam conversation mode as an adapter, not a new control plane |
| Deterministic terminal lane | Explicit terminal command execution with stdout, stderr, return code, cwd, timeout | Phone-to-Termux path exists; primary phone `phone_shell` canary passed | Indirectly; commands can invoke existing Drive-aware tools | Mutating when explicitly requested; must remain approval-bound | `primary-phone` marker completed with exit code 0; desktop `shell.exec` also proven | Expose as a separate explicit `TERMINAL` mode after inform mode |
| Phone relay | Home Center queue polling, phone shell, heartbeat, command completion | Yes; `primary-phone` is live | Home Center-owned | Depends on queued action | Fresh device heartbeat and `HOME_CENTER_PRIMARY_CANARY_V2` receipt | Use as the transport for all later phone features |
| Windows Computer Hands | Bounded desktop process/window/input/shell control | Yes through Home Center operations | Home Center-owned | Mixed/high-risk actions are explicit | `windows-hands-01 online=true`, `fileLayer=drive_sync`, fresh heartbeat | Keep as the desktop carrier; do not expose it as a free-form planner |
| Chromium Throne | Dedicated authenticated browser profile and browser mechanics | Yes through the existing Home Center desktop carrier | Organ/Throne-specific | Browser mutation | Running profile observed; Qmee survey window visibly present | Add browser observation and action adapters after conversation foundation |
| Local image generation | ComfyUI on THECAULDRON, `fortress-image` and `venice-image` wrappers, phone delivery | Designed for phone relay and `phone_shell` | Home Center receipt/delivery-aware | Generates files; not general desktop mutation | Transport contract and prior implementation evidence; perceptual quality remains separate | First use as an explicit `IMAGE` mode with prompt/result/provenance, not automation |
| Gemini | Conversation compaction and possible fallback/planner/builder | Through the owning Home Center path, not as a new transport | Can receive retrieved context when explicitly routed | No authority by default | Gemini compaction/provider code exists | Keep behind deterministic routing and use it only for ambiguity, synthesis, or bounded tool construction |
| Fortress event kernel | Durable campaign state, named boundaries, deterministic next action, receipts | Indirectly through Home Center | Yes | No direct external mutation; governs it | Existing event-kernel source/tests and recovery doctrine | Use its state model for inform/terminal/image promotion gates |
| Judgment Jar/Venice review | Plan/stop review, adversarial checks, completion permission | Primarily Adam/worker path | Repository/evidence-aware | Governing review, not execution | Existing Adam/Venice source and receipts | Apply only when a request crosses from information into action |

## Live proofs already obtained

These are current runtime observations, not source claims:

- `primary-phone` registered and reporting a fresh Home Center heartbeat.
- `HOME_CENTER_PRIMARY_CANARY_V2` completed through `command_center.phone_hands` with `exitCode=0`.
- `windows-hands-01` reported `online=true`, `status=idle`, and `fileLayer=drive_sync`.
- Chromium Throne reported `state=running` with profile `C:\Users\dclar\AppData\Local\HomeCenter\ChromiumThrone\profile`.
- The dedicated Chrome window visibly reported `Earn | Qmee - Google Chrome for Testing`.
- The phone relay was restored from `/storage/emulated/0/Documents/GodotProjects/home-center` using an LFS-skipped clone and absolute script path.

These proofs establish transport and body liveness. They do not yet establish a general-purpose phone conversation round trip or a completed paid-survey canary.

## Gaps to resolve

1. The phone can send and execute a marker, but a normal conversational message has not yet been proven end to end through the new foundation.
2. Drive retrieval and writing-context behavior exists, but it needs a small read-only phone canary with source references and a copy-ready answer.
3. Deterministic routing exists, but the normal submit path historically invokes GPT before local routing; this is both a cost and reliability opportunity.
4. Image transport is specified separately from image quality. Instruction-following needs a prompt/evaluation pass, not a new delivery architecture.
5. Direct SSH authentication to THECAULDRON has been intermittent; Home Center Computer Hands is currently the proven desktop carrier.

## Recommended first slice

Build and accept one read-only `INFORM` conversation round trip:

```text
Drew phone message
  -> primary-phone Home Center relay
  -> Home Center read-only router
  -> Drive/context retrieval
  -> source-backed answer plus copy-ready writing block
  -> phone response and durable receipt
```

Acceptance should require:

1. No desktop or browser mutation.
2. At least one retrieved source reference.
3. A concise answer and a separately copyable draft block.
4. A typed “source unavailable” result when retrieval fails.
5. Fresh phone heartbeat before and after.
6. A durable request/response receipt without storing unnecessary sensitive content.

After that passes, add explicit `TERMINAL`, `IMAGE`, and browser/Throne modes one at a time. Gemini can be introduced only where deterministic routing cannot answer or where a bounded builder task is explicitly commissioned.
