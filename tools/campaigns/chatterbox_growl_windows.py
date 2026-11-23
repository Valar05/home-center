#!/usr/bin/env python3
"""Isolated Chatterbox A/B voice test. No installs, network downloads or live service changes."""
import hashlib, importlib.metadata, json, os, shutil, subprocess, sys, tempfile, wave
from datetime import datetime, timezone
from pathlib import Path

REFERENCE_SHA="9E4B6C5A98FC7AF2CDA95BC2BD4C20852F4844C79A9B7763851BD530EC1C2E45"
REFERENCE_SIZE=2488364
REFERENCE_NAME="drew-growl-clone-conservative.wav"
EP_DRY="CHATTERBOX_GROWL_DRY_V1"
EP_DEEP="CHATTERBOX_GROWL_DEEP_V1"
PITCH_FILTER="rubberband=pitch=0.890898718:formant=preserved"
TEXT="Your Majesty. Four scouts returned. I sent five. Unfortunately, all four insist that I sent six."
ROOT=Path(os.environ["LOCALAPPDATA"])/"ChatterboxGrowl"/"v1"
RITSU_RUNS=Path(os.environ["LOCALAPPDATA"])/"RitsuASMR"/"runs"

def sha_bytes(b):return hashlib.sha256(b).hexdigest().upper()
def sha_file(p):
 with open(p,"rb") as f:
  h=hashlib.sha256()
  for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
 return h.hexdigest().upper()
def now():return datetime.now(timezone.utc).isoformat()
def atomic(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+".new")
 with open(tmp,"w",encoding="utf-8") as f:
  json.dump(d,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def status(phase,**kw):
 obj={"phase":phase,"updatedUtc":now(),"engine":"chatterbox","referenceSha256":REFERENCE_SHA,
      "networkDownloads":False,"livePocketModified":False,"liveRitsuModified":False,**kw}
 atomic(ROOT/"status.json",obj)
 return obj
def wav_data(p):
 with wave.open(str(p),"rb") as w:
  if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,24000) or not w.getnframes():
   raise RuntimeError("INVALID_24K_MONO_PCM_WAV")
  return w.getnframes()/24000
def source():
 roots=[Path.home()/"Downloads"]
 try:
  import winreg
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
   value,_=winreg.QueryValueEx(k,"{374DE290-123F-4565-9164-39C4925E467B}")
   roots.append(Path(os.path.expandvars(value)))
 except (OSError,ImportError):pass
 for base in dict.fromkeys(roots):
  for directory in (base,base/"Taildrop",base/"Tailscale"):
   if not directory.is_dir():continue
   for p in directory.iterdir():
    if p.is_file() and p.stat().st_size==REFERENCE_SIZE and sha_file(p)==REFERENCE_SHA:return p
 raise RuntimeError("REFERENCE_NOT_RECEIVED_BY_TAILDROP_SHA256_"+REFERENCE_SHA[:16])
def candidate_pythons():
 home=Path.home()
 choices=[]
 env=os.environ.get("RITSU_CHATTERBOX_PYTHON","")
 if env:choices.append(Path(env))
 for base in (home/"Documents"/"Codex"/"Venice",home/"workspace"):
  for name in ("Chatterbox","chatterbox","ChatterboxTTS","chatterbox-tts","chatterbox-tts-ui",
               "ritsu-chatterbox","chatterbox-voice"):
   for envname in (".venv","venv"):
    choices.append(base/name/envname/"Scripts"/"python.exe")
 # The historical workspace might be outside the usual folders. Never edit this environment.
 return list(dict.fromkeys(choices))
def find_runtime():
 inspected=[]
 for py in candidate_pythons():
  if not py.is_file():continue
  try:
   proc=subprocess.run([str(py),"-c",
    "import importlib.metadata as m,importlib.util as u,json;"
    "print(json.dumps({'package':m.version('chatterbox-tts'),'module':bool(u.find_spec('chatterbox'))}))"],
    capture_output=True,text=True,timeout=20)
   if proc.returncode:inspected.append({"python":str(py),"error":(proc.stderr or proc.stdout)[-120:]});continue
   row=json.loads(proc.stdout.strip().splitlines()[-1])
   if row.get("module") and row.get("package"):return py,row
  except (ValueError,OSError,subprocess.TimeoutExpired) as e:
   inspected.append({"python":str(py),"error":type(e).__name__})
 raise RuntimeError("CHATTERBOX_RUNTIME_NOT_VERIFIED; checked="+json.dumps(inspected)[:360])
def output_path(ep):return RITSU_RUNS/ep/(ep+".wav")
def verify_render(ep,profile,filter_sha):
 folder=RITSU_RUNS/ep
 rfile=folder/"receipt.json"
 if not rfile.exists():return None
 r=json.loads(rfile.read_text(encoding="utf-8"))
 if r.get("phase")!="rendered_not_delivered" or r.get("sourceReferenceSha256")!=REFERENCE_SHA or r.get("episodeId")!=ep or r.get("profile")!=profile or r.get("presetSha256")!=filter_sha:
  raise RuntimeError("EXISTING_RECEIPT_IDENTITY_MISMATCH")
 p=output_path(ep)
 if not p.is_file() or p.stat().st_size!=r.get("bytes") or sha_file(p)!=r.get("wavSha256"):
  raise RuntimeError("EXISTING_RENDER_IDENTITY_MISMATCH")
 wav_data(p)
 return r
