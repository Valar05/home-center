#!/usr/bin/env python3
"""Durable She-Ra campaign intake for Fortress Online.

The operator starts intake from the Home Center notification. Questions are asked
through Termux dialogs, answers are persisted after every step, and the finished
commission is submitted to the existing tmux-backed Adam surface.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center")).expanduser() / "campaign-intake"
STATE.mkdir(parents=True, exist_ok=True)

QUESTIONS = [
    ("desire", "She-Ra: What do you actually want at the end of this campaign? Not the implementation. The treasure."),
    ("pain", "She-Ra: What is making you furious, stuck, or disappointed right now? Give me the wound, not the polite version."),
    ("proof", "She-Ra: What would you personally accept as proof that this is real and usable?"),
    ("boundary", "She-Ra: What must I absolutely not change, replace, rename, route around, or 'improve' away?"),
    ("priority", "She-Ra: If I can only bring one useful thing home first, what has to work first?"),
    ("secret", "She-Ra: What are you assuming or hoping for that you have not said out loud yet? This is the part I am thirsty for."),
]


def atomic(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def dialog(title: str, prompt: str) -> str:
    if not which("termux-dialog"):
        raise RuntimeError("termux-dialog missing; install/enable Termux:API")
    p = subprocess.run(["termux-dialog", "text", "-t", title, "-i", prompt], text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "termux-dialog failed").strip())
    try:
        data = json.loads(p.stdout)
    except Exception as exc:
        raise RuntimeError(f"termux-dialog returned unreadable JSON: {exc}") from exc
    if int(data.get("code", 0)) < 0:
        raise KeyboardInterrupt
    return str(data.get("text") or "").strip()


def notify(title: str, content: str, mode: str = "main") -> None:
    if not which("termux-notification"):
        return
    cmd = f"cd {ROOT!s} && python3 tools/campaign_intake_shera.py {mode}"
    subprocess.run([
        "termux-notification", "--id", "6420", "--title", title, "--content", content,
        "--priority", "high", "--ongoing", "true", "--button1", "Continue",
        "--button1-action", f"bash -l -c '{cmd}'", "--button2", "Status",
        "--button2-action", f"bash -l -c 'cd {ROOT!s} && python3 tools/campaign_intake_shera.py status'",
        "--button3", "Cancel", "--button3-action", f"bash -l -c 'cd {ROOT!s} && python3 tools/campaign_intake_shera.py cancel'",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def latest() -> dict:
    p = STATE / "current.json"
    try:
        v = json.loads(p.read_text(encoding="utf-8")); return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def save(obj: dict) -> None:
    atomic(STATE / "current.json", obj)
    atomic(STATE / f"{obj['intakeId']}.json", obj)


def compile_commission(obj: dict) -> str:
    a = obj["answers"]
    return (
        "FORTRESS CAMPAIGN — compiled from She-Ra operator intake.\n\n"
        f"Desired outcome:\n{a.get('desire','')}\n\n"
        f"Current pain/failure:\n{a.get('pain','')}\n\n"
        f"Acceptance proof:\n{a.get('proof','')}\n\n"
        f"Mission boundary / forbidden substitutions:\n{a.get('boundary','')}\n\n"
        f"First useful priority:\n{a.get('priority','')}\n\n"
        f"Unspoken assumption/hope revealed during intake:\n{a.get('secret','')}\n\n"
        "Operate under existing Fortress Online doctrine. Preserve requested tool, owner, lane, evidence standard, and delivery surface. "
        "Use tmux-backed Home Center supervision, notifications for operator visibility, durable checkpoints, self-repair through recoverable failures, "
        "and separate requested/implemented/deployed/callable/verified/delivered/accepted state. Do not stop at a plan or local-only proof."
    )


def start_or_continue() -> int:
    obj = latest()
    if not obj or obj.get("status") in {"SUBMITTED", "CANCELLED", "COMPLETE"}:
        obj = {"schema":"fortress-shera-intake-v1","intakeId":time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6],"status":"INTAKE","index":0,"answers":{},"startedAtEpoch":int(time.time())}
        save(obj)
    idx = int(obj.get("index", 0))
    if idx >= len(QUESTIONS):
        return submit(obj)
    key, q = QUESTIONS[idx]
    notify("She-Ra intake", f"Question {idx+1}/{len(QUESTIONS)} — {q}")
    try:
        answer = dialog(f"She-Ra {idx+1}/{len(QUESTIONS)}", q)
    except KeyboardInterrupt:
        obj["status"] = "PAUSED"; obj["updatedAtEpoch"] = int(time.time()); save(obj); notify("She-Ra intake paused", "Your answers are safe. Continue when you want the interrogation to resume."); return 0
    except Exception as exc:
        obj["status"] = "BLOCKED"; obj["error"] = str(exc); obj["updatedAtEpoch"] = int(time.time()); save(obj); notify("She-Ra intake blocked", str(exc)); return 2
    obj["answers"][key] = answer
    obj["index"] = idx + 1
    obj["status"] = "INTAKE"
    obj["updatedAtEpoch"] = int(time.time())
    save(obj)
    if obj["index"] >= len(QUESTIONS):
        return submit(obj)
    notify("She-Ra is not done with you", f"Answer saved. {len(QUESTIONS)-obj['index']} question(s) remain.")
    return 0


def submit(obj: dict) -> int:
    commission = compile_commission(obj)
    obj["compiledCommission"] = commission
    obj["status"] = "SUBMITTING"
    save(obj)
    p = subprocess.run([str(Path.home()/"bin"/"adam"), commission], text=True, capture_output=True)
    obj["submitRc"] = p.returncode
    obj["submitStdout"] = p.stdout[-6000:]
    obj["submitStderr"] = p.stderr[-6000:]
    obj["status"] = "SUBMITTED" if p.returncode == 0 else "BLOCKED"
    obj["submittedAtEpoch"] = int(time.time())
    save(obj)
    notify("Campaign submitted" if p.returncode == 0 else "Campaign submit blocked", (p.stdout or p.stderr or obj["status"])[-700:])
    print(p.stdout, end="")
    if p.stderr: print(p.stderr, file=sys.stderr, end="")
    return p.returncode


def status() -> int:
    obj = latest()
    if not obj:
        print("She-Ra intake: idle")
        return 0
    print(json.dumps({k:obj.get(k) for k in ("intakeId","status","index","startedAtEpoch","updatedAtEpoch","submittedAtEpoch","error")}, indent=2, ensure_ascii=False))
    notify("She-Ra intake status", f"{obj.get('status')} — question {min(int(obj.get('index',0))+1,len(QUESTIONS))}/{len(QUESTIONS)}")
    return 0


def cancel() -> int:
    obj = latest()
    if not obj: return 0
    obj["status"] = "CANCELLED"; obj["updatedAtEpoch"] = int(time.time()); save(obj)
    notify("She-Ra intake cancelled", "The intake record remains durable; no campaign was submitted.")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd in {"start","continue"}: return start_or_continue()
    if cmd == "status": return status()
    if cmd == "cancel": return cancel()
    print("usage: campaign_intake_shera.py start|continue|status|cancel", file=sys.stderr); return 64

if __name__ == "__main__":
    raise SystemExit(main())
