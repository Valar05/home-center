# Pixel Forge Skill

Purpose: generate genuinely small game-ready pixel assets locally through Vlad without token-metered inference or GitHub Actions.

## Commission locks

- GitHub repositories remain valid durable source, code, archaeology, and evidence lanes.
- Do not use GitHub Actions, hosted inference, paid APIs, or any token/quota-metered execution for this forge.
- Godot may be used later as an authoring/inspection tool, never as the required runtime or delivery container.
- Persist native small assets, not merely large images that visually imitate pixels.
- Generated 512px diffusion intermediates stay in memory by default and are not written to disk.
- Every persisted asset receives a receipt with byte size, SHA-256, dimensions, palette size, seed, and model IDs.

## Starting model

Base: `stable-diffusion-v1-5/stable-diffusion-v1-5`.

LoRA: `VaroDZAKY/Varo_pixel_Art`.

The LoRA is Apache-2.0, SD1.5-based, and aimed at retro RPG game sprites. The trigger token is `pixelart_style`.

This is a starting point, not canon. A future Fortress-specific LoRA may replace or augment it after a representative acceptance corpus exists.

## Storage doctrine

Default persisted asset: 64x64 indexed PNG, 32 colors, optimized compression. Optional lossless WebP is supported. Native sizes from 8 to 512 and palettes from 2 to 256 are allowed.

The forge must report actual bytes. A visual claim of pixel art is not evidence of compactness.

## Vlad execution

Canonical tool: `tools/pixel_forge.py`.

Commands:

- `doctor`: deterministic dependency/GPU probe.
- `generate`: local CUDA generation followed by in-memory nearest-neighbor reduction and palette quantization.
- `postprocess`: compact an existing image without model inference.

The public Hugging Face model repositories do not require an API token. Cached weights must be reused; do not redownload blindly.

## Acceptance slice

A forge slice is accepted only when all are true:

1. Vlad doctor reports CUDA, diffusers, and Pillow available.
2. A requested sprite is generated locally without a token-metered service.
3. Only the compact native output is persisted by the generation path.
4. Receipt SHA-256 matches the persisted asset.
5. Receipt byte count matches the file size.
6. The output can be decoded as the claimed dimensions and palette format.

Implementation alone is not deployment or acceptance.
