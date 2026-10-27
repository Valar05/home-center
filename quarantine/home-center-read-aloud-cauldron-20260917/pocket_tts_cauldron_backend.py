#!/usr/bin/env python3
"""Pocket TTS v2 transport through Home Center Computer Hands."""
from __future__ import annotations
import base64,hashlib,json,os,pathlib,tempfile,time
from typing import Any,Callable
from home_center_mcp_client import HomeCenterMcp,HomeCenterError
from pocket_tts_render_v2 import CONTRACT_VERSION,atomic_json,sha256_bytes,validate_receipt
class CauldronRenderError(RuntimeError): pass
WORKER_ID="windows-hands-01"
LANE_ID="home-center-pocket-tts"
CHUNK_BYTES=80*1024

def _stdout(result:dict[str,Any])->str:
    nested=result.get("result") if isinstance(result.get("result"),dict) else result
    for key in ("stdout","output","text"):
        value=nested.get(key) if isinstance(nested,dict) else None
        if isinstance(value,str): return value.strip()
    raise CauldronRenderError("Computer Hands shell.exec returned no stdout")

def _run_action(client:HomeCenterMcp,request_id:str,action:str,arguments:dict[str,Any],timeout:int)->dict[str,Any]:
    created=client.drive_operation("computer_hands.request.create",{"requestId":request_id,"workerId":WORKER_ID,"laneId":LANE_ID,"action":action,"arguments":arguments,"approved":True,"highRiskApproved":True})
    ticket=str(created.get("ticketId") or "")
    if not ticket: raise CauldronRenderError("Computer Hands did not return a ticket")
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        status=client.drive_operation("computer_hands.request.status",{"ticketId":ticket}); state=str(status.get("status") or "")
        if state=="completed": return status
        if state in {"failed","cancelled"}:
            detail=status.get("result") or status.get("progress") or state; raise CauldronRenderError(f"Computer Hands {state}: {detail}")
        time.sleep(1.0)
    raise CauldronRenderError("Computer Hands Pocket TTS request timed out")

def _run_shell(client:HomeCenterMcp,request_id:str,command:str,timeout:int)->str:
    return _stdout(_run_action(client,request_id,"shell.exec",{"command":command},timeout))

def cauldron_status(client:HomeCenterMcp|None=None)->dict[str,Any]:
    try:
        value=(client or HomeCenterMcp()).drive_operation("computer_hands.worker.status",{"workerId":WORKER_ID})
    except HomeCenterError as exc: raise CauldronRenderError(str(exc)) from exc
    capabilities=value.get("capabilities") or []
    if value.get("online") is not True or "shell.exec" not in capabilities: raise CauldronRenderError("THECAULDRON Computer Hands worker is offline or lacks shell.exec")
    return value

def _safe_id(value:str)->str:
    safe="".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value).strip("-")[:100]
    if len(safe)<6: safe="pocket-"+hashlib.sha256(value.encode()).hexdigest()[:16]
    return safe

def render_on_cauldron(request_id:str,text:str,output:pathlib.Path,*,client:HomeCenterMcp|None=None,timeout:int=1800)->dict[str,Any]:
    if not text.strip(): raise CauldronRenderError("section text is empty")
    client=client or HomeCenterMcp(timeout=60); cauldron_status(client)
    safe=_safe_id(request_id); encoded=base64.b64encode(text.encode()).decode()
    install=r"C:\Users\Public\HomeCenterPocketTtsInstallV2"
    python_path=install+r"\.venv\Scripts\python.exe"; script_path=install+r"\render_section.py"
    remote_receipt=rf"C:\Users\Public\HomeCenterPocketTts\{safe}.json"
    arguments=f'"{script_path}" --request-id "{safe}" --text-base64 "{encoded}"'
    last_error=None
    for attempt in range(2):
        try:
            launch_id=f"ptts-launch-{hashlib.sha256((safe+text+str(attempt)).encode()).hexdigest()[:24]}"
            _run_action(client,launch_id,"process.start",{"command":python_path,"arguments":arguments,"workingDirectory":install},120)
            break
        except (HomeCenterError,CauldronRenderError) as exc:
            last_error=exc
            if attempt==0: time.sleep(2.0)
    else: raise CauldronRenderError(f"THECAULDRON render launch failed twice: {last_error}") from last_error
    remote=None; deadline=time.monotonic()+timeout; poll=0
    while time.monotonic()<deadline:
        probe=f"if(Test-Path '{remote_receipt}'){{Get-Content -Raw '{remote_receipt}'}}else{{'PENDING'}}"
        raw=_run_shell(client,f"ptts-probe-{hashlib.sha256((safe+str(poll)).encode()).hexdigest()[:24]}",probe,120); poll+=1
        if raw!='PENDING':
            try: remote=json.loads(raw)
            except json.JSONDecodeError as exc: raise CauldronRenderError(f"THECAULDRON returned invalid receipt: {raw[-500:]}") from exc
            break
        time.sleep(3.0)
    if remote is None: raise CauldronRenderError("THECAULDRON asynchronous render timed out")
    if remote.get("contractVersion")!=CONTRACT_VERSION or remote.get("accepted") is not True: raise CauldronRenderError("THECAULDRON receipt is not accepted Pocket TTS v2")
    remote_path=str(remote.get("output") or "").replace("'","''"); total=int(remote.get("frames") or 0)*2+44
    if total<=44: raise CauldronRenderError("THECAULDRON receipt has no audio bytes")
    assembled=bytearray()
    for offset in range(0,total,CHUNK_BYTES):
        length=min(CHUNK_BYTES,total-offset)
        chunk_command=(f"$s=[IO.File]::OpenRead('{remote_path}');try{{$s.Seek({offset},[IO.SeekOrigin]::Begin)|Out-Null;"
                       f"$b=New-Object byte[] {length};$n=$s.Read($b,0,{length});[Convert]::ToBase64String($b,0,$n)}}finally{{$s.Dispose()}}")
        block = b""; chunk_error = None
        for attempt in range(2):
            try:
                chunk_id=f"ptts-read-{hashlib.sha256((safe+str(offset)+str(length)+str(attempt)).encode()).hexdigest()[:24]}"
                payload=_run_shell(client,chunk_id,chunk_command,120)
                block=base64.b64decode(payload.strip(),validate=True)
                if len(block)!=length: raise CauldronRenderError(f"short Computer Hands audio chunk at {offset}")
                break
            except Exception as exc:
                chunk_error=exc
                if attempt==0: time.sleep(1.0)
        else: raise CauldronRenderError(f"audio chunk {offset} failed both bounded attempts: {chunk_error}") from chunk_error
        assembled.extend(block)
    if len(assembled)!=total or sha256_bytes(bytes(assembled))!=remote.get("artifactSha256"): raise CauldronRenderError("THECAULDRON reconstructed WAV identity mismatch")
    output=pathlib.Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=f".{output.name}.",suffix=".part",dir=output.parent); os.close(fd); staged=pathlib.Path(name)
    try: staged.write_bytes(assembled); os.replace(staged,output)
    finally: staged.unlink(missing_ok=True)
    local={**remote,"output":str(output),"backend":"cauldron-computer-hands","computerHandsWorkerId":WORKER_ID}
    atomic_json(output.with_suffix(".json"),local); validate_receipt(output,text=text); return local
