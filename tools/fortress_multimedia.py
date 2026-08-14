#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HOME = Path.home()
REPO = Path(os.environ.get("FORTRESS_HOME_CENTER", "/storage/emulated/0/Documents/GodotProjects/home-center"))
CONFIG = REPO / "config/fortress-multimedia.json"


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return None


def _read_int(path: Path) -> int | None:
    raw = _read_text(path)
    try:
        return int(raw) if raw is not None else None
    except ValueError:
        return None


def load_config() -> dict[str, Any]:
    if not CONFIG.exists():
        raise SystemExit(f"BLOCKED: missing multimedia config: {CONFIG}")
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def command_inventory() -> dict[str, str | None]:
    names = ["python", "python3", "node", "ffmpeg", "ffplay", "godot", "godot4", "blender", "cn", "termux-info"]
    return {name: shutil.which(name) for name in names}


def memory_profile() -> dict[str, int | None]:
    total = available = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                total = int(line.split()[1]) * 1024
            elif line.startswith("MemAvailable:"):
                available = int(line.split()[1]) * 1024
    except Exception:
        pass
    return {"totalBytes": total, "availableBytes": available}


def thermal_profile() -> dict[str, Any]:
    readings = []
    root = Path("/sys/class/thermal")
    if root.exists():
        for zone in sorted(root.glob("thermal_zone*")):
            raw = _read_int(zone / "temp")
            if raw is None:
                continue
            c = raw / 1000.0 if abs(raw) > 1000 else float(raw)
            readings.append({"zone": zone.name, "type": _read_text(zone / "type"), "celsius": round(c, 1)})
    return {"zones": readings[:32], "maxCelsius": max((x["celsius"] for x in readings), default=None)}


def battery_profile() -> dict[str, Any]:
    root = Path("/sys/class/power_supply/battery")
    return {
        "capacityPercent": _read_int(root / "capacity"),
        "status": _read_text(root / "status"),
        "temperatureRaw": _read_int(root / "temp"),
    }


def android_property(name: str) -> str | None:
    getprop = shutil.which("getprop")
    if not getprop:
        return None
    try:
        out = subprocess.run([getprop, name], check=False, capture_output=True, text=True, timeout=2)
        value = out.stdout.strip()
        return value or None
    except Exception:
        return None


def gpu_profile() -> dict[str, Any]:
    candidates = {
        "kgslGpuClock": "/sys/class/kgsl/kgsl-3d0/gpuclk",
        "kgslMaxGpuClock": "/sys/class/kgsl/kgsl-3d0/max_gpuclk",
        "kgslBusyPercent": "/sys/class/kgsl/kgsl-3d0/gpubusy",
    }
    return {
        "boardPlatform": android_property("ro.board.platform"),
        "hardwareEgl": android_property("ro.hardware.egl"),
        "hardwareVulkan": android_property("ro.hardware.vulkan"),
        **{key: _read_text(Path(path)) for key, path in candidates.items()},
    }


def media_profile(commands: dict[str, str | None]) -> dict[str, Any]:
    ffmpeg = commands.get("ffmpeg")
    codecs: list[str] = []
    if ffmpeg:
        try:
            proc = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], check=False, capture_output=True, text=True, timeout=5)
            text = proc.stdout + proc.stderr
            for marker in ("mediacodec", "h264", "hevc", "vp9", "av1", "aac", "opus"):
                if marker.lower() in text.lower():
                    codecs.append(marker)
        except Exception:
            pass
    return {"ffmpegPresent": bool(ffmpeg), "ffplayPresent": bool(commands.get("ffplay")), "encoderMarkers": codecs}


def profile() -> dict[str, Any]:
    commands = command_inventory()
    try:
        disk = shutil.disk_usage(REPO if REPO.exists() else HOME)
        storage = {"totalBytes": disk.total, "freeBytes": disk.free}
    except Exception:
        storage = {"totalBytes": None, "freeBytes": None}
    return {
        "schemaVersion": "home-center.fortress-device-profile.v1",
        "host": os.uname().nodename if hasattr(os, "uname") else None,
        "cpu": {"logicalCount": os.cpu_count()},
        "memory": memory_profile(),
        "storage": storage,
        "thermal": thermal_profile(),
        "battery": battery_profile(),
        "gpu": gpu_profile(),
        "commands": commands,
        "media": media_profile(commands),
    }


