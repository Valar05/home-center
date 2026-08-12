#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

BASE_MODEL = os.environ.get("HC_PIXEL_BASE_MODEL", "stable-diffusion-v1-5/stable-diffusion-v1-5")
LORA_MODEL = os.environ.get("HC_PIXEL_LORA_MODEL", "VaroDZAKY/Varo_pixel_Art")
DEFAULT_NEGATIVE = "blurry, realistic, 3d, gradient, smooth shading, antialiasing, watermark, text"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compact_image(image, output: Path, size: int, colors: int, fmt: str) -> dict:
    from PIL import Image

    if size < 8 or size > 512:
        raise ValueError("size must be between 8 and 512")
    if colors < 2 or colors > 256:
        raise ValueError("colors must be between 2 and 256")

    image = image.convert("RGBA")
    image = image.resize((size, size), Image.Resampling.NEAREST)
    rgb = image.convert("RGB")
    quantized = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

    output.parent.mkdir(parents=True, exist_ok=True)
    fmt = fmt.lower()
    if fmt == "png":
        quantized.save(output, format="PNG", optimize=True)
    elif fmt == "webp":
        quantized.convert("RGB").save(output, format="WEBP", lossless=True, method=6)
    else:
        raise ValueError("format must be png or webp")

    return {
        "path": str(output),
        "bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "width": size,
        "height": size,
        "colors": colors,
        "format": fmt,
    }


def load_pipeline():
    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError as exc:
        raise RuntimeError("pixel forge dependencies missing; run tools/setup_pixel_forge.sh") from exc

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU not available; Vlad pixel forge currently requires CUDA")

    dtype = torch.float16
    pipe = StableDiffusionPipeline.from_pretrained(
        BASE_MODEL,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
        use_safetensors=True,
    )
    pipe.load_lora_weights(LORA_MODEL)
    pipe.enable_attention_slicing("max")
    if hasattr(pipe, "enable_vae_slicing"):
        pipe.enable_vae_slicing()
    if hasattr(pipe, "enable_model_cpu_offload"):
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")
    return pipe, torch


def doctor() -> int:
    info = {
        "baseModel": BASE_MODEL,
        "loraModel": LORA_MODEL,
        "hfTokenRequired": False,
        "cuda": False,
    }
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda"] = bool(torch.cuda.is_available())
        if info["cuda"]:
            info["gpu"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["vramBytes"] = int(props.total_memory)
    except Exception as exc:
        info["torchError"] = f"{type(exc).__name__}: {exc}"
    try:
        import diffusers
        info["diffusers"] = diffusers.__version__
    except Exception as exc:
        info["diffusersError"] = f"{type(exc).__name__}: {exc}"
    try:
        import PIL
        info["pillow"] = PIL.__version__
    except Exception as exc:
        info["pillowError"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(info, indent=2, sort_keys=True))
    return 0 if info["cuda"] and "diffusers" in info and "pillow" in info else 2


def generate(args) -> int:
    started = time.time()
    pipe, torch = load_pipeline()
    generator = torch.Generator(device="cuda").manual_seed(args.seed)
    prompt = f"pixelart_style, {args.prompt}, sharp pixel edges, flat colors, limited palette"
    result = pipe(
        prompt=prompt,
        negative_prompt=args.negative,
        width=args.render_size,
        height=args.render_size,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance,
        generator=generator,
    ).images[0]

    output = Path(args.output).expanduser().resolve()
    asset = compact_image(result, output, args.size, args.colors, args.format)
    receipt = {
        "kind": "pixel.forge.receipt.v1",
        "ok": True,
        "createdAtUnix": int(time.time()),
        "durationSeconds": round(time.time() - started, 3),
        "prompt": args.prompt,
        "expandedPrompt": prompt,
        "negativePrompt": args.negative,
        "seed": args.seed,
        "steps": args.steps,
        "guidance": args.guidance,
        "renderSize": args.render_size,
        "baseModel": BASE_MODEL,
        "loraModel": LORA_MODEL,
        "asset": asset,
        "persistedIntermediate": False,
        "tokenDependentService": False,
    }
    receipt_path = Path(args.receipt).expanduser().resolve() if args.receipt else output.with_suffix(output.suffix + ".receipt.json")
    save_receipt(receipt_path, receipt)
    print(json.dumps({"ok": True, "asset": asset, "receipt": str(receipt_path)}, sort_keys=True))
    return 0


def postprocess(args) -> int:
    from PIL import Image

    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    image = Image.open(source)
    asset = compact_image(image, output, args.size, args.colors, args.format)
    print(json.dumps({"ok": True, "asset": asset}, sort_keys=True))
    return 0


def build_parser():
    ap = argparse.ArgumentParser(description="Local-first tiny pixel asset forge for Vlad")
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")

    gp = sub.add_parser("generate")
    gp.add_argument("prompt")
    gp.add_argument("--output", required=True)
    gp.add_argument("--receipt")
    gp.add_argument("--size", type=int, default=64, help="persisted native sprite size")
    gp.add_argument("--colors", type=int, default=32)
    gp.add_argument("--format", choices=("png", "webp"), default="png")
    gp.add_argument("--render-size", type=int, default=512, choices=(256, 384, 512))
    gp.add_argument("--seed", type=int, default=1337)
    gp.add_argument("--steps", type=int, default=28)
    gp.add_argument("--guidance", type=float, default=7.5)
    gp.add_argument("--negative", default=DEFAULT_NEGATIVE)

    pp = sub.add_parser("postprocess")
    pp.add_argument("--input", required=True)
    pp.add_argument("--output", required=True)
    pp.add_argument("--size", type=int, default=64)
    pp.add_argument("--colors", type=int, default=32)
    pp.add_argument("--format", choices=("png", "webp"), default="png")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "doctor":
        return doctor()
    if args.command == "generate":
        return generate(args)
    if args.command == "postprocess":
        return postprocess(args)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        raise
