#!/usr/bin/env python3
"""Ritsu voice campaign: patch existing relay's local WAV enqueue, generate, send, verify.
No alternative transport. Run on THECAULDRON under existing Python installations.
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys, time, urllib.request, urllib.error, uuid, wave

ROOT=pathlib.Path(r"C:\Users\dclar\Documents\Codex\Venice\PocketTTS\embodiment_campaign")
TURBO=pathlib.Path(r"C:\Users\dclar\workspace\ritsu-chatterbox-turbo")
GENERATOR=pathlib.Path(r"C:\Users\dclar\workspace\home-center\tools\campaigns\ritsu_turbo_generate.py")
PYTHON=TURBO/".venv"/"Scripts"/"python.exe"
RELAY=ROOT/"relay.py"
HOST="100.68.37.106"
PORT=19643
MARKER="__TURBO_WAV__:"
SENTINEL="filename,_=resolve(text,character) if text != '__TURBO_SAMPLE_20261021__' else (r'C:\\Users\\dclar\\workspace\\ritsu-chatterbox-turbo\\ritsu-turbo-first.wav', None)"
BACKUP=ROOT/"relay.py.before-ritsu-turbo-campaign"
PATCH="""if text.startswith('__TURBO_WAV__:'):
                        basename=text[len('__TURBO_WAV__:'):]
                        candidate=(Path(r'C:\\Users\\dclar\\workspace\\ritsu-chatterbox-turbo')/'generated'/basename).resolve()
                        directory=(Path(r'C:\\Users\\dclar\\workspace\\ritsu-chatterbox-turbo')/'generated').resolve()
                        if (not basename or '/' in basename or '\\\\' in basename
                            or candidate.parent != directory or candidate.suffix.lower() != '.wav'
                            or not candidate.is_file() or candidate.stat().st_size <= 44):
                            return self.respond(400,b'{"error":"invalid_generated_wav"}')
                        filename=str(candidate)
                    else:
                        filename,_=resolve(text,character)"""
def install():
    code=RELAY.read_text(encoding="utf-8")
    if "if text.startswith('__TURBO_WAV__:'):" in code:
        print("ALREADY_PATCHED"); return
    if code.count(SENTINEL)!=1:
        raise SystemExit("BLOCKED: unexpected live relay.py; no patch applied")
    import shutil
    if not BACKUP.exists(): shutil.copy2(RELAY,BACKUP)
    changed=code.replace(SENTINEL,PATCH)
    compile(changed,str(RELAY),"exec")
    RELAY.write_text(changed,encoding="utf-8")
    print("PATCHED_RESTART_RELAY_REQUIRED")
def request(method,path,payload=None):
    token=(ROOT/"relay-token.txt").read_text(encoding="utf-8").strip()
    data=json.dumps(payload).encode() if payload is not None else None
    headers={"Authorization":"Bearer "+token}
    if data: headers["Content-Type"]="application/json"
    req=urllib.request.Request(f"http://{HOST}:{PORT}{path}",data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=20) as r:
        raw=r.read()
        return r.status,json.loads(raw) if raw else {}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--install-relay",action="store_true")
    p.add_argument("--text")
    p.add_argument("--output")
    args=p.parse_args()
    if args.install_relay: return install()
    if not args.text: p.error("--text is required")
    if not GENERATOR.is_file() or not PYTHON.is_file():
        raise SystemExit("BLOCKED: generator script or Turbo python missing")
    path=(TURBO/"generated"/(uuid.uuid4().hex+".wav")) if not args.output else pathlib.Path(args.output)
    generated=(TURBO/"generated").resolve()
    if path.resolve().parent != generated: raise SystemExit("BLOCKED: output must be directly in Turbo generated directory")
    if request("GET","/health")[0]!=200: raise SystemExit("BLOCKED: relay unhealthy")
    command=[str(PYTHON),str(GENERATOR),"--text",args.text,"--output",str(path)]
    subprocess.run(command,check=True,timeout=600)
    with wave.open(str(path),"rb") as f:
        if f.getnframes()<=0: raise SystemExit("BLOCKED: invalid WAV")
    size=path.stat().st_size
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    status,obj=request("POST","/enqueue",{"character":"ritsu","text":MARKER+path.name})
    if status!=200 or not obj.get("ok") or not obj.get("id"): raise SystemExit("BLOCKED: enqueue failed")
    ident=obj["id"]
    receipt={"status":"ENQUEUED_NOT_YET_HEARD","id":ident,"file":str(path),"size":size,"sha256":sha}
    print(json.dumps(receipt))
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        status,obj=request("GET","/next")
        if status==204 or (obj and obj.get("id")!=ident):
            receipt["status"]="CONSUMED_NOT_HEARD"
            print(json.dumps(receipt))
            break
        time.sleep(2)
    path.with_suffix(".delivery.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
if __name__=="__main__": main()
