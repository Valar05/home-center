# HF Vendor Through GitHub Plan - 2026-08-11

Status: accepted direction.

## Ruling

Do not make the phone a full Hugging Face workstation. Do not depend on the `hf` CLI for PocketTTS runtime.

Use a desktop/workstation lane to curate Hugging Face code and model artifacts piece by piece, then publish pinned private GitHub artifacts for phone and local runtimes to consume.

## Lanes

### Desktop vendor lane

The desktop is allowed to do the heavier work:

- inspect upstream Hugging Face repos and model cards,
- fork or mirror only useful code,
- download and verify artifacts,
- convert or repack when needed,
- run larger tests,
- produce release assets with checksums,
- update the private vendor manifest.

### Private GitHub vendor/CDN lane

GitHub is the versioned distribution surface:

- private source forks for code,
- private release artifacts for model/config/tokenizer bundles,
- Git LFS only where it helps and does not punish phone sync,
- immutable tags for known-good bundles,
- checksum manifests committed beside release metadata,
- license/provenance files per upstream source.

GitHub raw URLs may be convenient for development, but runtime consumers should prefer release artifacts or local checked-out/cache paths with SHA-256 verification.

### Phone runtime lane

The phone remains a small local runtime:

- call PocketTTS directly through `pockettts-say` or `pocket-tts-phone`,
- keep `HF_HUB_DISABLE_XET=1`,
- avoid `hf` CLI,
- avoid arbitrary full-stack `transformers` installs unless a specific local runtime requires it,
- consume vendored release artifacts from private GitHub when needed,
- cache locally under Termux after first fetch,
- repair PocketTTS WAV headers with `fix-pockettts-wav-header` before treating output as interoperable media.

## Current phone proof

Created on `primary-phone`:

- `/data/data/com.termux/files/home/bin/pockettts-say`
- `/data/data/com.termux/files/home/pockettts_out/no_hf_cli_canary.wav`

Canary receipt:

- Bytes: `170924`
- SHA-256: `27213ebb59fa1acbc912ced5f55838991acb7c08f15fed579707e955eab89c84`
- Format readback: mono, 24000 Hz, 85440 frames, 16-bit PCM
- Duration: `3.56` seconds
- HF CLI state: present on phone but unused by the workflow.

## Vendor manifest shape

Each vendored piece should get one manifest record:

```json
{
  "id": "pockettts-english-runtime-YYYYMMDD",
  "upstream": {
    "kind": "huggingface_repo_or_file",
    "repo": "owner/name",
    "revision": "commit-or-tag",
    "files": ["config.yaml", "model.safetensors", "tokenizer.json"]
  },
  "license": "upstream license string",
  "desktopBuild": {
    "tool": "manual|script name",
    "host": "desktop",
    "createdAt": "ISO-8601"
  },
  "artifacts": [
    {
      "name": "bundle.tar.zst",
      "githubReleaseTag": "hf-vendor/pockettts-english-runtime-YYYYMMDD",
      "sha256": "...",
      "bytes": 0
    }
  ],
  "phoneInstall": {
    "targetDir": "$HOME/.local/share/fortress/vendor/pockettts/english",
    "runtime": "pockettts-say",
    "requiresHfCli": false
  }
}
```

## Fork/update policy

- Fork upstream code only when patching or freezing behavior matters.
- Prefer release artifacts for generated bundles and model files.
- Keep upstream refs pinned by commit, not branch name.
- Update one bundle at a time.
- Every update must include: upstream ref, byte count, SHA-256, license note, phone install target, and at least one smoke test receipt.
- If a model file is too large for normal phone git sync, keep it out of the worktree and fetch it as a release asset into a local cache.

## Immediate next target

Turn PocketTTS into the first vendor manifest:

1. Desktop identifies the exact PocketTTS upstream code/model/config files used by the current phone install.
2. Desktop publishes a private GitHub release bundle for the smallest working English PocketTTS runtime.
3. Phone installer downloads that release asset, verifies SHA-256, and places it under a stable local cache path.
4. `pockettts-say` gets an optional `--vendor-root`/environment hook so it can use the vendored cache without calling Hugging Face at runtime.
