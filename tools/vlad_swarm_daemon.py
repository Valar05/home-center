#!/usr/bin/env python3
import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("HC_SWARM_STATE_DIR", "~/.local/state/home-center/vlad-swarm")).expanduser()
RISH = os.environ.get("HC_RISH", "rish")
INTERVAL = int(os.environ.get("HC_SWARM_INTERVAL", "30"))


def now():
    return int(time.time())


def run(cmd, timeout=20):
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    return {
        "cmd": cmd,
        "rc": p.returncode,
        "stdout": p.stdout.strip()[-4000:],
        "stderr": p.stderr.strip()[-4000:],
    }


def rish(command):
    return run([RISH, "-c", command])


def append_receipt(event):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    event = {"at": now(), **event}
    with (STATE_DIR / "receipts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    (STATE_DIR / "last.json").write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def phone_health():
    probe = rish("id")
    shizuku_ok = probe["rc"] == 0
    event = {"kind": "phone.shizuku.probe", "ok": shizuku_ok, "result": probe}
    append_receipt(event)
    if not shizuku_ok:
        return False

    wifi = rish("cmd wifi status")
    text = (wifi["stdout"] + "\n" + wifi["stderr"]).lower()
    enabled = "wifi is enabled" in text or "enabled: true" in text
    connected = any(k in text for k in ("connected", "ssid", "networkid")) and "disconnected" not in text
    append_receipt({"kind": "phone.wlan.probe", "ok": wifi["rc"] == 0, "enabled": enabled, "connected": connected, "result": wifi})

    if not enabled:
        repair = rish("cmd wifi set-wifi-enabled enabled")
        append_receipt({"kind": "phone.wlan.enable", "ok": repair["rc"] == 0, "result": repair})
    elif not connected:
        scan = rish("cmd wifi start-scan")
        append_receipt({"kind": "phone.wlan.scan", "ok": scan["rc"] == 0, "result": scan})
    return True


def process_review_inbox(repo_root):
    inbox = STATE_DIR / "review-inbox"
    done = STATE_DIR / "review-done"
    inbox.mkdir(parents=True, exist_ok=True)
    done.mkdir(parents=True, exist_ok=True)
    for job in sorted(inbox.glob("*.json")):
        data = json.loads(job.read_text(encoding="utf-8"))
        repo = data.get("repo") or repo_root
        base = data.get("base", "HEAD~1")
        head = data.get("head", "HEAD")
        acceptance = data.get("acceptance", "")
        receipt_path = done / (job.stem + ".receipt.json")
        cmd = [
            "python3", str(Path(repo_root) / "tools" / "venice_review.py"),
            "--repo", repo,
            "--base", base,
            "--head", head,
            "--acceptance", acceptance,
            "--receipt", str(receipt_path),
        ]
        result = run(cmd, timeout=int(data.get("timeout", 180)))
        append_receipt({"kind": "venice.review", "job": job.name, "ok": result["rc"] == 0, "result": result, "receipt": str(receipt_path)})
        job.rename(done / job.name)


def heartbeat(repo_root):
    shizuku_ok = phone_health()
    process_review_inbox(repo_root)
    append_receipt({"kind": "swarm.heartbeat", "ok": True, "shizuku": shizuku_ok})


def main():
    ap = argparse.ArgumentParser(description="Deterministic Vlad swarm keeper")
    ap.add_argument("--repo", default=os.environ.get("HC_REPO_ROOT", "."))
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=INTERVAL)
    args = ap.parse_args()
    repo_root = str(Path(args.repo).resolve())
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    append_receipt({"kind": "swarm.start", "ok": True, "repo": repo_root, "interval": args.interval})
    while True:
        try:
            heartbeat(repo_root)
        except Exception as exc:
            append_receipt({"kind": "swarm.error", "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        if args.once:
            return 0
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
