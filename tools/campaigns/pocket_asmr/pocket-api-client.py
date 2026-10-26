#!/usr/bin/env python3
"""Termux-first Pocket ASMR client. HTTPS/Tailscale API only; no SSH or shell execution."""
import argparse, hashlib, json, os, re, sys, time, urllib.request, wave
from pathlib import Path
from io import BytesIO

API = os.environ.get("POCKET_ASMR_URL", "https://thecauldron-2.tail574fdf.ts.net:8443").rstrip("/")
TOKEN = Path(os.environ.get("POCKET_ASMR_TOKEN", str(Path.home()/".config/pocket-asmr/token")))
HOME = Path.home()/".local/share/pocket-asmr"
VOICES = ("whisper","normal","amused","happy","somber","upset")

def call(method, route, data=None, wav=False):
    token = TOKEN.read_text(encoding="utf-8").strip()
    req = urllib.request.Request(API+route,
        data=json.dumps(data).encode() if data is not None else None,
        method=method, headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=60) as r:
        return r.read() if wav else json.load(r)

def passages(text):
    # Respect explicit paragraph/sentence endings. Never cut a word or sentence.
    text = re.sub(r"\[(?:Long gentle |Final long gentle )?[Pp]ause\]|\[Final long gentle silence\]", "\n\n", text)
    text = re.sub(r"(?m)^RITSU ASMR.*$|^Narrator:.*$|^Target:.*$|^Audio directions:.*$", "", text).strip()
    lines = [x.strip() for x in re.split(r"\n\s*\n",text) if x.strip()]
    out=[]
    for para in lines:
        if len(para)<=450:
            out.append(para); continue
        sentences = re.split(r"(?<=[.!?])\s+",para)
        bucket=""
        for sentence in sentences:
            if len(sentence)>450: raise ValueError("Sentence exceeds 450-char API cap; edit transcript intentionally")
            if len(bucket)+len(sentence)+1>450:
                if bucket: out.append(bucket)
                bucket=sentence
            else: bucket=(bucket+" "+sentence).strip()
        if bucket:out.append(bucket)
    return out

def store(job,obj):
    p=HOME/job
    p.mkdir(parents=True,exist_ok=True)
    (p/"receipt.json").write_text(json.dumps(obj,indent=2),encoding="utf-8")

def load(job):
    return json.loads((HOME/job/"receipt.json").read_text(encoding="utf-8"))

def submit(path, voice):
    source=Path(path)
    original=source.read_text(encoding="utf-8-sig")
    segments=passages(original)
    job=time.strftime("%Y%m%d-%H%M%S")+"-"+hashlib.sha256(original.encode()).hexdigest()[:8]
    receipt={"job":job,"state":"submitting","voice":voice,"sha256":hashlib.sha256(original.encode()).hexdigest(),"segments":[]}
    store(job,receipt)
    (HOME/job/"transcript.txt").write_text(original,encoding="utf-8")
    for i,text in enumerate(segments):
        obj=call("POST","/asmr/jobs",{"text":text,"voice":voice})
        if obj.get("state")!="queued" or not obj.get("id"):raise RuntimeError("Upstream refused segment "+str(i))
        receipt["segments"].append({"id":obj["id"],"index":i,"sha256":hashlib.sha256(text.encode()).hexdigest()})
        store(job,receipt)
    receipt["state"]="submitted"
    store(job,receipt)
    print("QUEUED",job,"segments",len(segments))
    return job

def check(job):
    receipt=load(job)
    states=[call("GET","/asmr/jobs/"+s["id"]) for s in receipt["segments"]]
    counts={}
    for st in states:counts[st.get("state","unknown")]=counts.get(st.get("state","unknown"),0)+1
    print(job,counts)
    if counts.get("failed"):receipt["state"]="failed"
    elif len(states)>0 and counts.get("completed")==len(states):receipt["state"]="completed"
    store(job,receipt)
    return receipt["state"]=="completed"

def pull(job):
    if not check(job):raise RuntimeError("Not all segments completed")
    receipt=load(job)
    pieces=[]
    for item in receipt["segments"]:
        blob=call("GET","/asmr/jobs/"+item["id"]+"/audio",wav=True)
        with wave.open(BytesIO(blob),"rb") as f:
            spec=(f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getcomptype())
            if pieces and spec!=pieces[0][0]:raise RuntimeError("Mismatched PCM specification")
            frames=f.readframes(f.getnframes())
            pieces.append((spec,frames))
    outdir=Path(os.environ.get("POCKET_DOWNLOADS",str(Path.home()/"storage/downloads")))
    outdir.mkdir(parents=True,exist_ok=True)
    target=outdir/("ritsu-asmr-"+job+".wav")
    if target.exists():raise FileExistsError(str(target))
    with wave.open(str(target),"wb") as output:
        channels,width,rate,_=pieces[0][0]
        output.setnchannels(channels);output.setsampwidth(width);output.setframerate(rate)
        silence=b"\0"*int(rate*.6)*width*channels
        for i,(_,frames) in enumerate(pieces):
            if i:output.writeframesraw(silence)
            output.writeframesraw(frames)
    receipt["state"]="downloaded";receipt["output"]=str(target)
    receipt["outputSha256"]=hashlib.sha256(target.read_bytes()).hexdigest()
    store(job,receipt)
    print("SAVED",target)

def main():
    p=argparse.ArgumentParser(prog="pocket")
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("asmr");a.add_argument("source",nargs="?",default="asmr.txt");a.add_argument("--voice",choices=VOICES,default="whisper")
    for n in ("status","pull"):
        s=sub.add_parser(n);s.add_argument("job")
    args=p.parse_args()
    if args.command=="asmr":submit(args.source,args.voice)
    elif args.command=="status":check(args.job)
    else:pull(args.job)

if __name__=="__main__":
    try:main()
    except Exception as exc:print("ERROR:",exc,file=sys.stderr);sys.exit(1)
