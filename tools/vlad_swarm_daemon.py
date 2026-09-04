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

import fortress_night_status as night_status

STATE_DIR = Path(os.environ.get("HC_SWARM_STATE_DIR", "~/.local/state/home-center/vlad-swarm")).expanduser()
JAR_CACHE = Path(os.environ.get("HC_JUDGMENT_JARS_CACHE", str(STATE_DIR / "judgment-jars.json"))).expanduser()
JAR_CONFIG = Path(os.environ.get("HC_JUDGMENT_JARS_CONFIG", "config/judgment-jars.v1.json")).expanduser()
JAR_SYNC_TIMEOUT = int(os.environ.get("HC_JUDGMENT_JARS_SYNC_TIMEOUT", "90"))
RISH = os.environ.get("HC_RISH", "rish")
INTERVAL = int(os.environ.get("HC_SWARM_INTERVAL", "30"))
ADAM_POLL_SECONDS = float(os.environ.get("HC_ADAM_POLL_SECONDS", "1.0"))
CONTEXT_SENSOR_INTERVAL = int(os.environ.get("HC_CONTEXT_SENSOR_INTERVAL", "120"))
CONTEXT_SENSOR_CHARGING_INTERVAL = int(os.environ.get("HC_CONTEXT_SENSOR_CHARGING_INTERVAL", "60"))
CONTEXT_SENSOR_LOW_BATTERY_INTERVAL = int(os.environ.get("HC_CONTEXT_SENSOR_LOW_BATTERY_INTERVAL", "300"))
CONTEXT_SENSOR_CRITICAL_BATTERY_INTERVAL = int(os.environ.get("HC_CONTEXT_SENSOR_CRITICAL_BATTERY_INTERVAL", "600"))
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
def sync_judgment_jars(repo_root):
    script=Path(repo_root)/"tools"/"judgment_jars.py"
    config=JAR_CONFIG if JAR_CONFIG.is_absolute() else Path(repo_root)/JAR_CONFIG
    if not script.is_file():
        summary={"ok":False,"complete":False,"state":"script_missing","cachePath":str(JAR_CACHE),"script":str(script)}
        append_receipt({"kind":"vlad.judgment_jars.sync",**summary});return summary
    if not config.is_file():
        summary={"ok":False,"complete":False,"state":"config_missing","cachePath":str(JAR_CACHE),"config":str(config)}
        append_receipt({"kind":"vlad.judgment_jars.sync",**summary});return summary
    cmd=["python3",str(script),"--root",repo_root,"--cache",str(JAR_CACHE),"--config",str(config),"sync"]
    try:
        process=subprocess.run(cmd,text=True,capture_output=True,timeout=JAR_SYNC_TIMEOUT,cwd=repo_root)
        full_stdout=process.stdout.strip();full_stderr=process.stderr.strip()
        result={"cmd":cmd,"rc":process.returncode,"stdout":full_stdout[-4000:],"stderr":full_stderr[-4000:]}
        payload=json.loads(full_stdout)
    except subprocess.TimeoutExpired as exc:
        result={"cmd":cmd,"rc":124,"stdout":str(exc.stdout or "")[-4000:],"stderr":str(exc.stderr or "")[-4000:]}
        payload={"ok":False,"complete":False,"error":"judgment_jar_sync_timeout"}
    except Exception as exc:
        result={"cmd":cmd,"rc":2,"stdout":"","stderr":f"{type(exc).__name__}: {exc}"}
        payload={"ok":False,"complete":False,"error":f"invalid_sync_receipt:{type(exc).__name__}:{exc}"}
    ok=result["rc"]==0 and payload.get("ok") is True
    complete=ok and payload.get("complete") is True
    home_state=str(payload.get("homeCenterState") or "unavailable")
    summary={
        "ok":ok,
        "complete":complete,
        "state":"synced" if complete else ("stale" if ok and home_state=="stale" else "degraded" if ok else "failed"),
        "cachePath":str(JAR_CACHE),
        "configPath":str(config),
        "jarCount":int(payload.get("jarCount") or 0),
        "localJarCount":int(payload.get("localJarCount") or 0),
        "cabinetJarCount":int(payload.get("cabinetJarCount") or 0),
        "unregisteredJarCount":int(payload.get("unregisteredJarCount") or 0),
        "registryDigest":payload.get("registryDigest"),
        "sourceCommit":payload.get("sourceCommit"),
        "homeCenterState":home_state,
        "homeCenterLastError":payload.get("homeCenterLastError") or "",
        "homeCenterAttempted":payload.get("homeCenterAttempted") is True,
        "homeCenterFailed":payload.get("homeCenterFailed") is True,
        "changed":payload.get("changed") is True,
        "cacheRewritten":payload.get("cacheRewritten") is True,
    }
    if not ok or summary["changed"] or summary["cacheRewritten"] or summary["homeCenterFailed"]:
        append_receipt({"kind":"vlad.judgment_jars.sync",**summary,"result":result})
    return summary

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

