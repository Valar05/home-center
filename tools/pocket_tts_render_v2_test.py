#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math, tempfile
from pathlib import Path
from pocket_tts_render_v2 import BUILTIN_VOICE,CONTRACT_VERSION,GeneratedUnit,PocketTtsEngine,RenderRejected,SAMPLE_RATE,VENICE_AUDIO_FILTER,VOICE_PROFILE_ID,doctor_wav,normalized_text,split_token_hard,validate_receipt
class FakeTokens:
    def __init__(self,count:int): self.tokens=[list(range(count))]
class WordTokenizer:
    def __call__(self,text:str): return FakeTokens(len(text.split()))
def clean_pcm(seconds:float)->bytes:
    values=bytearray()
    for i in range(int(seconds*SAMPLE_RATE)):
        sample=int(5000*math.sin(2*math.pi*180*i/SAMPLE_RATE)); values.extend(sample.to_bytes(2,"little",signed=True))
    return bytes(values)
source=" ".join(f"token-{i}" for i in range(632)); units=split_token_hard(source,WordTokenizer())
assert len(units)==13 and max(len(u.split()) for u in units)<=50
assert normalized_text(" ".join(units))==normalized_text(source)
calls=[]
def synth(text:str,seed:int)->GeneratedUnit:
    calls.append((text,seed)); return GeneratedUnit(clean_pcm(max(.5,len(text.split())*.11)))
with tempfile.TemporaryDirectory(prefix="pocket-tts-v3-") as temp:
    base=Path(temp); wav=base/"section.wav"
    receipt=PocketTtsEngine(tokenizer=WordTokenizer(),generator=synth).render(source,wav,"fixture-632")
    assert receipt["contractVersion"]==CONTRACT_VERSION and receipt["unitCount"]==13 and len(calls)==13
    assert receipt["voiceProfileId"]==VOICE_PROFILE_ID and receipt["voice"]==BUILTIN_VOICE=="vera"
    assert receipt["audioFilter"]==VENICE_AUDIO_FILTER
    validate_receipt(wav,text=source)
    ablated=base/"ablated.wav"
    PocketTtsEngine(tokenizer=WordTokenizer(),generator=synth,voice_profile_id="test-ablated",audio_filter="").render(source,ablated,"fixture-632-ablated")
    assert hashlib.sha256(wav.read_bytes()).hexdigest()!=hashlib.sha256(ablated.read_bytes()).hexdigest(),"filter ablation did not change output"
    unavailable=base/"ffmpeg-unavailable.wav"
    try:
        PocketTtsEngine(tokenizer=WordTokenizer(),generator=synth,ffmpeg_path=str(base/"missing-ffmpeg")).render("filter dependency canary",unavailable,"missing-ffmpeg")
        raise AssertionError("missing FFmpeg accepted")
    except RenderRejected: pass
    assert not unavailable.exists() and not unavailable.with_suffix(".json").exists(),"failed filter published an artifact or receipt"
    baseline=json.loads(wav.with_suffix(".json").read_text())
    stale={**baseline,"contractVersion":"pocket-tts-render-v2"}; wav.with_suffix(".json").write_text(json.dumps(stale))
    try: validate_receipt(wav,text=source); raise AssertionError("stale contract accepted")
    except RenderRejected: pass
    wrong_profile={**baseline,"voiceProfileId":"default"}; wav.with_suffix(".json").write_text(json.dumps(wrong_profile))
    try: validate_receipt(wav,text=source); raise AssertionError("wrong voice profile accepted")
    except RenderRejected: pass
    wrong_hash={**baseline,"artifactSha256":"0"*64}; wav.with_suffix(".json").write_text(json.dumps(wrong_hash))
    try: validate_receipt(wav,text=source); raise AssertionError("wrong artifact hash accepted")
    except RenderRejected: pass
attempts=0
def no_eos(text:str,seed:int)->GeneratedUnit:
    global attempts; attempts+=1; return GeneratedUnit(clean_pcm(.5),False)
try: PocketTtsEngine(tokenizer=WordTokenizer(),generator=no_eos).render("small fixture",Path(tempfile.gettempdir())/"must-not-publish.wav","no-eos"); raise AssertionError("no-EOS accepted")
except RenderRejected: assert attempts==2
known_bad=Path("/storage/emulated/0/Documents/FortressAudio/HomeCenterPocketTts/hc-1B_nUq6e7sLGwOuI8zeJegftMTDzCWuWX-91ffc9b759063b31-000007-5f88b4a04b756ead.wav")
if known_bad.exists():
    verdict=doctor_wav(known_bad); assert verdict["status"]=="rejected",verdict
print("Pocket TTS render v3 Vera close-mic contract: OK")
