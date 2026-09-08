#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

VERSION = "1.0.0"
DEFAULT_SAMPLES = 12
DEFAULT_WIDTH = 480


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def need(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"required executable not found: {name}")
    return found


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def fraction_to_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        if "/" in value:
            num, den = value.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else None
        return float(value)
    except (ValueError, ZeroDivisionError):
        return None


def probe_video(src: Path) -> dict:
    ffprobe = need("ffprobe")
    result = run([
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,avg_frame_rate:format=duration",
        "-of", "json",
        str(src),
    ])
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    if not streams:
        raise RuntimeError(f"no video stream found: {src}")
    stream = streams[0]
    duration = float((payload.get("format") or {}).get("duration") or 0.0)
    if duration <= 0:
        raise RuntimeError(f"invalid/unknown duration for {src}")
    fps = fraction_to_float(stream.get("avg_frame_rate")) or fraction_to_float(stream.get("r_frame_rate"))
    return {
        "duration_seconds": duration,
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "frame_rate": fps,
    }


def build_storyboard(
    src: Path,
    dst: Path,
    *,
    source_duration: float,
    start: float | None,
    end: float | None,
    samples: int,
    width: int,
) -> dict:
    ffmpeg = need("ffmpeg")
    start_s = max(0.0, float(start or 0.0))
    end_s = min(source_duration, float(end)) if end is not None else source_duration
    if end_s <= start_s:
        raise RuntimeError(f"invalid window: start={start_s}, end={end_s}")
    window_duration = end_s - start_s
    rate = samples / window_duration
    cols = min(4, samples)
    rows = max(1, math.ceil(samples / cols))
    vf = (
        f"fps={rate:.9f},"
        f"scale={width}:-2:flags=lanczos,"
        f"tile={cols}x{rows}:nb_frames={samples}:padding=4:margin=4"
    )
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    if start_s > 0:
        cmd += ["-ss", f"{start_s:.6f}"]
    if window_duration < source_duration:
        cmd += ["-t", f"{window_duration:.6f}"]
    cmd += ["-i", str(src), "-vf", vf, "-frames:v", "1", str(dst)]
    run(cmd)
    if not dst.exists() or dst.stat().st_size == 0:
        raise RuntimeError(f"storyboard was not produced: {dst}")
    return {
        "start_seconds": start_s,
        "end_seconds": end_s,
        "window_duration_seconds": window_duration,
        "requested_samples": samples,
        "storyboard_columns": cols,
        "storyboard_rows": rows,
        "storyboard_width_per_sample": width,
        "sampling_rate_fps": rate,
    }