def context_sensor_delay():
    """Keep local sensing responsive while charging and cheap on low battery.

    Battery truth is delegated to the bounded Night Core probe: Termux API/sysfs
    first, with rish dumpsys as a <=3 second fallback. Never use generic rish()
    here; its wider timeout is for unrelated phone operations.
    """
    started=time.monotonic();battery=night_status.battery();latency_ms=int((time.monotonic()-started)*1000)
    try:level=int(battery.get("level",-1))
    except (TypeError,ValueError):level=-1
    charging=bool(battery.get("plugged"));source=str(battery.get("source") or "unavailable")
    if charging:delay=max(30,CONTEXT_SENSOR_CHARGING_INTERVAL)
    elif 0<=level<=20:delay=max(60,CONTEXT_SENSOR_CRITICAL_BATTERY_INTERVAL)
    elif 0<=level<=40:delay=max(60,CONTEXT_SENSOR_LOW_BATTERY_INTERVAL)
    else:delay=max(30,CONTEXT_SENSOR_INTERVAL)
    append_receipt({"kind":"context.battery.cadence","ok":level>=0,"source":source,"level":level,"plugged":charging,"latencyMs":latency_ms,"delaySeconds":delay,"boundedNightCoreProbe":True})
    return delay
def sense_context(repo_root):
    script=Path(repo_root)/"tools"/"fortress_context_sensors.py"
    if not script.is_file():
        summary={"ok":False,"state":"script_missing","script":str(script)}
        append_receipt({"kind":"context.sensors","ok":False,**summary});return summary
    cmd=["python3",str(script)]
    try:
        process=subprocess.run(cmd,text=True,capture_output=True,timeout=45,cwd=repo_root)
        full_stdout=process.stdout.strip();full_stderr=process.stderr.strip()
    except subprocess.TimeoutExpired as exc:
        summary={"ok":False,"state":"timeout","result":{"cmd":cmd,"rc":124,"stdout":str(exc.stdout or "")[-4000:],"stderr":str(exc.stderr or "")[-4000:]}}
        append_receipt({"kind":"context.sensors","ok":False,**summary});return summary
    result={"cmd":cmd,"rc":process.returncode,"stdout":full_stdout[-4000:],"stderr":full_stderr[-4000:]}
    if process.returncode!=0:
        summary={"ok":False,"state":"failed","result":result}
        append_receipt({"kind":"context.sensors","ok":False,**summary});return summary
    try:payload=json.loads(full_stdout)
    except Exception as exc:
        summary={"ok":False,"state":"invalid_receipt","error":f"{type(exc).__name__}: {exc}","result":result}
        append_receipt({"kind":"context.sensors","ok":False,**summary});return summary
    summary={
        "ok":True,
        "state":"wake_emitted" if payload.get("wakeEmitted") else "quiet",
        "meaningfulDigest":payload.get("meaningfulDigest"),
        "changed":payload.get("changed") is True,
        "wakeRequired":payload.get("wakeRequired") is True,
        "wakeEmitted":payload.get("wakeEmitted") is True,
        "wakePending":payload.get("wakePending") is True,
        "wakeReasons":payload.get("wakeReasons") or [],
        "staleWorkerIds":((payload.get("chatgptShell") or {}).get("staleWorkerIds") or []),
        "blockedWorkerIds":((payload.get("chatgptShell") or {}).get("blockedWorkerIds") or []),
    }
    refresh=payload.get("refresh") or {}
    refresh_failures={name:value for name,value in refresh.items() if value.get("attempted") and value.get("ok") is False}
    if refresh_failures:
        summary["refreshFailures"]=refresh_failures
        append_receipt({"kind":"context.sensors.refresh","ok":False,**summary})
    if summary["wakeEmitted"]:
        append_receipt({"kind":"context.scheduler.wake","ok":True,**summary})
    return summary

