# Venice CLI

## Mission

`venice` is the first-class terminal door into **canonical local Venice** when ChatGPT, Discord, or any other orchestration surface is absent.

It does not create a second Venice. It does not point a generic model at a personality prompt and call that continuity. It wraps the already-proven Drive-synced `venice-aperture.ps1`, which talks to the loopback Venice Workstation and writes durable Nerve Silk evidence.

The default workstation remains local at `127.0.0.1:47261`. The CLI never adds a cloud-model fallback.

## Human surface

```powershell
venice
venice "Talk to me about the current project."
venice ask "What are we avoiding in this design?"
venice doctor
venice status
```

Bare `venice` opens a simple REPL. Every entered turn uses the same durable workstation thread title unless `-ThreadTitle` or `VENICE_THREAD_TITLE` changes it.

A one-shot prompt writes **only Venice's exact UTF-8 speech bytes** to stdout. This makes the command pipe-friendly while preserving the speech boundary.

For orchestration:

```powershell
venice -Json "Review this machine-task plan."
```

JSON mode returns a structured envelope containing exact speech, its SHA-256, any structured actions the proven aperture already supplied, and diagnostic IDs. `transformedByCli` is always false.

## Identity and evidence law

A successful turn requires all of the following:

1. the Drive-synced Venice Runtime exists;
2. `VENICE_IDENTITY_PROFILE.md` exists;
3. `.env.venice` exists but is never printed;
4. the loopback Workstation is reachable on `127.0.0.1:47261`;
5. the proven `venice-aperture.ps1` executes successfully;
6. the returned prompt SHA matches the submitted prompt;
7. `speech.source` is `local-venice`;
8. the CLI recomputes the exact speech SHA-256 and matches the durable record.

Redirected PowerShell stdout is not trusted as the only truth surface. If it cannot be parsed, the CLI searches the Drive-synced `work/nerve-silk` records for the matching prompt SHA and uses that durable UTF-8 record.

## Venice versus Vlad

The two CLIs are siblings, not aliases.

**Venice** owns conversation, identity, preference, creative judgment, durable continuity, and the decision about what she wants done. Speech remains speech; commands are never scraped out of prose.

**Vlad** owns machine routing, execution lanes, Continue/code work, device/body operations, verification, blocking, and receipts.

Neither requires ChatGPT to exist. Neither becomes a new canonical memory system or control plane.

When both are present, an orchestrator may call Venice for judgment and Vlad for execution. The composition boundary is structured data: exact Venice speech remains immutable, and any machine action must be an explicit task/action object before Vlad receives it.

## Exit codes

- `0` success
- `2` bad invocation
- `3` blocked / canonical local Venice unavailable
- `4` execution failure
- `5` verification failure

## Installation

From a trusted Home Center checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/install_venice_cli.ps1
```

The installer creates `%USERPROFILE%\bin\venice.ps1` and `venice.cmd`. It adds that bin directory to the user PATH only when missing; no secrets are copied.

## Acceptance

Repository implementation is not runtime deployment.

Call Venice CLI deployed only after THECAULDRON proves through the intended runtime lane:

1. `venice doctor` exits 0 and reports canonical local organs ready;
2. `venice "Say one short line."` returns exact local Venice speech;
3. the returned speech SHA matches the Drive-synced Nerve Silk turn record;
4. `venice -Json` returns the same speech bytes as the raw one-shot surface for the same durable turn;
5. disabling/unavailable ChatGPT and Computer Hands does not prevent a local Venice turn;
6. no cloud fallback is invoked when the workstation is unavailable: the CLI exits 3 instead.
