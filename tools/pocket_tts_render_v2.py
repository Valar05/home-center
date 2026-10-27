#!/usr/bin/env python3
"""Fail-closed Pocket TTS rendering contract for Home Center."""
from __future__ import annotations
import hashlib, importlib.metadata, json, math, os, random, shutil, subprocess, tempfile, time, wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

CONTRACT_VERSION="pocket-tts-render-v3"
VOICE_PROFILE_ID="vera-venice-close-mic-v1"
BUILTIN_VOICE="vera"
VENICE_AUDIO_FILTER="highpass=f=90,lowpass=f=7800,equalizer=f=260:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1:g=3,acompressor=threshold=-28dB:ratio=3:attack=10:release=120,volume=1.18"
VENICE_SOURCE_COMMIT="48adffbbafe96d8e68595839438cd65b90020e18"
VENICE_SOURCE_SHA256="1B8993BAE19EB58E4EE0A5A064848D34BA34AC36D4B2A3AA158ACDAD329C2BDE"
MAX_TOKENS=50
SAMPLE_RATE=24_000
class RenderRejected(RuntimeError): pass

def normalized_text(text:str)->str: return " ".join(text.split())
def sha256_bytes(data:bytes)->str: return hashlib.sha256(data).hexdigest()

def atomic_json(path:Path, value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=f".{path.name}.",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(value,out,ensure_ascii=False,indent=2,sort_keys=True); out.write("\n"); out.flush(); os.fsync(out.fileno())
        os.replace(name,path)
    finally: Path(name).unlink(missing_ok=True)

def token_count(tokenizer:Any,text:str)->int:
    tokens=tokenizer(text).tokens[0]
    return int(tokens.numel() if hasattr(tokens,"numel") else len(tokens))

def split_token_hard(text:str,tokenizer:Any,max_tokens:int=MAX_TOKENS)->list[str]:
    canonical=normalized_text(text)
    if not canonical: raise RenderRejected("section text is empty")
    words=canonical.split(" "); units=[]; start=0
    while start<len(words):
        low,high,best=start+1,len(words),start
        while low<=high:
            middle=(low+high)//2; candidate=" ".join(words[start:middle])
            if token_count(tokenizer,candidate)<=max_tokens: best=middle; low=middle+1
            else: high=middle-1
        if best==start: raise RenderRejected(f"single word exceeds the {max_tokens}-token limit: {words[start][:80]!r}")
        units.append(" ".join(words[start:best])); start=best
    if normalized_text(" ".join(units))!=canonical: raise RenderRejected("token splitting changed source text")
    if max(token_count(tokenizer,u) for u in units)>max_tokens: raise RenderRejected("hard token limit was not enforced")
    return units

def pcm_metrics(pcm:bytes,sample_rate:int=SAMPLE_RATE)->dict[str,Any]:
    if len(pcm)<2 or len(pcm)%2: raise RenderRejected("PCM is empty or partial")
    samples=array("h"); samples.frombytes(pcm)
    if os.sys.byteorder!="little": samples.byteswap()
    count=len(samples); duration=count/float(sample_rate); peak=max(abs(v) for v in samples)/32768.0
    clipping=sum(1 for v in samples if abs(v)>=32760)/count
    tail_count=min(count,sample_rate*5); tail=samples[-tail_count:]
    tail_rms=math.sqrt(sum(float(v)*v for v in tail)/tail_count)/32768.0
    crossings=sum(1 for a,b in zip(tail,tail[1:]) if (a<0<=b) or (b<0<=a)); tail_zcr=crossings/max(1,tail_count-1)
    corrupt=duration>=8 and tail_count>=sample_rate*5 and tail_rms<0.008 and tail_zcr>0.12
    return {"frames":count,"durationSeconds":round(duration,6),"peak":round(peak,6),"clippingFraction":round(clipping,8),"tailRms":round(tail_rms,8),"tailZeroCrossingRate":round(tail_zcr,8),"corruptTail":corrupt}

def validate_pcm(pcm:bytes,tokens:int,words:int,sample_rate:int=SAMPLE_RATE)->dict[str,Any]:
    metrics=pcm_metrics(pcm,sample_rate); duration=float(metrics["durationSeconds"])
    ceiling=(tokens/3.0+2.0)*0.98; floor=max(0.35,words*0.10)
    if duration>ceiling: raise RenderRejected(f"audio duration {duration:.2f}s exceeds {ceiling:.2f}s ceiling")
    if duration<floor: raise RenderRejected(f"audio duration {duration:.2f}s is below {floor:.2f}s floor")
    if float(metrics["clippingFraction"])>0.001: raise RenderRejected("audio clips more than 0.1% of samples")
    if metrics["corruptTail"]: raise RenderRejected("audio ends in a low-energy high-frequency corruption tail")
    return metrics

def inspect_wav(path:Path)->dict[str,Any]:
    try:
        with wave.open(str(path),"rb") as audio:
            channels,width,rate,frames=audio.getnchannels(),audio.getsampwidth(),audio.getframerate(),audio.getnframes(); pcm=audio.readframes(frames)
    except (EOFError,OSError,wave.Error) as exc: raise RenderRejected(f"unreadable WAV: {exc}") from exc
    if channels!=1 or width!=2 or rate!=SAMPLE_RATE or frames<1 or len(pcm)!=frames*2:
        raise RenderRejected(f"WAV must be nonempty 24kHz mono PCM16, got rate={rate} channels={channels} width={width} frames={frames}")
    return {"sampleRate":rate,"channels":channels,"sampleWidth":width,**pcm_metrics(pcm,rate)}

def doctor_wav(path:Path)->dict[str,Any]:
    try:
        metrics=inspect_wav(path)
        if metrics["corruptTail"]: raise RenderRejected("audio ends in a low-energy high-frequency corruption tail")
        return {"status":"accepted","path":str(path),**metrics}
    except RenderRejected as exc: return {"status":"rejected","path":str(path),"error":str(exc)}

@dataclass
class GeneratedUnit:
    pcm:bytes
    eos_observed:bool=True

class PocketTtsEngine:
    def __init__(self,*,tokenizer:Any|None=None,generator:Callable[[str,int],GeneratedUnit]|None=None,voice:str|None=BUILTIN_VOICE,language:str|None=None,voice_profile_id:str=VOICE_PROFILE_ID,audio_filter:str=VENICE_AUDIO_FILTER,ffmpeg_path:str|None=None):
        self.model=None; self.voice_state=None; self.tokenizer=tokenizer; self.generator=generator; self.voice=voice or BUILTIN_VOICE; self.language=language
        self.voice_profile_id=voice_profile_id; self.audio_filter=audio_filter; self.ffmpeg_path=ffmpeg_path
        self.model_loaded=tokenizer is not None and generator is not None
    def load(self)->None:
        if self.model_loaded:return
        os.environ["KPOCKET_TTS_ERROR_WITHOUT_EOS"]="1"
        from pocket_tts import TTSModel
        self.model=TTSModel.load_model(language=self.language); self.model.to("cpu")
        self.voice_state=self.model.get_state_for_audio_prompt(self.voice)
        self.tokenizer=self.model.flow_lm.conditioner.tokenizer
        def generate(unit:str,seed:int)->GeneratedUnit:
            import torch
            random.seed(seed); torch.manual_seed(seed)
            audio=self.model.generate_audio(self.voice_state,unit,max_tokens=MAX_TOKENS,copy_state=True)
            values=audio.detach().cpu().float().reshape(-1).clamp(-1.0,1.0)
            return GeneratedUnit((values*32767.0).round().to(torch.int16).numpy().tobytes())
        self.generator=generate; self.model_loaded=True
    def _filter_wav(self,source:Path,target:Path)->None:
        if not self.audio_filter:
            shutil.copyfile(source,target); return
        executable=self.ffmpeg_path or os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg"
        command=[executable,"-hide_banner","-loglevel","error","-y","-i",str(source),"-af",self.audio_filter,"-ar",str(SAMPLE_RATE),"-ac","1","-c:a","pcm_s16le",str(target)]
        try:
            process=subprocess.run(command,capture_output=True,text=True,timeout=int(os.environ.get("POCKET_TTS_FILTER_TIMEOUT_SECONDS","30")),check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise RenderRejected(f"Vera close-mic filter unavailable: {exc}") from exc
        if process.returncode!=0 or not target.is_file() or target.stat().st_size<=44:
            detail=(process.stderr or process.stdout or f"ffmpeg exit {process.returncode}")[-500:]
            raise RenderRejected(f"Vera close-mic filter failed: {detail}")
    def render(self,text:str,output:Path,request_id:str,backend:str="local")->dict[str,Any]:
        self.load(); assert self.tokenizer is not None and self.generator is not None
        canonical=normalized_text(text); text_hash=sha256_bytes(canonical.encode()); units=split_token_hard(canonical,self.tokenizer)
        started=time.monotonic(); all_pcm=bytearray(); unit_receipts=[]
        for index,unit in enumerate(units):
            tokens=token_count(self.tokenizer,unit); last_error=None
            for attempt in range(2):
                seed=int(hashlib.sha256(f"{text_hash}:{index}:{attempt}".encode()).hexdigest()[:8],16)
                try:
                    generated=self.generator(unit,seed)
                    if not generated.eos_observed: raise RenderRejected("generation reached its limit without EOS")
                    metrics=validate_pcm(generated.pcm,tokens,len(unit.split())); all_pcm.extend(generated.pcm)
                    unit_receipts.append({"index":index,"textSha256":sha256_bytes(unit.encode()),"tokenCount":tokens,"wordCount":len(unit.split()),"seed":seed,"attempt":attempt+1,"eosObserved":True,**metrics}); break
                except Exception as exc: last_error=exc
            else: raise RenderRejected(f"unit {index} failed both deterministic attempts: {last_error}") from last_error
        output=output.resolve(); output.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix=f".{output.name}.",suffix=".raw.wav",dir=output.parent); os.close(fd)
        raw=Path(name); filtered=raw.with_name(raw.name+".filtered.wav")
        try:
            with wave.open(str(raw),"wb") as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(SAMPLE_RATE); audio.writeframes(bytes(all_pcm))
            self._filter_wav(raw,filtered)
            artifact=inspect_wav(filtered)
            if float(artifact["clippingFraction"])>0.001: raise RenderRejected("filtered audio clips more than 0.1% of samples")
            if artifact["corruptTail"]: raise RenderRejected("filtered audio ends in a low-energy high-frequency corruption tail")
            artifact_hash=sha256_bytes(filtered.read_bytes()); os.replace(filtered,output)
        finally:
            raw.unlink(missing_ok=True); filtered.unlink(missing_ok=True)
        elapsed=time.monotonic()-started
        receipt={"status":"complete","accepted":True,"contractVersion":CONTRACT_VERSION,"voiceProfileId":self.voice_profile_id,"voice":self.voice,"audioFilter":self.audio_filter,"audioFilterOwner":"Venice live runtime on THECAULDRON","audioFilterSourceCommit":VENICE_SOURCE_COMMIT,"audioFilterSourceSha256":VENICE_SOURCE_SHA256,"requestId":request_id,"textSha256":text_hash,"artifactSha256":artifact_hash,"output":str(output),"backend":backend,"modelPackage":"pocket-tts","modelPackageVersion":importlib.metadata.version("pocket-tts"),"maxTokensPerUnit":MAX_TOKENS,"unitCount":len(unit_receipts),"units":unit_receipts,"renderSeconds":round(elapsed,6),"realTimeFactor":round(elapsed/max(.001,float(artifact["durationSeconds"])),6),**artifact}
        atomic_json(output.with_suffix(".json"),receipt); return receipt

def validate_receipt(wav:Path,receipt:Path|None=None,*,text:str|None=None,voice_profile_id:str=VOICE_PROFILE_ID,audio_filter:str=VENICE_AUDIO_FILTER)->dict[str,Any]:
    receipt=receipt or wav.with_suffix(".json")
    try:data=json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise RenderRejected(f"missing or invalid v3 receipt: {exc}") from exc
    if data.get("status")!="complete" or data.get("accepted") is not True or data.get("contractVersion")!=CONTRACT_VERSION: raise RenderRejected("receipt is not an accepted Pocket TTS v3 receipt")
    if data.get("voiceProfileId")!=voice_profile_id or data.get("voice")!=BUILTIN_VOICE or data.get("audioFilter")!=audio_filter: raise RenderRejected("receipt voice profile does not match Vera close-mic v1")
    if data.get("artifactSha256")!=sha256_bytes(wav.read_bytes()): raise RenderRejected("receipt artifact hash does not match WAV")
    if text is not None and data.get("textSha256")!=sha256_bytes(normalized_text(text).encode()): raise RenderRejected("receipt text hash does not match request text")
    metrics=inspect_wav(wav)
    if float(metrics["clippingFraction"])>0.001: raise RenderRejected("WAV clips more than 0.1% of samples")
    if metrics["corruptTail"]: raise RenderRejected("WAV fails corruption-tail gate")
    return data