def ensure_phone_ssh(repo_root):
    script=Path(repo_root)/"tools"/"phone_ssh_service.sh"
    if not script.is_file():
        append_receipt({"kind":"phone.ssh.ensure","ok":False,"state":"script_missing","script":str(script)});return False
    result=run(["bash",str(script),"ensure"],timeout=90,cwd=repo_root)
    ok=result["rc"]==0
    append_receipt({"kind":"phone.ssh.ensure","ok":ok,"state":"healthy" if ok else "failed","result":result})
    return ok
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

def _pending_response_path(request_id):
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    return STATE_DIR/f"adam-pending-response-{int(request_id):020d}.json"
def _delivery_halt_path():
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    return STATE_DIR/"adam-delivery-halt.json"
def _save_delivery_halt(reason,path=None):
    halt={"schema":"adam-delivery-halt-v1","reason":str(reason),"pendingPath":str(path) if path else None,"createdAtEpoch":now()};p=_delivery_halt_path();tmp=p.with_suffix(".tmp");tmp.write_text(json.dumps(halt,indent=2,sort_keys=True)+"\n",encoding="utf-8");tmp.replace(p);append_receipt({"kind":"adam.delivery.halt","ok":False,**halt});return p
def _save_pending_response(data):
    p=_pending_response_path(data["requestId"]);tmp=p.with_suffix(".tmp");tmp.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8");tmp.replace(p);return p
def _pending_response_paths():
    STATE_DIR.mkdir(parents=True,exist_ok=True);return sorted(STATE_DIR.glob("adam-pending-response-*.json"))
def _load_pending_response(path):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        append_receipt({"kind":"adam.delivery.pending.invalid","ok":False,"path":str(path),"error":f"{type(exc).__name__}: {exc}"})
        return None
def _deliver_pending_responses():
    """Preserve request ordering: do not start newer work until older output is delivered."""
    if _delivery_halt_path().exists():return False
    for path in _pending_response_paths():
        data=_load_pending_response(path)
        if not data:
            bad=path.with_name("quarantine-"+path.name)
            try:path.replace(bad)
            except Exception:pass
            _save_delivery_halt("corrupt_pending_response",bad)
            return False
        request_id=int(data.get("requestId") or 0);mode=str(data.get("mode") or "unknown")
        if request_id<=0:
            bad=path.with_name("quarantine-"+path.name)
            try:path.replace(bad)
            except Exception:pass
            _save_delivery_halt("pending_response_missing_request_id",bad)
            return False
        if request_id<=_last_adam_request_id():
            try:path.unlink()
            except Exception:pass
            continue
        next_attempt=int(data.get("nextAttemptEpoch") or 0)
        if next_attempt>now():return False
        update=operator_update(data.get("display", ""),f"Adam/{mode}")
        if update["rc"]==0:
            append_receipt({"kind":"adam.delivery","ok":True,"requestId":request_id,"mode":mode,"attempts":int(data.get("attempts") or 0)+1,"overlayUpdate":update,"pending":str(path)})
            _set_last_adam_request_id(request_id)
            try:path.unlink()
            except Exception:pass
            continue
        attempts=int(data.get("attempts") or 0)+1;delay=min(60,2**min(attempts,5));data["attempts"]=attempts;data["nextAttemptEpoch"]=now()+delay;data["lastOverlayUpdate"]=update;_save_pending_response(data)
        append_receipt({"kind":"adam.delivery","ok":False,"requestId":request_id,"mode":mode,"attempts":attempts,"backoffSeconds":delay,"nextAttemptEpoch":data["nextAttemptEpoch"],"overlayUpdate":update,"pending":str(path)})
        return False
    return True