def commit_render(ep,profile,filter_sha,candidate,model_info):
 folder=RITSU_RUNS/ep;folder.mkdir(parents=True,exist_ok=True)
 receipt=verify_render(ep,profile,filter_sha)
 if receipt:return receipt
 target=output_path(ep)
 if target.exists() or (folder/"receipt.json").exists():raise RuntimeError("OUTPUT_COLLISION_NO_OVERWRITE")
 wav_data(candidate)
 # Atomic move within the local disk. Never replace a prior artifact.
 os.rename(candidate,target)
 receipt={"phase":"rendered_not_delivered","engine":"chatterbox","episodeId":ep,"profile":profile,
          "voiceIdentityType":"reference-audio-not-exported-state","voiceSha256":REFERENCE_SHA,
          "sourceReferenceSha256":REFERENCE_SHA,"presetSha256":filter_sha,
          "wavPath":str(target),"wavSha256":sha_file(target),"bytes":target.stat().st_size,
          "durationSeconds":round(wav_data(target),3),"textSha256":sha_bytes(TEXT.encode("utf-8")),
          "modelVersion":model_info["package"],"device":model_info["device"],"speechWatermarked":True,
          "liveRitsuModified":False,"livePocketModified":False}
 atomic(folder/"receipt.json",receipt)
 return receipt
def infer():
 import torch,torchaudio
 from chatterbox.tts import ChatterboxTTS
 source_file=source()
 dryhash=sha_bytes(b"anull")
 deephash=sha_bytes(PITCH_FILTER.encode("utf-8"))
 previous={EP_DRY:verify_render(EP_DRY,"chatterbox-dry",dryhash),
           EP_DEEP:verify_render(EP_DEEP,"chatterbox-minus2",deephash)}
 if all(previous.values()):return status("both_renders_ready_not_delivered",receipts=previous)
 ff=shutil.which("ffmpeg")
 if not ff:raise RuntimeError("FFMPEG_NOT_FOUND")
 proc=subprocess.run([ff,"-hide_banner","-filters"],capture_output=True,text=True,timeout=20)
 if proc.returncode or "rubberband" not in proc.stdout:raise RuntimeError("RUBBERBAND_FILTER_MISSING")
 torch.manual_seed(1737)
 device="cuda" if torch.cuda.is_available() else "cpu"
 status("loading_cached_chatterbox",device=device)
 model=ChatterboxTTS.from_pretrained(device=device)
 modelinfo={"package":importlib.metadata.version("chatterbox-tts"),"device":device}
 status("generating",device=device,modelVersion=modelinfo["package"])
 with tempfile.TemporaryDirectory(prefix="cb-",dir=ROOT) as td:
  folder=Path(td)
  generated=folder/"generated.wav"
  audio=model.generate(TEXT,audio_prompt_path=str(source_file))
  torchaudio.save(str(generated),audio.detach().cpu(),model.sr)
  dry=folder/"dry.wav";deep=folder/"deep.wav"
  def convert(dst,filter_value):
   args=[ff,"-hide_banner","-nostdin","-v","error","-i",str(generated)]
   if filter_value:args+=["-af",filter_value]
   args+=["-ac","1","-ar","24000","-c:a","pcm_s16le",str(dst)]
   p=subprocess.run(args,capture_output=True,text=True,timeout=180)
   if p.returncode:raise RuntimeError("FFMPEG_CONVERSION_FAILED: "+p.stderr[-250:])
   wav_data(dst)
  if not previous[EP_DRY]:
   convert(dry,None);previous[EP_DRY]=commit_render(EP_DRY,"chatterbox-dry",dryhash,dry,modelinfo)
  if not previous[EP_DEEP]:
   convert(deep,PITCH_FILTER)
   previous[EP_DEEP]=commit_render(EP_DEEP,"chatterbox-minus2",deephash,deep,modelinfo)
 return status("both_renders_ready_not_delivered",receipts=previous)
def work():
 import msvcrt
 ROOT.mkdir(parents=True,exist_ok=True)
 lockfile=ROOT/"worker.lock"
 with lockfile.open("a+b") as f:
  f.seek(0);f.write(b"0");f.flush();f.seek(0)
  try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:raise RuntimeError("CHATTERBOX_WORKER_ALREADY_RUNNING")
  try:
   status("preflight")
   source()
   python,installed=find_runtime()
   status("runtime_verified",python=str(python),installedVersion=installed["package"])
   if Path(sys.executable).resolve()!=python.resolve():
    env=dict(os.environ,HF_HUB_OFFLINE="1",HF_DATASETS_OFFLINE="1",TRANSFORMERS_OFFLINE="1")
    p=subprocess.run([str(python),str(Path(__file__).resolve()),"infer"],capture_output=True,text=True,env=env,timeout=1500)
    if p.returncode:raise RuntimeError("CHATTERBOX_INFER_FAILED: "+(p.stderr or p.stdout)[-700:])
    final=json.loads((ROOT/"status.json").read_text(encoding="utf-8"))
    if final.get("phase")!="both_renders_ready_not_delivered":raise RuntimeError("INFER_RECEIPT_NOT_COMPLETE")
    return final
   return infer()
  except Exception as e:
   status("blocked",lastError=type(e).__name__+": "+str(e)[:700])
   raise
  finally:
   f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
def main():
 if sys.argv[1:]==["work"]:print(json.dumps(work()));return
 if sys.argv[1:]==["infer"]:print(json.dumps(infer()));return
 if sys.argv[1:]==["status"]:
  f=ROOT/"status.json";print(f.read_text(encoding="utf-8") if f.exists() else json.dumps({"phase":"not_started"}));return
 raise SystemExit("Use work, infer or status")
if __name__=="__main__":main()
