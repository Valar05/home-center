#!/usr/bin/env python3
import argparse, base64, json, os, re, shlex, subprocess, time
from pathlib import Path

STATE_DIR = Path(os.environ.get("HC_SWARM_STATE_DIR", "~/.local/state/home-center/vlad-swarm")).expanduser()
RISH = os.environ.get("HC_RISH", "rish")
INTERVAL = int(os.environ.get("HC_SWARM_INTERVAL", "30"))
ADAM_POLL_SECONDS = float(os.environ.get("HC_ADAM_POLL_SECONDS", "1.0"))
OPERATOR_STATE_URI = "content://com.homecenter.operatoroverlay.state/state"
OPERATOR_RECEIVER = "com.homecenter.operatoroverlay/.OverlayUpdateReceiver"

def now(): return int(time.time())

def run(cmd, timeout=20, cwd=None):
 p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout,cwd=cwd)
 return {"cmd":cmd,"rc":p.returncode,"stdout":p.stdout.strip()[-8000:],"stderr":p.stderr.strip()[-8000:]}

def rish(command): return run([RISH,"-c",command])

def append_receipt(event):
 STATE_DIR.mkdir(parents=True,exist_ok=True); event={"at":now(),**event}
 with (STATE_DIR/"receipts.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(event,sort_keys=True)+"\n")
 (STATE_DIR/"last.json").write_text(json.dumps(event,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def phone_health():
 probe=rish("id"); ok=probe["rc"]==0; append_receipt({"kind":"phone.shizuku.probe","ok":ok,"result":probe})
 if not ok:return False
 wifi=rish("cmd wifi status"); text=(wifi["stdout"]+"\n"+wifi["stderr"]).lower(); enabled="wifi is enabled" in text or "enabled: true" in text; connected=any(k in text for k in ("connected","ssid","networkid")) and "disconnected" not in text
 append_receipt({"kind":"phone.wlan.probe","ok":wifi["rc"]==0,"enabled":enabled,"connected":connected,"result":wifi})
 if not enabled:append_receipt({"kind":"phone.wlan.enable","ok":(x:=rish("cmd wifi set-wifi-enabled enabled"))["rc"]==0,"result":x})
 elif not connected:append_receipt({"kind":"phone.wlan.scan","ok":(x:=rish("cmd wifi start-scan"))["rc"]==0,"result":x})
 return True

def _operator_field(raw,name,default=""):
 match=re.search(rf"\b{re.escape(name)}=([^,\n]*)",raw); return match.group(1).strip() if match else default

def operator_heartbeat():
 result=rish("am broadcast --receiver-foreground -a com.homecenter.operatoroverlay.HEARTBEAT -n "+OPERATOR_RECEIVER)
 append_receipt({"kind":"adam.overlay.heartbeat","ok":result["rc"]==0,"result":result})

def operator_update(text,source):
 return rish("am broadcast --receiver-foreground -a com.homecenter.operatoroverlay.UPDATE -n "+OPERATOR_RECEIVER+f" --es latestText {shlex.quote(str(text)[:8000])} --es source {shlex.quote(str(source)[:80])}")

def _last_adam_request_id():
 try:return int((STATE_DIR/"adam-last-request-id").read_text(encoding="utf-8").strip())
 except Exception:return 0

def _set_last_adam_request_id(value):
 STATE_DIR.mkdir(parents=True,exist_ok=True); (STATE_DIR/"adam-last-request-id").write_text(str(int(value))+"\n",encoding="utf-8")

def _display(result):
 display=result["stdout"] or result["stderr"] or f"request exited {result['rc']}"
 try:
  parsed=json.loads(result["stdout"]); display=parsed.get("response") or parsed.get("stdout") or parsed.get("detail") or parsed.get("error") or display
  if parsed.get("job") and not parsed.get("response"):display=f"Hands queued {parsed['job'].get('id','')}"
  if parsed.get("stderr"):display=(str(display)+"\n"+str(parsed["stderr"])).strip()
 except Exception:pass
 return display

def _route_overlay(repo_root,mode,text):
 clean=text.strip(); lower=clean.lower()
 if lower=="hands status":return run(["python3",str(Path(repo_root)/"tools"/"hands_router.py"),"status"],timeout=30,cwd=repo_root),"Hands"
 if lower=="hands on":return run(["python3",str(Path(repo_root)/"tools"/"hands_router.py"),"on"],timeout=30,cwd=repo_root),"Hands"
 if lower=="hands off":return run(["python3",str(Path(repo_root)/"tools"/"hands_router.py"),"off"],timeout=30,cwd=repo_root),"Hands"
 if lower.startswith("hands "):return run(["python3",str(Path(repo_root)/"tools"/"hands_overlay.py"),clean],timeout=60,cwd=repo_root),"Hands"
 if lower in {"audio start","listen start","start listening"}:return run(["python3",str(Path(repo_root)/"tools"/"adam_audio_lab.py"),"start"],timeout=30,cwd=repo_root),"Adam/audio"
 if lower in {"audio stop","listen stop","stop listening"}:return run(["python3",str(Path(repo_root)/"tools"/"adam_audio_lab.py"),"stop"],timeout=30,cwd=repo_root),"Adam/audio"
 if lower in {"audio status","listen status"}:return run(["python3",str(Path(repo_root)/"tools"/"adam_audio_lab.py"),"status"],timeout=30,cwd=repo_root),"Adam/audio"
 if lower in {"audio inspect","listen once"}:return run(["python3",str(Path(repo_root)/"tools"/"adam_audio_lab.py"),"once"],timeout=60,cwd=repo_root),"Adam/audio"
 if any(phrase in lower for phrase in ("find me something to watch","something to watch","pick something to watch")):
  return run(["python3",str(Path(repo_root)/"tools"/"adam_contextual.py"),clean],timeout=180,cwd=repo_root),"Adam/context"
 return run(["python3",str(Path(repo_root)/"tools"/"adam.py"),mode,clean,"--cwd",repo_root],timeout=240,cwd=repo_root),f"Adam/{mode}"

def process_adam_overlay(repo_root):
 query=rish(f"content query --uri {shlex.quote(OPERATOR_STATE_URI)}")
 if query["rc"]!=0:return
 raw=query["stdout"]
 try:request_id=int(_operator_field(raw,"adam_request_id","0") or "0")
 except ValueError:return
 if request_id<=0 or request_id<=_last_adam_request_id():return
 mode=_operator_field(raw,"adam_request_mode","terminal"); payload=_operator_field(raw,"adam_request_payload_b64",""); _set_last_adam_request_id(request_id)
 try:text=base64.b64decode(payload,validate=True).decode("utf-8")
 except Exception as exc:
  event={"kind":"adam.request","ok":False,"requestId":request_id,"mode":mode,"error":f"invalid_payload: {exc}"}; append_receipt(event); operator_update(event["error"],f"Adam/{mode}"); return
 result,source=_route_overlay(repo_root,mode,text); update=operator_update(_display(result),source)
 append_receipt({"kind":"adam.request","ok":result["rc"]==0 and update["rc"]==0,"requestId":request_id,"mode":mode,"source":source,"result":result,"overlayUpdate":update})

def process_review_inbox(repo_root):
 inbox=STATE_DIR/"review-inbox"; done=STATE_DIR/"review-done"; inbox.mkdir(parents=True,exist_ok=True); done.mkdir(parents=True,exist_ok=True)
 for job in sorted(inbox.glob("*.json")):
  data=json.loads(job.read_text(encoding="utf-8")); repo=data.get("repo") or repo_root; base=data.get("base","HEAD~1"); head=data.get("head","HEAD"); acceptance=data.get("acceptance",""); receipt_path=done/(job.stem+".receipt.json")
  result=run(["python3",str(Path(repo_root)/"tools"/"venice_review.py"),"--repo",repo,"--base",base,"--head",head,"--acceptance",acceptance,"--receipt",str(receipt_path)],timeout=int(data.get("timeout",180)))
  append_receipt({"kind":"venice.review","job":job.name,"ok":result["rc"]==0,"result":result,"receipt":str(receipt_path)}); job.rename(done/job.name)

def heartbeat(repo_root):
 shizuku_ok=phone_health(); operator_heartbeat(); process_review_inbox(repo_root); append_receipt({"kind":"swarm.heartbeat","ok":True,"shizuku":shizuku_ok})

def main():
 ap=argparse.ArgumentParser(description="Deterministic Vlad swarm keeper"); ap.add_argument("--repo",default=os.environ.get("HC_REPO_ROOT",".")); ap.add_argument("--once",action="store_true"); ap.add_argument("--interval",type=int,default=INTERVAL); args=ap.parse_args(); repo_root=str(Path(args.repo).resolve())
 STATE_DIR.mkdir(parents=True,exist_ok=True); append_receipt({"kind":"swarm.start","ok":True,"repo":repo_root,"interval":args.interval}); next_heartbeat=0.0
 while True:
  try:
   process_adam_overlay(repo_root); current=time.monotonic()
   if current>=next_heartbeat:heartbeat(repo_root); next_heartbeat=current+max(5,args.interval)
  except Exception as exc:append_receipt({"kind":"swarm.error","ok":False,"error":f"{type(exc).__name__}: {exc}"})
  if args.once:return 0
  time.sleep(max(0.25,ADAM_POLL_SECONDS))
if __name__=="__main__":raise SystemExit(main())