def process_adam_overlay(repo_root):
    if not _deliver_pending_responses():return
    query=rish(f"content query --uri {shlex.quote(OPERATOR_STATE_URI)}")
    if query["rc"]!=0:return
    raw=query["stdout"]
    try:request_id=int(_operator_field(raw,"adam_request_id","0") or "0")
    except ValueError:return
    if request_id<=0 or request_id<=_last_adam_request_id():return
    mode=_operator_field(raw,"adam_request_mode","terminal");payload=_operator_field(raw,"adam_request_payload_b64","")
    try:text=base64.b64decode(payload,validate=True).decode("utf-8")
    except Exception as exc:
        display=f"invalid_payload: {exc}";pending={"schema":"adam-overlay-pending-response-v1","requestId":request_id,"mode":mode,"display":display[:8000],"taskRc":2,"taskResult":{"error":display},"attempts":0,"nextAttemptEpoch":0,"createdAtEpoch":now()};pending_path=_save_pending_response(pending);append_receipt({"kind":"adam.request.invalid","ok":False,"requestId":request_id,"mode":mode,"error":display,"pending":str(pending_path)});_deliver_pending_responses();return
    result=run(["python3",str(Path(repo_root)/"tools"/"adam.py"),mode,text,"--cwd",repo_root],timeout=None,cwd=repo_root);display=result["stdout"] or result["stderr"] or f"Adam {mode} exited {result['rc']}"
    try:
        parsed=json.loads(result["stdout"]);display=parsed.get("response") or parsed.get("stdout") or parsed.get("detail") or parsed.get("error") or display
        if parsed.get("stderr"):display=(str(display)+"\n"+str(parsed["stderr"])).strip()
    except Exception:pass
    pending={"schema":"adam-overlay-pending-response-v1","requestId":request_id,"mode":mode,"display":str(display)[:8000],"taskRc":result["rc"],"taskResult":result,"attempts":0,"nextAttemptEpoch":0,"createdAtEpoch":now()};pending_path=_save_pending_response(pending)
    append_receipt({"kind":"adam.request.executed","ok":result["rc"]==0,"requestId":request_id,"mode":mode,"result":result,"pending":str(pending_path),"daemonWait":True})
    _deliver_pending_responses()

def _review_bucket(name):
    p=STATE_DIR/name;p.mkdir(parents=True,exist_ok=True);return p
def _load_review_receipt(path):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:return {"directive":"HALT_REQUIRED","verdict":"FAIL","findings":[f"invalid_review_receipt:{exc}"],"externalReviewGateSatisfied":False}
def _review_text_path(job,data):
    raw=str(data.get("reviewTextPath") or "").strip()
    return Path(raw).expanduser() if raw else job.with_suffix('.review.txt')
def _authorized_primary_review_text(path):
    if not path.is_file():return False
    text=path.read_text(encoding="utf-8",errors="replace")
    return bool(re.search(r"(?im)^VERDICT\s*:\s*(PASS|FAIL)\s*$",text) and re.search(r"(?im)^DIRECTIVE\s*:\s*(STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED)\s*$",text))