def observe_one(
    src: Path,
    out_dir: Path,
    *,
    label: str,
    samples: int,
    width: int,
    start: float | None,
    end: float | None,
) -> dict:
    src = src.expanduser().resolve()
    if not src.exists() or not src.is_file():
        raise RuntimeError(f"video not found: {src}")
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata = probe_video(src)
    storyboard_path = out_dir / "storyboard.jpg"
    sampling = build_storyboard(
        src,
        storyboard_path,
        source_duration=metadata["duration_seconds"],
        start=start,
        end=end,
        samples=samples,
        width=width,
    )
    manifest = {
        "schema": "home-center.kinesis-flight-recorder.video.v1",
        "recorder_version": VERSION,
        "state": "DONE",
        "label": label,
        "created_at": utc_now(),
        "source": {
            "path": str(src),
            "sha256": sha256_file(src),
            **metadata,
        },
        "sampling": sampling,
        "artifacts": {
            "storyboard": str(storyboard_path.resolve()),
        },
        "evidence_contract": {
            "script_observed": [
                "source hash",
                "video metadata",
                "bounded uniform storyboard generation",
            ],
            "not_proven_by_script": [
                "intent",
                "contact semantics",
                "felt state",
                "precise sub-sample timing",
                "performance quality",
            ],
        },
    }
    atomic_json(out_dir / "manifest.json", manifest)
    return manifest


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic sparse video witness for Embodied Kinesis / KEY-KI analysis."
    )
    parser.add_argument("video", type=Path)
    parser.add_argument("--compare", type=Path, default=None)
    parser.add_argument("--relation", default="adversarial_opposite")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--start", type=float, default=None)
    parser.add_argument("--end", type=float, default=None)
    parser.add_argument("--detach", action="store_true")
    parser.add_argument("--foreground", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def default_out(video: Path) -> Path:
    return Path.cwd() / f"{video.stem}.kinesis-flight-recorder"


def child_command(args: argparse.Namespace, out_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        str(args.video),
        "--out", str(out_dir),
        "--samples", str(args.samples),
        "--width", str(args.width),
        "--foreground",
    ]
    if args.compare is not None:
        cmd += ["--compare", str(args.compare), "--relation", args.relation]
    if args.start is not None:
        cmd += ["--start", str(args.start)]
    if args.end is not None:
        cmd += ["--end", str(args.end)]
    return cmd


def detach(args: argparse.Namespace, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    command = child_command(args, out_dir)
    launch = {
        "schema": "home-center.kinesis-flight-recorder.launch.v1",
        "state": "STARTING",
        "created_at": utc_now(),
        "command": command,
        "out_dir": str(out_dir.resolve()),
    }
    atomic_json(out_dir / "launch.json", launch)
    log_path = out_dir / "run.log"
    with log_path.open("ab", buffering=0) as log:
        kwargs: dict = {
            "stdin": subprocess.DEVNULL,
            "stdout": log,
            "stderr": subprocess.STDOUT,
            "cwd": str(Path.cwd()),
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(command, **kwargs)
    launch.update({"state": "STARTED", "pid": proc.pid, "log": str(log_path.resolve())})
    atomic_json(out_dir / "launch.json", launch)
    print(json.dumps({
        "state": "STARTED",
        "pid": proc.pid,
        "out_dir": str(out_dir.resolve()),
        "status": str((out_dir / "status.json").resolve()),
        "result": str((out_dir / "result.json").resolve()),
    }, sort_keys=True))
    return 0


def foreground(args: argparse.Namespace, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    status_path = out_dir / "status.json"
    atomic_json(status_path, {
        "schema": "home-center.kinesis-flight-recorder.status.v1",
        "state": "RUNNING",
        "started_at": utc_now(),
        "recorder_version": VERSION,
    })
    try:
        if args.samples < 2 or args.samples > 64:
            raise RuntimeError("--samples must be between 2 and 64")
        if args.width < 160 or args.width > 1920:
            raise RuntimeError("--width must be between 160 and 1920")
        primary = observe_one(
            args.video,
            out_dir / "primary",
            label="primary",
            samples=args.samples,
            width=args.width,
            start=args.start,
            end=args.end,
        )
        pair = None
        if args.compare is not None:
            adversary = observe_one(
                args.compare,
                out_dir / "adversary",
                label="adversary",
                samples=args.samples,
                width=args.width,
                start=args.start,
                end=args.end,
            )
            pair = {
                "relation": args.relation,
                "primary_manifest": str((out_dir / "primary" / "manifest.json").resolve()),
                "adversary_manifest": str((out_dir / "adversary" / "manifest.json").resolve()),
                "primary_sha256": primary["source"]["sha256"],
                "adversary_sha256": adversary["source"]["sha256"],
            }
            atomic_json(out_dir / "pair.json", {
                "schema": "home-center.kinesis-flight-recorder.pair.v1",
                "created_at": utc_now(),
                **pair,
            })
        result = {
            "schema": "home-center.kinesis-flight-recorder.result.v1",
            "state": "DONE",
            "completed_at": utc_now(),
            "recorder_version": VERSION,
            "mode": "pair" if pair else "single",
            "primary_manifest": str((out_dir / "primary" / "manifest.json").resolve()),
            "pair": pair,
            "model_polling_required": False,
        }
        atomic_json(out_dir / "result.json", result)
        atomic_json(status_path, {
            "schema": "home-center.kinesis-flight-recorder.status.v1",
            "state": "DONE",
            "completed_at": utc_now(),
            "result": str((out_dir / "result.json").resolve()),
        })
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        atomic_json(status_path, {
            "schema": "home-center.kinesis-flight-recorder.status.v1",
            "state": "FAILED",
            "failed_at": utc_now(),
            "error": f"{type(exc).__name__}: {exc}",
        })
        raise


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv if argv is not None else sys.argv[1:]))
    out_dir = (args.out or default_out(args.video)).expanduser().resolve()
    if args.detach and not args.foreground:
        return detach(args, out_dir)
    return foreground(args, out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
