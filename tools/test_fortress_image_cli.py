#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "fortress_image_cli.py"
PRESETS = ROOT / "tools" / "fortress_image_presets.json"
PS1 = ROOT / "tools" / "fortress_image_cauldron.ps1"


def run(*args, ok=True):
    p = subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True)
    if ok and p.returncode:
        raise AssertionError(f"{args!r} failed rc={p.returncode}\nstdout={p.stdout}\nstderr={p.stderr}")
    return p


def plan(prompt, preset="graphic", *extra):
    return json.loads(run("plan", prompt, "--preset", preset, *extra).stdout)


def main():
    registry = json.loads(PRESETS.read_text(encoding="utf-8"))
    assert registry["schema"] == "fortress-image-presets.v1"
    assert registry["managedAssets"]["dreamshaper8"]["sha256"] == "879db523c30d3b9017143d56705015e15a2cb5628762c11d086fed9538abd7fd"
    assert registry["managedAssets"]["detailTweaker"]["sha256"] == "47aaaf0d2945ca937151d61304946dd229b3f072140b85484bc93e38f2a6e2f7"

    listed = run("presets").stdout
    for name in ("plain", "fleshpunk", "dream", "dream-photo", "graphic", "graphic-thirst", "fleshpunk-plus"):
        assert name in listed, name

    prompt = "adult editorial portrait with chrome jewelry"
    a = plan(prompt, "graphic")
    b = plan(prompt, "graphic")
    thirst = plan(prompt, "graphic-thirst")
    assert a == b
    assert a["seed"] == thirst["seed"], "default seed must stay stable for A/B preset comparisons"
    assert a["checkpoint"] == "DreamShaper_8_pruned.safetensors"
    assert a["loras"][0]["filename"] == "add_detail.safetensors"
    assert "adult woman age 25+" in thirst["positivePrefix"]
    assert "minor" in thirst["negative"]

    stacked = plan(prompt, "graphic", "--lora", "my_style.safetensors@0.45@0.35")
    assert [x["filename"] for x in stacked["loras"]] == ["add_detail.safetensors", "my_style.safetensors"]
    assert stacked["loras"][1]["model"] == 0.45
    assert stacked["loras"][1]["clip"] == 0.35

    sheet = json.loads(run(
        "plan", prompt, "--preset", "graphic", "--sheet", "--count", "9", "--cols", "3"
    ).stdout)
    assert sheet["mode"] == "sheet"
    assert sheet["count"] == 9
    assert sheet["cols"] == 3

    explicit = plan(prompt, "dream", "--seed", "424242", "--size", "square")
    assert explicit["seed"] == 424242
    assert explicit["width"] == explicit["height"] == 640

    too_many = run(
        "plan", prompt, "--preset", "dream",
        "--lora", "a.safetensors@0.2",
        "--lora", "b.safetensors@0.2",
        "--lora", "c.safetensors@0.2",
        "--lora", "d.safetensors@0.2",
        "--lora", "e.safetensors@0.2",
        ok=False,
    )
    assert too_many.returncode != 0
    assert "at most four LoRAs" in too_many.stderr

    ps = PS1.read_text(encoding="utf-8")
    for fragment in (
        "http://127.0.0.1:8188",
        "CheckpointLoaderSimple",
        "LoraLoader",
        "strength_model",
        "strength_clip",
        "New-ContactSheet",
        "curl.exe",
        "huggingface.co",
        "Get-FileHash -Algorithm SHA256",
        "sourceImages",
        "seed {0}",
    ):
        assert fragment in ps, fragment
    assert "0.0.0.0:8188" not in ps

    print("FORTRESS_IMAGE_CLI_OK")


if __name__ == "__main__":
    main()
