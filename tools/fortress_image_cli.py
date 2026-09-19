#!/usr/bin/env python3
"""Deterministic CLI front-end for the canonical Fortress Image renderer.

This file never renders pixels itself. It compiles named presets into explicit
environment variables and then delegates to fortress_image_entry.sh, which
retains SSH Axis ownership and the existing THECAULDRON ComfyUI transport.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRESETS_PATH = ROOT / "fortress_image_presets.json"
ENTRY = ROOT / "fortress_image_entry.sh"

LORA_RE = re.compile(r"^[A-Za-z0-9._ ()+\-]+\.safetensors$")


def load_registry() -> dict:
    data = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "fortress-image-presets.v1":
        raise SystemExit("BLOCKED: unsupported preset registry schema")
    return data


def deterministic_seed(prompt: str) -> int:
    digest = hashlib.sha256(("fortress-image-v1\0" + prompt.strip()).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1) + 1


def parse_size(value: str, preset: dict) -> tuple[int, int]:
    aliases = {
        "portrait": (512, 768),
        "square": (640, 640),
        "landscape": (768, 512),
        "preset": (int(preset["width"]), int(preset["height"])),
    }
    if value in aliases:
        return aliases[value]
    m = re.fullmatch(r"(\d+)[xX](\d+)", value)
    if not m:
        raise argparse.ArgumentTypeError("size must be preset, portrait, square, landscape, or WIDTHxHEIGHT")
    width, height = map(int, m.groups())
    for name, n in (("width", width), ("height", height)):
        if n < 128 or n > 1024 or n % 64:
            raise argparse.ArgumentTypeError(f"{name} must be 128..1024 and divisible by 64")
    return width, height


def parse_lora(spec: str) -> dict:
    parts = spec.split("@")
    if not parts or not LORA_RE.fullmatch(parts[0]) or Path(parts[0]).name != parts[0]:
        raise argparse.ArgumentTypeError("LoRA must be an installed .safetensors basename, optionally @MODEL[@CLIP]")
    try:
        model = float(parts[1]) if len(parts) > 1 and parts[1] else 0.6
        clip = float(parts[2]) if len(parts) > 2 and parts[2] else model
    except ValueError as exc:
        raise argparse.ArgumentTypeError("LoRA strengths must be numbers") from exc
    if len(parts) > 3 or not (-2.0 <= model <= 2.0 and -2.0 <= clip <= 2.0):
        raise argparse.ArgumentTypeError("LoRA strengths must be between -2.0 and 2.0")
    return {"filename": parts[0], "model": model, "clip": clip}


def compile_config(args: argparse.Namespace, registry: dict, mode: str) -> dict:
    presets = registry["presets"]
    if args.preset not in presets:
        raise SystemExit(f"BLOCKED: unknown preset {args.preset!r}; run fortress-image presets")
    p = json.loads(json.dumps(presets[args.preset]))

    width, height = parse_size(args.size, p)
    loras = list(p.get("loras") or [])
    for raw in args.lora or []:
        loras.append(parse_lora(raw))
    if len(loras) > 4:
        raise SystemExit("BLOCKED: at most four LoRAs may be stacked in one render")

    seed = args.seed if args.seed is not None else deterministic_seed(args.prompt)
    if seed < 1 or seed > 2**63 - 1:
        raise SystemExit("BLOCKED: seed must be 1..9223372036854775807")

    negative = p.get("negative", "")
    if args.negative_extra:
        negative = ", ".join(x for x in (negative, args.negative_extra.strip()) if x)

    steps = args.steps if args.steps is not None else int(p["steps"])
    cfg = args.cfg if args.cfg is not None else float(p["cfg"])
    if not 1 <= steps <= 80:
        raise SystemExit("BLOCKED: steps must be 1..80")
    if not 0.0 <= cfg <= 30.0:
        raise SystemExit("BLOCKED: cfg must be 0..30")

    count = 1 if mode == "single" else int(args.count)
    cols = 1 if mode == "single" else int(args.cols or min(3, count))
    if mode == "sheet":
        if not 2 <= count <= 12:
            raise SystemExit("BLOCKED: contact-sheet count must be 2..12")
        if not 1 <= cols <= min(6, count):
            raise SystemExit("BLOCKED: contact-sheet cols must be 1..min(6,count)")

    return {
        "schema": "fortress-image-render-config.v1",
        "preset": args.preset,
        "description": p.get("description", ""),
        "mode": mode,
        "prompt": args.prompt.strip(),
        "seed": seed,
        "checkpoint": p["checkpoint"],
        "managedAssetKeys": p.get("managedAssetKeys") or [],
        "loras": loras,
        "positivePrefix": p.get("positivePrefix", ""),
        "negative": negative,
        "steps": steps,
        "cfg": cfg,
        "sampler": args.sampler or p["sampler"],
        "scheduler": args.scheduler or p["scheduler"],
        "width": width,
        "height": height,
        "count": count,
        "cols": cols,
    }


def env_for_config(config: dict, registry: dict) -> dict:
    env = os.environ.copy()
    env.update({
        "FORTRESS_IMAGE_PROFILE": config["preset"],
        "FORTRESS_IMAGE_CHECKPOINT": config["checkpoint"],
        "FORTRESS_IMAGE_LORAS_JSON": json.dumps(config["loras"], separators=(",", ":")),
        "FORTRESS_IMAGE_POSITIVE_PREFIX": config["positivePrefix"],
        "FORTRESS_IMAGE_NEGATIVE": config["negative"],
        "FORTRESS_IMAGE_STEPS": str(config["steps"]),
        "FORTRESS_IMAGE_CFG": str(config["cfg"]),
        "FORTRESS_IMAGE_SAMPLER": config["sampler"],
        "FORTRESS_IMAGE_SCHEDULER": config["scheduler"],
        "FORTRESS_IMAGE_WIDTH": str(config["width"]),
        "FORTRESS_IMAGE_HEIGHT": str(config["height"]),
        "FORTRESS_IMAGE_MODE": config["mode"],
        "FORTRESS_IMAGE_COUNT": str(config["count"]),
        "FORTRESS_IMAGE_CONTACT_COLS": str(config["cols"]),
        "FORTRESS_IMAGE_MANAGED_ASSETS_JSON": json.dumps(
            [registry["managedAssets"][k] for k in config["managedAssetKeys"]],
            separators=(",", ":"),
        ),
    })
    return env


def exec_entry(argv: list[str], env: dict | None = None) -> None:
    if not ENTRY.is_file():
        raise SystemExit(f"BLOCKED: canonical image entry missing: {ENTRY}")
    os.execvpe("bash", ["bash", str(ENTRY), *argv], env or os.environ.copy())


def add_render_args(parser: argparse.ArgumentParser, *, sheet: bool) -> None:
    parser.add_argument("prompt", help="scene description")
    parser.add_argument("--preset", default="graphic", help="named preset; see 'presets'")
    parser.add_argument("--seed", type=int, help="explicit seed; default is a deterministic hash of the prompt")
    parser.add_argument("--size", default="preset", help="preset|portrait|square|landscape|WIDTHxHEIGHT")
    parser.add_argument("--lora", action="append", default=[], metavar="FILE@MODEL@CLIP",
                        help="stack an already-installed SD1.5 LoRA after the preset; repeatable")
    parser.add_argument("--negative-extra", default="", help="append to the preset negative prompt")
    parser.add_argument("--steps", type=int)
    parser.add_argument("--cfg", type=float)
    parser.add_argument("--sampler")
    parser.add_argument("--scheduler")
    if sheet:
        parser.add_argument("--count", type=int, default=9)
        parser.add_argument("--cols", type=int, default=3)


def main() -> None:
    registry = load_registry()
    parser = argparse.ArgumentParser(
        prog="fortress-image",
        description="Deterministic CLI for THECAULDRON's existing localhost ComfyUI renderer.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("presets", help="list named rendering presets")
    sub.add_parser("status", help="check canonical THECAULDRON transport")
    sub.add_parser("receipts", help="show the latest image receipt")

    p_models = sub.add_parser("models", help="inspect required model assets on THECAULDRON")
    p_models.add_argument("--preset", default=os.environ.get("FORTRESS_IMAGE_PROFILE", "graphic"))

    p_setup = sub.add_parser("setup", help="download and SHA-256 verify managed Hugging Face assets on THECAULDRON")
    p_setup.add_argument("--preset", default=os.environ.get("FORTRESS_IMAGE_PROFILE", "graphic"), help="preset to provision, or 'all'")

    p_doctor = sub.add_parser("doctor", help="validate transport, preset, dimensions, and model files")
    p_doctor.add_argument("--preset", default=os.environ.get("FORTRESS_IMAGE_PROFILE", "graphic"))

    p_render = sub.add_parser("render", help="render one deterministic image")
    add_render_args(p_render, sheet=False)

    p_sheet = sub.add_parser("sheet", help="render a deterministic labeled contact sheet")
    add_render_args(p_sheet, sheet=True)

    p_plan = sub.add_parser("plan", help="print the exact compiled render config without executing it")
    add_render_args(p_plan, sheet=False)
    p_plan.add_argument("--sheet", action="store_true", help="plan contact-sheet mode instead of single")

    p_generate = sub.add_parser("generate", help="legacy positional generator compatibility")
    p_generate.add_argument("prompt")
    p_generate.add_argument("seed", nargs="?")

    args = parser.parse_args()

    if args.command == "presets":
        for name, p in registry["presets"].items():
            stack = ", ".join(f"{x['filename']}@{x['model']}" for x in p.get("loras") or []) or "none"
            print(f"{name:16} {p['checkpoint']}  LoRA: {stack}")
            print(f"{'':16} {p.get('description','')}")
        return

    if args.command in {"status", "receipts"}:
        exec_entry([args.command])

    if args.command == "generate":
        argv = ["generate", args.prompt]
        if args.seed is not None:
            argv.append(args.seed)
        exec_entry(argv)

    if args.command in {"models", "setup", "doctor"}:
        preset = args.preset
        if preset == "all" and args.command != "setup":
            raise SystemExit("BLOCKED: 'all' is valid only for setup")
        if preset != "all" and preset not in registry["presets"]:
            raise SystemExit(f"BLOCKED: unknown preset {preset!r}")
        keys = []
        if preset == "all":
            for p in registry["presets"].values():
                keys.extend(p.get("managedAssetKeys") or [])
            keys = list(dict.fromkeys(keys))
            profile = "all"
            checkpoint = ""
            loras = []
        else:
            p = registry["presets"][preset]
            keys = p.get("managedAssetKeys") or []
            profile = preset
            checkpoint = p["checkpoint"]
            loras = p.get("loras") or []
        env = os.environ.copy()
        env.update({
            "FORTRESS_IMAGE_PROFILE": profile,
            "FORTRESS_IMAGE_CHECKPOINT": checkpoint,
            "FORTRESS_IMAGE_LORAS_JSON": json.dumps(loras, separators=(",", ":")),
            "FORTRESS_IMAGE_MANAGED_ASSETS_JSON": json.dumps(
                [registry["managedAssets"][k] for k in keys], separators=(",", ":")
            ),
        })
        exec_entry([args.command], env)

    mode = "sheet" if args.command == "sheet" or (args.command == "plan" and args.sheet) else "single"
    config = compile_config(args, registry, mode)
    if not config["prompt"]:
        raise SystemExit("BLOCKED: prompt is empty")
    if args.command == "plan":
        print(json.dumps(config, indent=2, ensure_ascii=False, sort_keys=True))
        return

    env = env_for_config(config, registry)
    exec_entry(["generate", config["prompt"], str(config["seed"])], env)


if __name__ == "__main__":
    main()
