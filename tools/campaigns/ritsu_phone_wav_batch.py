#!/usr/bin/env python3
"""Lossless-by-sample FIFO grouping for canonical Android termux-media-player.

This tool merges *already prefetched* 24kHz mono PCM16 WAV files so Android can
start fewer tracks. It NEVER edits original WAVs, shortens silence, invents speech,
uses another player, accesses the relay, or decides linguistic boundaries.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, re, sys, wave

MAX_FILES=3
MAX_AUDIO_SECONDS=90
RATE=24000
WIDTH=2
CHANNELS=1
VALID=re.compile(r"^([0-9]{8})_([a-f0-9]{24})\.wav$")

def sha256(data):return hashlib.sha256(data).hexdigest()
def read_file(path):
    name=path.name
    match=VALID.fullmatch(name)
    if not match:raise ValueError("Not a canonical queued WAV filename")
    with wave.open(str(path),"rb") as f:
        if (f.getnchannels(), f.getsampwidth(), f.getframerate(),f.getcomptype())!=(CHANNELS,WIDTH,RATE,"NONE"):
            raise ValueError("Unexpected WAV format")
        n=f.getnframes()
        if n < 1 or n > MAX_AUDIO_SECONDS*RATE:raise ValueError("Empty or oversized WAV")
        pcm=f.readframes(n)
        if len(pcm)!=n*WIDTH:raise ValueError("Incomplete WAV")
    return {"seq":int(match[1]),"id":match[2],"file":str(path),"frames":n,"pcmSha256":sha256(pcm)},pcm

def build(paths,out):
    if not 2<=len(paths)<=MAX_FILES:raise ValueError("Only two or three complete files can be grouped")
    if out.exists() or any(out.resolve()==p.resolve() for p in paths):
        raise FileExistsError("Never overwrite an existing file")
    metadata=[];pieces=[]
    expected=None
    for p in paths:
        meta,pcm=read_file(p)
        if expected is not None and meta["seq"]!=expected:raise ValueError("Nonconsecutive FIFO sequence")
        expected=meta["seq"]+1
        metadata.append(meta);pieces.append(pcm)
    combined=b"".join(pieces)
    if len(combined)>MAX_AUDIO_SECONDS*RATE*WIDTH:raise ValueError("Batch too long")
    try:
        with out.open("xb") as sink:
            with wave.open(sink,"wb") as dst:
                dst.setnchannels(CHANNELS);dst.setsampwidth(WIDTH);dst.setframerate(RATE)
                dst.writeframes(combined)
        with wave.open(str(out),"rb") as f:
            if (f.getnchannels(),f.getsampwidth(),f.getframerate())!=(CHANNELS,WIDTH,RATE):
                raise ValueError("Output format mismatch")
            readback=f.readframes(f.getnframes())
        if sha256(combined)!=sha256(readback):raise ValueError("Output PCM mismatch")
    except BaseException:
        out.unlink(missing_ok=True)
        raise
    return {"status":"verified","firstSeq":metadata[0]["seq"],"lastSeq":metadata[-1]["seq"],
            "ids":[x["id"] for x in metadata],"items":metadata,"frames":len(combined)//WIDTH,
            "output":str(out),"outputPcmSha256":sha256(combined),
            "gapInsertedSamples":0,"sourceSamplesTrimmed":0,"sourceWavsChanged":False,
            "player":"termux-media-player","liveAudioDelivered":False}

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument("--output",required=True,type=pathlib.Path)
    ap.add_argument("input",nargs="+",type=pathlib.Path);args=ap.parse_args(argv)
    try:print(json.dumps(build(args.input,args.output),sort_keys=True));return 0
    except (OSError, ValueError,EOFError,wave.Error) as e:
        print("RITSU_BATCH_REFUSED "+type(e).__name__,file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