def choose_lanes(device: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    commands = device.get("commands", {})
    media = device.get("media", {})
    thermal = device.get("thermal", {})
    max_c = thermal.get("maxCelsius")
    hot = isinstance(max_c, (int, float)) and max_c >= 45.0

    phone_media = bool(commands.get("ffmpeg"))
    hardware_codec = "mediacodec" in media.get("encoderMarkers", [])
    phone_game = bool(commands.get("godot") or commands.get("godot4"))
    phone_blender = bool(commands.get("blender"))

    return {
        "phoneLocal": {"enabled": True, "throttled": hot, "reason": "thermal guard" if hot else "local-first"},
        "phoneMedia": {"enabled": phone_media and not hot, "hardwareCodecDetected": hardware_codec},
        "game": {"preferred": "phone" if phone_game and not hot else "fleet", "phoneExecutable": commands.get("godot") or commands.get("godot4")},
        "blender": {"preferred": "phone" if phone_blender and not hot else "fleet-gpu", "phoneExecutable": commands.get("blender")},
        "cloudEscalationAllowed": bool(cfg.get("policy", {}).get("cloudEscalation", False)),
    }


def combined_plan() -> dict[str, Any]:
    cfg = load_config()
    device = profile()
    lanes = choose_lanes(device, cfg)
    stages = [
        {"stage": 1, "name": "sense-and-plan", "lane": "phone-local", "organs": ["venice", "game"], "outputs": ["brief", "shot-list", "asset-manifest"]},
        {"stage": 2, "name": "forge-assets", "lane": lanes["blender"]["preferred"], "organs": ["blender"], "outputs": ["scene-revision", "meshes", "rigs", "animations"]},
        {"stage": 3, "name": "forge-audio", "lane": "phone-media" if lanes["phoneMedia"]["enabled"] else "fleet", "organs": ["venice", "media"], "outputs": ["stems", "sfx", "narration"]},
        {"stage": 4, "name": "assemble-game", "lane": lanes["game"]["preferred"], "organs": ["game", "media"], "outputs": ["playable-build", "capture-plan"]},
        {"stage": 5, "name": "render-and-package", "lane": "phone-media" if lanes["phoneMedia"]["enabled"] else "fleet-gpu", "organs": ["media", "blender", "game"], "outputs": ["video", "screenshots", "package", "receipt"]},
    ]
    return {"schemaVersion": "home-center.combined-arms-plan.v1", "device": device, "lanes": lanes, "stages": stages}


def run_venice(payload: dict[str, Any]) -> dict[str, Any]:
    script = REPO / "tools/venice_reactor.py"
    if not script.exists():
        return {"ok": False, "blocked": f"missing {script}"}
    proc = subprocess.run(
        [shutil.which("python") or sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
        cwd=REPO,
    )
    out = proc.stdout.strip()
    try:
        parsed = json.loads(out) if out else {}
    except json.JSONDecodeError:
        parsed = {"stdout": out}
    return {"ok": proc.returncode == 0, "exitCode": proc.returncode, "result": parsed, "stderr": proc.stderr.strip()}


def run_recipe(name: str) -> dict[str, Any]:
    cfg = load_config()
    recipe = cfg.get("recipes", {}).get(name)
    if not recipe:
        return {"ok": False, "blocked": f"unknown recipe: {name}", "known": sorted(cfg.get("recipes", {}))}
    action = recipe.get("action")
    if action == "profile":
        return {"ok": True, "recipe": name, "result": profile()}
    if action == "plan":
        return {"ok": True, "recipe": name, "result": combined_plan()}
    if action == "venice-json":
        return {"recipe": name, **run_venice(dict(recipe.get("payload", {})))}
    return {"ok": False, "blocked": f"unsupported recipe action: {action}"}


def status() -> dict[str, Any]:
    cfg = load_config()
    device = profile()
    return {
        "schemaVersion": "home-center.fortress-multimedia-status.v1",
        "config": str(CONFIG),
        "organs": sorted(cfg.get("organs", {})),
        "recipes": sorted(cfg.get("recipes", {})),
        "lanes": choose_lanes(device, cfg),
        "device": device,
    }


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv == ["status"]:
        result = status()
    elif argv == ["profile"]:
        result = profile()
    elif argv == ["plan"]:
        result = combined_plan()
    elif len(argv) == 2 and argv[0] == "run":
        result = run_recipe(argv[1])
    elif argv == ["catalog"]:
        cfg = load_config()
        result = {"organs": cfg.get("organs", {}), "lanes": cfg.get("lanes", {}), "recipes": cfg.get("recipes", {})}
    else:
        print("usage: fortress-multimedia [status|profile|plan|catalog|run <recipe>]", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