def process_review_inbox(repo_root):
    inbox=_review_bucket("review-inbox");done=_review_bucket("review-done");cont=_review_bucket("review-continue");halt=_review_bucket("review-halt")
    for job in sorted(inbox.glob("*.json")):
        data=json.loads(job.read_text(encoding="utf-8"));repo=data.get("repo") or repo_root;base=data.get("base","HEAD~1");head=data.get("head","HEAD");acceptance=data.get("acceptance","");receipt_path=done/(job.stem+".receipt.json")
        local_venice=data.get("localVenice") is True or data.get("reviewerMode")=="local_venice"
        review_text=_review_text_path(job,data)
        if not local_venice and not _authorized_primary_review_text(review_text):
            append_receipt({"kind":"venice.review.awaiting_chatgpt_judgment_jar","job":job.name,"ok":False,"state":"awaiting_review","reviewTextPath":str(review_text),"reviewerMode":"judgment_jar_emulation"})
            continue
        cmd=["bash",str(Path(repo_root)/"tools"/"venice_review_selfheal.sh"),"--repo",repo,"--base",base,"--head",head,"--acceptance",acceptance,"--receipt",str(receipt_path)]
        if local_venice:cmd.append("--local-venice")
        else:cmd.extend(["--review-text-file",str(review_text),"--reviewer",str(data.get("reviewer") or "chatgpt-venice-judgment-jar")])
        result=run(cmd,timeout=int(data.get("timeout",600)));receipt=_load_review_receipt(receipt_path) if receipt_path.exists() else {"directive":"HALT_REQUIRED","verdict":"FAIL","findings":["review_receipt_missing"],"externalReviewGateSatisfied":False}
        directive=receipt.get("directive") or "HALT_REQUIRED"
        if directive=="STOP_ALLOWED" and receipt.get("externalReviewGateSatisfied") is True:
            bucket=done;state="stop_allowed";ok=True
        elif directive=="CONTINUE_REQUIRED":
            bucket=cont;state="continue_required";ok=False
        else:
            bucket=halt;state="halt_required";ok=False
        decision={"schema":"venice-swarm-decision-v2","job":data,"reviewReceipt":str(receipt_path),"directive":directive,"state":state,"findings":receipt.get("findings",[]),"reviewHead":head,"reviewerMode":receipt.get("reviewerMode"),"createdAtEpoch":now()}
        (bucket/(job.stem+".decision.json")).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        target=bucket/job.name
        if target.exists():target.unlink()
        job.rename(target)
        append_receipt({"kind":"venice.review.directive","job":job.name,"ok":ok,"directive":directive,"state":state,"receipt":str(receipt_path),"decision":str(bucket/(job.stem+".decision.json")),"reviewerMode":receipt.get("reviewerMode"),"localVeniceExplicit":local_venice,"result":result})
def heartbeat(repo_root,context_due=False):
    jars=sync_judgment_jars(repo_root);shizuku_ok=phone_health();ssh_ok=ensure_phone_ssh(repo_root);overlay_ok=ensure_operator_overlay(repo_root) if shizuku_ok else False
    if overlay_ok:operator_heartbeat()
    context=sense_context(repo_root) if context_due else {"ok":True,"state":"deferred"}
    process_review_inbox(repo_root)
    summary={"kind":"swarm.heartbeat","ok":True,"shizuku":shizuku_ok,"ssh":ssh_ok,"overlay":overlay_ok,"judgmentJars":jars,"contextSenses":context}
    append_receipt(summary);return summary
def main():
    ap=argparse.ArgumentParser(description="Deterministic Vlad swarm keeper");ap.add_argument("--repo",default=os.environ.get("HC_REPO_ROOT","."));ap.add_argument("--once",action="store_true");ap.add_argument("--interval",type=int,default=INTERVAL);args=ap.parse_args();repo_root=str(Path(args.repo).resolve());STATE_DIR.mkdir(parents=True,exist_ok=True);append_receipt({"kind":"swarm.start","ok":True,"repo":repo_root,"interval":args.interval,"contextSensorInterval":CONTEXT_SENSOR_INTERVAL,"judgmentJarCache":str(JAR_CACHE)});next_heartbeat=0.0;next_context_sense=0.0
    while True:
        try:
            process_adam_overlay(repo_root);current=time.monotonic()
            if current>=next_heartbeat:
                context_due=current>=next_context_sense
                heartbeat(repo_root,context_due=context_due);next_heartbeat=current+max(5,args.interval)
                if context_due:next_context_sense=current+context_sensor_delay()
        except Exception as exc:append_receipt({"kind":"swarm.error","ok":False,"error":f"{type(exc).__name__}: {exc}"})
        if args.once:return 0
        time.sleep(max(.25,ADAM_POLL_SECONDS))
if __name__=="__main__":raise SystemExit(main())
