# Anvil native phone plane release and acceptance

This runbook carries the Anvil Shell commission from repository source through a callable installation on `primary-phone`. A source PR, a green repository run, a cloud deployment, a worker bootstrap, an APK installation, delivery, and user acceptance are separate states.

## Fixed identities

- Home Center repository: `Valar05/home-center`
- Anvil Shell repository: `Valar05/continue-continue`
- reviewed Anvil source head: `7e0e949ba3e3aefa8df608226086b6273cfb16ca`
- device: `primary-phone`
- worker: `phone-relay:primary-phone`
- maintenance lane: `PHONE_MAINTENANCE`
- package: `com.continuecontinue.anvilshell`
- expected version: `0.1.0-checkpoint`
- automatic replay: false

Command Center, THECAULDRON, a cloud-only substitute, another device, an arbitrary shell command, caller-supplied argv, caller-supplied URLs, and caller-supplied filesystem paths are excluded.

## Gate 1: exact-head source proof

1. Obtain a green `Anvil native phone plane` run for the exact Home Center PR head.
2. Preserve the workflow URL, run ID, reviewed head, Regnet receipt, and artifact digest.
3. A budget-cancelled, queued, skipped, stale-head, or empty-step job does not satisfy this gate.
4. Regnet may mark the exact source tested. It cannot mark deployment, phone callability, installation, delivery, or acceptance.

## Gate 2: merge and native cloud deployment

1. Merge only the exact green reviewed Home Center head to `main`.
2. Dispatch `Deploy Anvil native phone plane` with that exact merged commit and confirmation `deploy-native-phone`.
3. Require its deployment artifact and verify both `phoneHandsRelay` and `homeCenterMcp` identify the exact source.
4. Verify the live Home Center registry version is `2026-08-13.native-phone-plane-v1` and exposes:
   - `phone.devices`
   - `phone.diagnostics.enqueue`
   - `phone.maintenance.enqueue`
   - `phone.operation.get`

The deployment workflow does not deploy Command Center. A successful cloud deployment still does not prove that the phone worker was updated.

## Gate 3: one-time owner bootstrap

The stale worker cannot install its own new executor through a capability it does not yet possess. Do not cross that gap through `phone_shell` or another generic remote shell. The device owner runs the fixed bootstrap once from the existing Home Center checkout:

```sh
bash tools/bootstrap_native_phone_plane.sh <exact-merged-home-center-commit>
```

The script accepts only one 40-hex merged commit. It verifies the fixed Home Center origin, requires that commit to be an ancestor of current `origin/main`, extracts exactly three worker modules, compiles them, backs up the old modules, replaces them atomically, restarts exactly one relay, verifies `primary-phone`, and records a hashed receipt. It never accepts command text, argv, a URL, a device identity, or a path.

Require the receipt status `BOOTSTRAP_VERIFIED`, the exact merged source head, and both capabilities:

- `phone_diagnostics_readonly`
- `phone_maintenance_anvil_shell`

A restored rollback, missing capability, ambiguous process, unmerged commit, or changed origin fails closed.

## Gate 4: native callability

1. Call `phone.devices`; require one owner-scoped `primary-phone` registration carrying both capabilities.
2. Enqueue a `capability_snapshot` through `phone.diagnostics.enqueue`.
3. Poll only through `phone.operation.get`.
4. Require a terminal `phone.diagnostics.receipt.v1` whose request, stream, device, worker, queue, commission, lane, session, chunk, and receipt hashes validate.
5. Read-only diagnostics must report no network, write, subprocess, build, install, or UI authority.

This proves the native operation path is callable. It does not prove Anvil installation.

## Gate 5: native Anvil build, test, install, and readback

1. Mint the exact Home Center approval, queue revision, session, idempotency key, and unexpired device lease.
2. Enqueue only `anvil_shell.build_install.v1` through `phone.maintenance.enqueue`.
3. Bind the fixed identities above and source head `7e0e949ba3e3aefa8df608226086b6273cfb16ca`.
4. Poll through `phone.operation.get`; never replay automatically.
5. Require a terminal maintenance receipt binding:
   - exact source commit and clean detached worktree
   - pinned bootstrap archive hashes
   - deterministic CLI and Android tests
   - APK byte count and SHA-256
   - signing certificate digest
   - installer strategy and result
   - package/version readback
   - installed APK hash equal to built APK hash
   - rollback observation
   - exact unexpired `primary-phone` lease
   - receipt hash

Any mismatch is a failed installation, not a partial success.

## Gate 6: commissioned runtime acceptance

Run the Anvil acceptance contract from the Anvil repository on the installed app, including:

- Termux-parity shell behaviors promised by the source contract
- Drew's deterministic CLI tools
- deterministic offline `adam.quote` selections from the pinned literature, history, and Bible corpus
- team marker behavior
- Hunger invocation
- Hyperbolic invocation
- offline behavior and restart/crash recovery

Record observed commands, outputs, quote seed/input and selected corpus entry, timestamps, package/version, APK hash, and crash/restart outcomes. Do not infer these from source or build success.

## Gate 7: delivery and acceptance

Delivery requires the installed callable app plus the linked cloud, bootstrap, diagnostic, maintenance, and runtime receipts. Acceptance remains Drew's decision. Venice may issue completion authority only after every preceding gate is satisfied; until then its directive is `CONTINUE_REQUIRED`.
