#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, shlex, subprocess, sys, time, wave
from pathlib import Path

ROOT = Path(os.environ.get("FORTRESS_CLIP_ROOT", "/storage/emulated/0/Documents/FortressAudio/Clips"))
INDEX = ROOT / "catalog.json"
POCKET = Path.home() / "bin/pocket-tts-phone"
RISH_CANDIDATES = [Path.home()/"bin/rish", Path.home()/"rish", Path("/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish"), Path("/storage/emulated/0/Documents/rish"), Path("/storage/emulated/0/Download/rish")]
COMPONENT = "com.dclar.homecenter/.PocketTtsPlaybackActivity"
LOG_TAG = "PocketTtsDuck"


def slugify(v: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", v.strip().lower()).strip("-")
    if not s: raise SystemExit("slug/title must contain letters or digits")
    return s


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()


def load() -> dict:
    if not INDEX.exists(): return {"schema":"fortress.clip-catalog.v1","clips":{}}
    data = json.loads(INDEX.read_text("utf-8")); data.setdefault("clips", {})
    return data


def save(data: dict) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = INDEX.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", "utf-8")
    os.replace(tmp, INDEX)


def rish() -> Path:
    for p in RISH_CANDIDATES:
        if p.is_file(): return p
    raise SystemExit("BLOCKED: Shizuku rish unavailable")


def run_rish(cmd: str, timeout=30) -> str:
    p = subprocess.run([str(rish()), "-c", cmd], capture_output=True, text=True, timeout=timeout)
    out = "\n".join(x.strip() for x in (p.stdout,p.stderr) if x.strip())
    if p.returncode: raise SystemExit(out or f"rish failed ({p.returncode})")
    return out


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w: return w.getnframes()/float(w.getframerate())


def verify_playback(path: Path) -> dict:
    secs = duration(path)
    launch = run_rish("am start -W -n "+shlex.quote(COMPONENT)+" --es file "+shlex.quote(str(path)), 20)
    time.sleep(max(.15, secs+.75))
    logs = run_rish("logcat -d -v epoch -s "+shlex.quote(LOG_TAG+":I")+" '*:S'",20)
    token = "play_start file="+str(path)
    pos = logs.rfind(token)
    if pos < 0: raise SystemExit("playback unverified: missing play_start")
    tail = logs[pos:]
    if "play_error" in tail or "play_rejected" in tail or "play_finish reason=completed" not in tail:
        raise SystemExit("playback unverified: completion receipt missing/error")
    return {"playbackVerified":True,"audioSeconds":round(secs,3),"component":COMPONENT}


def forge(args):
    slug = slugify(args.slug or args.title)
    data = load()
    if slug in data["clips"] and not args.replace: raise SystemExit(f"clip exists: {slug}; use --replace")
    if not POCKET.is_file(): raise SystemExit(f"BLOCKED: missing {POCKET}")
    ROOT.mkdir(parents=True, exist_ok=True)
    out = ROOT / f"{slug}.wav"
    tmpdir = ROOT / f".forge-{os.getpid()}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    cmd=[str(POCKET),"generate","--text",args.text,"--voice",args.voice,"--language",args.language]
    p=subprocess.run(cmd,cwd=tmpdir,capture_output=True,text=True,timeout=300)
    if p.returncode: raise SystemExit((p.stderr or p.stdout or "Pocket TTS failed")[-4000:])
    generated=tmpdir/"tts_output.wav"
    if not generated.is_file(): raise SystemExit("Pocket TTS completed without tts_output.wav")
    os.replace(generated,out)
    try: tmpdir.rmdir()
    except OSError: pass
    rec={"slug":slug,"title":args.title,"text":args.text,"voice":args.voice,"language":args.language,"path":str(out),"sha256":sha256(out),"bytes":out.stat().st_size,"audioSeconds":round(duration(out),3),"createdAt":int(time.time()),"renderEngine":"pocket-tts-phone","replayRequiresAI":False}
    data["clips"][slug]=rec; save(data)
    print(json.dumps(rec,ensure_ascii=False))


def play(args):
    data=load(); slug=slugify(args.slug)
    rec=data["clips"].get(slug)
    if not rec: raise SystemExit(f"unknown clip: {slug}")
    path=Path(rec["path"])
    if not path.is_file(): raise SystemExit(f"missing audio file: {path}")
    if sha256(path)!=rec["sha256"]: raise SystemExit("BLOCKED: clip SHA-256 mismatch")
    receipt={"slug":slug,"sha256":rec["sha256"],"renderEngine":rec.get("renderEngine"),"replaySynthesisUsed":False,**verify_playback(path)}
    print(json.dumps(receipt,ensure_ascii=False))


def main():
    p=argparse.ArgumentParser(prog="fortress-clip",description="Deterministic durable audio clip catalog; synthesize once, replay without AI")
    sub=p.add_subparsers(dest="cmd",required=True)
    f=sub.add_parser("forge"); f.add_argument("slug",nargs="?"); f.add_argument("--title",required=True); f.add_argument("--text",required=True); f.add_argument("--voice",default="michael"); f.add_argument("--language",default="english"); f.add_argument("--replace",action="store_true"); f.set_defaults(fn=forge)
    q=sub.add_parser("play"); q.add_argument("slug"); q.set_defaults(fn=play)
    l=sub.add_parser("list"); l.set_defaults(fn=lambda a: print(json.dumps(list(load()["clips"].values()),ensure_ascii=False,indent=2)))
    s=sub.add_parser("show"); s.add_argument("slug"); s.set_defaults(fn=lambda a: print(json.dumps(load()["clips"].get(slugify(a.slug)),ensure_ascii=False,indent=2)))
    args=p.parse_args(); args.fn(args)
if __name__=="__main__": main()
