# Fortress Online unified bootstrap

`tools/fortress_bootstrap.py` is the single operator entrypoint for the Android/Termux phone and the Windows desktop. It detects the host, calls the existing Home Center machine bodies, repairs native startup, and writes explicit receipts. It does **not** use ChatGPT browser or tab orchestration.

## Mission boundary

- One Python file is used on both machines.
- Android/Termux reuses the existing llama.cpp phone floor, Adam CLI, Vlad swarm daemon, Termux:Boot, wake lock, and Home Center status menu.
- Windows reuses Computer Hands, DPAPI-protected worker credentials, Ollama, the repository's offline Continue configuration, and Scheduled Tasks.
- Runtime inference has no cloud-model fallback.
- A second swarm implementation is not created.
- Battery and charge-aware workload governing is recorded as `deferred_by_owner`; this patch does not pretend to implement it.

## Run the same file

From an existing Home Center checkout on either machine:

```text
python tools/fortress_bootstrap.py install --repo-root <HOME_CENTER_CHECKOUT>
```

After installation, both machines expose the same command surface:

```text
fortress status
fortress repair
fortress doctor
fortress local -- <prompt>
```

### Android / Termux

The initial run installs the repository's existing phone-local model floor, Adam CLI, and Vlad service. It adds a Termux:Boot repair entry and requests `termux-wake-lock`. A green Android receipt requires the local inference health endpoint, Vlad, installed commands, boot entry, and the wake-lock command.

Termux:Boot and Termux:API still have to be permitted by Android. The script cannot repeal Android process killing by writing a confident JSON file.

### Windows desktop

The initial run installs or repairs Ollama and Continue CLI, ensures the canonical local models, invokes the existing Computer Hands installer, and registers startup/repair tasks. The first Computer Hands enrollment requires the existing bootstrap code through its hidden prompt or `HC_WINDOWS_BOOTSTRAP_CODE`; the value is redacted from logs and receipts.

By default, the bootstrap applies a reversible **AC-only** policy so closing the lid does not suspend the machine and AC idle sleep is disabled. Battery power policy is untouched. Use `--no-ac-awake` to leave the AC policy unchanged.

The Windows bodies use the current user's Scheduled Tasks and DPAPI scope. They resume after that user logs on. They are not falsely described as pre-login system services.

## Receipts

Android:

```text
~/.local/state/home-center/fortress-bootstrap/last-receipt.json
~/.local/state/home-center/fortress-bootstrap/receipts.jsonl
```

Windows:

```text
%LOCALAPPDATA%\HomeCenter\FortressBootstrap\last-receipt.json
%LOCALAPPDATA%\HomeCenter\FortressBootstrap\receipts.jsonl
```

Each receipt separates requested, implemented, deployed, verified, and blocked capability. Repository source existence is not device deployment evidence.

## Actions budget boundary

The repository's hosted GitHub Actions budget was exhausted while this source was assembled. The source includes deterministic contract tests at `tools/test_fortress_bootstrap.py`, but no hosted CI success is claimed until that account boundary is cleared. Exact Git blob readback proves the committed bytes; fresh phone and Windows receipts are still required for physical deployment acceptance.
