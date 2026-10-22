#!/usr/bin/env python3
"""Single-candidate Nano voice test, keeps the canonical phone relay intact."""
import argparse, hashlib, json, os, pathlib, sys, time, wave
ROOT=pathlib.Path(r"C:\Users\dclar\workspace\ritsu-chatterbox-nano\src")
REFERENCE=pathlib.Path(r"C:\Users\dclar\Documents\Codex\Venice\PocketTTS\speech_store\cache\c427230b53740062dfc343cb7142d446c71c44e5ae9eca9a8926c014cd855ce0.wav")
BASE=pathlib.Path(r"C:\Users\dclar\workspace\ritsu-chatterbox-turbo\generated")
sys.path.insert(0,str(ROOT))
def log(event,**extra):
    print(json.dumps({"event":event,"time":round(time.time(),3),**extra}),flush=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--text",default="Drew, this is Ritsu speaking with the smaller Nano voice. Can you hear me?")
    p.add_argument("--device",default="cpu",choices=("cpu","cuda"))
    args=p.parse_args()
    if not REFERENCE.is_file():raise SystemExit("BLOCKED: pinned Ritsu voice reference missing")
    BASE.mkdir(parents=True,exist_ok=True)
    import uuid
    out=BASE/("ritsu-nano-"+uuid.uuid4().hex+".wav")
    log("START",source=str(ROOT),device=args.device)
    import torch,torchaudio
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    log("IMPORT_COMPLETE",torch=torch.__version__)
    t=time.monotonic()
    model=ChatterboxTurboTTS.from_pretrained(device=args.device,nano=True)
    log("MODEL_READY",seconds=round(time.monotonic()-t,2))
    t=time.monotonic()
    with torch.inference_mode():
        audio=model.generate(args.text,audio_prompt_path=str(REFERENCE))
    log("GENERATED",seconds=round(time.monotonic()-t,2))
    torchaudio.save(str(out),audio.cpu(),model.sr)
    with wave.open(str(out),"rb") as f:
        duration=f.getnframes()/f.getframerate()
    log("WAV_VERIFIED",path=str(out),bytes=out.stat().st_size,duration=round(duration,2),
        sha256=hashlib.sha256(out.read_bytes()).hexdigest())
if __name__=="__main__":main()
