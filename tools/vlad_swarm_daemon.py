#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("HC_SWARM_STATE_DIR", "~/.local/state/home-center/vlad-swarm")).expanduser()
RISH = os.environ.get("HC_RISH", "rish")
INTERVAL = int(os.environ.get("HC_SWARM_INTERVAL", "30"))
ADAM_POLL_SECONDS = float(os.environ.get("HC_ADAM_POLL_SECONDS", "1.0"))
OPERATOR_STATE_URI = "content://com.homecenter.operatoroverlay.state/state"
OPERATOR_RECEIVER = "com.homecenter.operatoroverlay/.OverlayUpdateReceiver"
OVERLAY_RECOVERY_COOLDOWN = int(os.environ.get("HC_OVERLAY_RECOVERY_COOLDOWN", "120"))


def now(): return int(time.time())

def run(cmd, timeout=20, cwd=None):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout,cwd=cwd)
    return {"cmd":cmd,"rc":p.returncode,"stdout":p.stdout.strip()[-4000:],"stderr":p.stderr.strip()[-4000:]}
def rish(command): return run([RISH,"-c",command])
def append_receipt(event):
    STATE_DIR.mkdir(parents=True,exist_ok=True);event={"at":now(),**event}
    with (STATE_DIR/"receipts.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(event,sort_keys=True)+"\n")
    (STATE_DIR/"last.json").write_text(json.dumps(event,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def phone_health():
    probe=rish("id");ok=probe["rc"]==0;append_receipt({"kind":"phone.shizuku.probe","ok":ok,"result":probe})
    if not ok:return False
    wifi=rish("cmd wifi status");text=(wifi["stdout"]+"\n"+wifi["stderr"]).lower();enabled="wifi is enabled" in text or "enabled: true" in text;connected=any(k in text for k in ("connected","ssid","networkid")) and "disconnected" not in text
    append_receipt({"kind":"phone.wlan.probe","ok":wifi["rc"]==0,"enabled":enabled,"connected":connected,"result":wifi})
    if not enabled:
        repair=rish("cmd wifi set-wifi-enabled enabled");append_receipt({"kind":"phone.wlan.enable","ok":repair["rc"]==0,"result":repair})
    elif not connected:
        scan=rish("cmd wifi start-scan");append_receipt({"kind":"phone.wlan.scan","ok":scan["rc"]==0,"result":scan})
    return True
def _overlay_recovery_stamp(): return STATE_DIR/"overlay-last-recovery-epoch"
def _last_overlay_recovery():
    try:return int(_overlay_recovery_stamp().read_text(encoding="utf-8").strip())
    except Exception:return 0
def _set_overlay_recovery(value):STATE_DIR.mkdir(parents=True,exist_ok=True);_overlay_recovery_stamp().write_text(str(int(value))+"\n",encoding="utf-8")
def ensure_operator_overlay(repo_root):
    query=rish(f"content query --uri {shlex.quote(OPERATOR_STATE_URI)}");healthy=query["rc"]==0 and "control_enabled=" in query["stdout"];append_receipt({"kind":"operator.overlay.probe","ok":healthy,"result":query})
    if healthy:return True
    current=now()
    if current-_last_overlay_recovery()<max(30,OVERLAY_RECOVERY_COOLDOWN):append_receipt({"kind":"operator.overlay.recovery","ok":False,"state":"cooldown"});return False
    _set_overlay_recovery(current);script=Path(repo_root)/"tools"/"recover_adam_overlay_phone.sh"
    if not script.is_file():append_receipt({"kind":"operator.overlay.recovery","ok":False,"state":"script_missing","script":str(script)});return False
    result=run(["bash",str(script)],timeout=600,cwd=repo_root);verify=rish(f"content query --uri {shlex.quote(OPERATOR_STATE_URI)}");recovered=result["rc"]==0 and verify["rc"]==0 and "control_enabled=" in verify["stdout"];append_receipt({"kind":"operator.overlay.recovery","ok":recovered,"state":"recovered" if recovered else "failed","result":result,"verify":verify});return recovered
def _operator_field(raw,name,default=""):
    m=re.search(rf"\b{re.escape(name)}=([^,\n]*)",raw);return m.group(1).strip() if m else default
def operator_heartbeat():
    result=rish("am broadcast --receiver-foreground -a com.homecenter.operatoroverlay.HEARTBEAT "+f"-n {OPERATOR_RECEIVER}");append_receipt({"kind":"adam.overlay.heartbeat","ok":result["rc"]==0,"result":result})
def operator_update(text,source):
    return rish("am broadcast --receiver-foreground -a com.homecenter.operatoroverlay.UPDATE "+f"-n {OPERATOR_RECEIVER} --es latestText {shlex.quote(str(text)[:8000])} --es source {shlex.quote(str(source)[:80])}")
def _last_adam_request_id():
    try:return int((STATE_DIR/"adam-last-request-id").read_text(encoding="utf-8").strip())
    except Exception:return 0
def _set_last_adam_request_id(value):STATE_DIR.mkdir(parents=True,exist_ok=True);(STATE_DIR/"adam-last-request-id").write_text(str(int(value))+"\n",encoding="utf-8")
def process_adam_overlay(repo_root):
    query=rish(f"content query --uri {shlex.quote(OPERATOR_STATE_URI)}")
    if query["rc"]!=0:return
    raw=query["stdout"]
    try:request_id=int(_operator_field(raw,"adam_request_id","0") or "0")
    except ValueError:return
    if request_id<=0 or request_id<=_last_adam_request_id():return
    mode=_operator_field(raw,"adam_request_mode","terminal");payload=_operator_field(raw,"adam_request_payload_b64","")
    try:text=base64.b64decode(payload,validate=True).decode("utf-8")
    except Exception as exc:
        event={"kind":"adam.request","ok":False,"requestId":request_id,"mode":mode,"error":f"invalid_payload: {exc}"};append_receipt(event);operator_update(event["error"],f"Adam/{mode}");_set_last_adam_request_id(request_id);return
    # Adam is daemon-governed. Do not impose a short caller timeout: the worker
    # itself backs off transient dependencies, checkpoints long work, and may
    # stop only through canonical Venice review. If this process dies mid-run,
    # the request remains unacknowledged and will be retried after restart.
    result=run(["python3",str(Path(repo_root)/"tools"/"adam.py"),mode,text,"--cwd",repo_root],timeout=None,cwd=repo_root);display=result["stdout"] or result["stderr"] or f"Adam {mode} exited {result['rc']}"
    try:
        parsed=json.loads(result["stdout"]);display=parsed.get("response") or parsed.get("stdout") or parsed.get("detail") or parsed.get("error") or display
        if parsed.get("stderr"):display=(str(display)+"\n"+str(parsed["stderr"])).strip()
    except Exception:pass
    update=operator_update(display,f"Adam/{mode}");append_receipt({"kind":"adam.request","ok":result["rc"]==0 and update["rc"]==0,"requestId":request_id,"mode":mode,"result":result,"overlayUpdate":update,"daemonWait":True})
    _set_last_adam_request_id(request_id)

def _review_bucket(name):
    p=STATE_DIR/name;p.mkdir(parents=True,exist_ok=True);return p
def _load_review_receipt(path):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:return {"directive":"HALT_REQUIRED","verdict":"FAIL","findings":[f"invalid_review_receipt:{exc}"],"externalReviewGateSatisfied":False}
def process_review_inbox(repo_root):
    inbox=_review_bucket("review-inbox");done=_review_bucket("review-done");cont=_review_bucket("review-continue");halt=_review_bucket("review-halt")
    for job in sorted(inbox.glob("*.json")):
        data=json.loads(job.read_text(encoding="utf-8"));repo=data.get("repo") or repo_root;base=data.get("base","HEAD~1");head=data.get("head","HEAD");acceptance=data.get("acceptance","");receipt_path=done/(job.stem+".receipt.json")
        cmd=["bash",str(Path(repo_root)/"tools"/"venice_review_selfheal.sh"),"--repo",repo,"--base",base,"--head",head,"--acceptance",acceptance,"--receipt",str(receipt_path)]
        result=run(cmd,timeout=int(data.get("timeout",600)));receipt=_load_review_receipt(receipt_path) if receipt_path.exists() else {"directive":"HALT_REQUIRED","verdict":"FAIL","findings":["review_receipt_missing"],"externalReviewGateSatisfied":False}
        directive=receipt.get("directive") or "HALT_REQUIRED"
        if directive=="STOP_ALLOWED" and receipt.get("externalReviewGateSatisfied") is True:
            bucket=done;state="stop_allowed";ok=True
        elif directive=="CONTINUE_REQUIRED":
            bucket=cont;state="continue_required";ok=False
        else:
            bucket=halt;state="halt_required";ok=False
        decision={"schema":"venice-swarm-decision-v1","job":data,"reviewReceipt":str(receipt_path),"directive":directive,"state":state,"findings":receipt.get("findings",[]),"reviewHead":head,"createdAtEpoch":now()}
        (bucket/(job.stem+".decision.json")).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        target=bucket/job.name
        if target.exists():target.unlink()
        job.rename(target)
        append_receipt({"kind":"venice.review.directive","job":job.name,"ok":ok,"directive":directive,"state":state,"receipt":str(receipt_path),"decision":str(bucket/(job.stem+".decision.json")),"selfHeal":True,"result":result})
def heartbeat(repo_root):
    shizuku_ok=phone_health();overlay_ok=ensure_operator_overlay(repo_root) if shizuku_ok else False
    if overlay_ok:operator_heartbeat()
    process_review_inbox(repo_root);append_receipt({"kind":"swarm.heartbeat","ok":True,"shizuku":shizuku_ok,"overlay":overlay_ok})
def main():
    ap=argparse.ArgumentParser(description="Deterministic Vlad swarm keeper");ap.add_argument("--repo",default=os.environ.get("HC_REPO_ROOT","."));ap.add_argument("--once",action="store_true");ap.add_argument("--interval",type=int,default=INTERVAL);args=ap.parse_args();repo_root=str(Path(args.repo).resolve());STATE_DIR.mkdir(parents=True,exist_ok=True);append_receipt({"kind":"swarm.start","ok":True,"repo":repo_root,"interval":args.interval});next_heartbeat=0.0
    while True:
        try:
            process_adam_overlay(repo_root);current=time.monotonic()
            if current>=next_heartbeat:heartbeat(repo_root);next_heartbeat=current+max(5,args.interval)
        except Exception as exc:append_receipt({"kind":"swarm.error","ok":False,"error":f"{type(exc).__name__}: {exc}"})
        if args.once:return 0
        time.sleep(max(.25,ADAM_POLL_SECONDS))
if __name__=="__main__":raise SystemExit(main())
