#!/usr/bin/env python3
import argparse
import json
import os
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("HC_SWARM_STATE_DIR", "~/.local/state/home-center/vlad-swarm")).expanduser()


def main():
    ap = argparse.ArgumentParser(description="Queue a pixel forge job for the Vlad swarm daemon")
    ap.add_argument("prompt")
    ap.add_argument("--output", required=True)
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--colors", type=int, default=32)
    ap.add_argument("--format", choices=("png", "webp"), default="png")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--guidance", type=float, default=7.5)
    ap.add_argument("--render-size", type=int, default=512, choices=(256, 384, 512))
    ap.add_argument("--negative")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    inbox = STATE_DIR / "pixel-inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    job_id = f"{int(time.time() * 1000)}-{os.getpid()}"
    pending = inbox / f".{job_id}.json.tmp"
    final = inbox / f"{job_id}.json"
    data = {
        "kind": "pixel.forge.job.v1",
        "prompt": args.prompt,
        "output": str(Path(args.output).expanduser()),
        "size": args.size,
        "colors": args.colors,
        "format": args.format,
        "seed": args.seed,
        "steps": args.steps,
        "guidance": args.guidance,
        "renderSize": args.render_size,
        "timeout": args.timeout,
    }
    if args.negative:
        data["negative"] = args.negative
    pending.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pending.replace(final)
    print(json.dumps({"ok": True, "job": job_id, "path": str(final)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
