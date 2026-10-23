"""One-shot Pocket TTS whisper-clone trial, with unmodified reference and output."""
from pathlib import Path
import json, os, wave, urllib.request, traceback, time
import numpy as np
from pocket_tts import TTSModel

HOME=Path.home()
POCKET=HOME/'Documents'/'Codex'/'Venice'/'PocketTTS'
REF=HOME/'workspace'/'ritsu-expresso-auditions'/'ex04_whisper_00059.wav'
OUT=HOME/'workspace'/'ritsu-chatterbox-turbo'/'generated'
RELAY=POCKET/'embodiment_campaign'
RESULT=Path(os.environ.get('LOCALAPPDATA',str(HOME)))/'RitsuWarmTicketWorker'/'pocket-whisper-test.json'
FILENAME='ritsu-pocket-whisper-clone-20261023.wav'
TEXT='Come closer, darling. I have something lovely to tell you.'
def write(status, **details):
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps({'status':status,**details},indent=2),encoding='utf-8')
write('loading_model')
try:
    if not REF.is_file():raise FileNotFoundError('Whisper reference missing')
    model=TTSModel.load_model(language='english')
    model.to('cpu')
    write('cloning_reference')
    voice=model.get_state_for_audio_prompt(REF)
    generated=model.generate_audio(voice,TEXT,max_tokens=120)
    samples=generated.detach().cpu().float().reshape(-1).numpy()
    if not len(samples):raise RuntimeError('Pocket returned no samples')
    if not np.isfinite(samples).all():raise RuntimeError('Pocket produced invalid samples')
    rate=int(model.config.mimi.sample_rate)
    OUT.mkdir(parents=True,exist_ok=True)
    destination=OUT/FILENAME
    with wave.open(str(destination),'wb') as dst:
        dst.setnchannels(1);dst.setsampwidth(2);dst.setframerate(rate)
        dst.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
    write('rendered',file=str(destination),durationSeconds=round(len(samples)/rate,2),sampleRate=rate)
    token=(RELAY/'relay-token.txt').read_text(encoding='utf-8').strip()
    data=json.dumps({'text':'__TURBO_WAV__:'+FILENAME,'character':'ritsu'}).encode('utf-8')
    req=urllib.request.Request('http://127.0.0.1:19643/enqueue',data=data,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=20) as response:receipt=json.load(response)
    if not receipt.get('id'):raise RuntimeError('Phone relay did not return a receipt')
    write('enqueued_not_heard',file=str(destination),durationSeconds=round(len(samples)/rate,2),relayId=receipt['id'],sampleRate=rate)
    print('POCKET_WHISPER_ENQUEUED',receipt['id'],flush=True)
except Exception as exc:
    write('failed',error=type(exc).__name__+': '+str(exc)[:250])
    print('POCKET_WHISPER_FAILED',type(exc).__name__,flush=True)
    raise
