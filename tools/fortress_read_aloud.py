#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shlex, struct, subprocess, sys, time, wave
from pathlib import Path
from typing import Iterable, Iterator

REPO=Path(os.environ.get('FORTRESS_HOME_CENTER','/storage/emulated/0/Documents/GodotProjects/home-center'))
VOICE_CONFIG=Path(os.environ.get('FORTRESS_ADAM_VOICE_CONFIG',str(REPO/'config/fortress-adam-voice.json')))
AUDIO_ROOT=Path('/storage/emulated/0/Documents/FortressAudio')
POCKET_PHONE=Path.home()/'bin/pocket-tts-phone'
DEFAULT_CHUNK=700


def find_rish()->Path|None:
    candidates=[
        os.environ.get('RISH',''),
        str(Path.home()/'bin/rish'),
        str(Path.home()/'rish'),
        '/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish',
        '/storage/emulated/0/Documents/rish',
        '/storage/emulated/0/Download/rish',
    ]
    for raw in candidates:
        if raw:
            p=Path(raw).expanduser()
            if p.is_file(): return p
    return None


def profile():
    raw=json.loads(VOICE_CONFIG.read_text(encoding='utf-8')) if VOICE_CONFIG.exists() else {}
    delivery=raw.get('delivery',{}); voice=raw.get('voice',{})
    return {
        'id':raw.get('id','adam-phone'),'displayName':raw.get('displayName','Adam'),
        'language':raw.get('language','english'),'engine':'pocket-tts-phone+home-center-playback+rish',
        'voiceKind':voice.get('kind','builtin'),'voiceValue':voice.get('value','michael'),
        'chunkChars':int(os.environ.get('FORTRESS_READ_ALOUD_CHUNK',delivery.get('chunkChars',DEFAULT_CHUNK))),
        'tempo':float(delivery.get('tempo',1.0)),'volume':float(delivery.get('volume',1.0)),
        'pitchSemitones':float(delivery.get('pitchSemitones',0.0)),'prefetchChunks':0,
        'style':delivery.get('style',''),'canonicalProvider':'pocket-home-center','allowSystemFallback':False,
    }


def doctor():
    p=profile(); pocket=POCKET_PHONE.is_file() and os.access(POCKET_PHONE,os.X_OK); rish=find_rish()
    ok=bool(pocket and rish)
    return {'ok':ok,'preferred':'pocket-home-center' if ok else '','canonicalProvider':'pocket-home-center','voiceProfile':p,
            'pocketPhone':str(POCKET_PHONE) if pocket else '','androidLaunchTransport':'shizuku-rish','rish':str(rish) if rish else '',
            'systemFallbackAllowed':False,'blockedReason':'' if ok else ('pocket-tts-phone missing' if not pocket else 'Shizuku rish unavailable'),
            'textChunkChars':p['chunkChars'],'prefetchChunks':0,'batching':False,'cloudFallback':False}


def chunk_text_piece(text:str)->Iterator[str]:
    limit=profile()['chunkChars']; text=' '.join(str(text or '').split()).strip()
    while text:
        if len(text)<=limit: yield text; return
        window=text[:limit+1]; cuts=[window.rfind(x) for x in ('. ','? ','! ','; ',': ', ', ')]; cut=max(cuts)
        if cut<limit//3: cut=window.rfind(' ')
        if cut<limit//3: cut=limit
        else: cut+=1
        yield text[:cut].strip(); text=text[cut:].strip()


def chunks_from_text(text:str)->Iterator[str]: yield from chunk_text_piece(text)

def chunks_from_file(path:str)->Iterator[str]:
    p=Path(path).expanduser(); p=p if p.is_absolute() else (Path.cwd()/p).resolve()
    if not p.is_file(): raise FileNotFoundError(path)
    buf=''; limit=profile()['chunkChars']
    with p.open('r',encoding='utf-8',errors='replace') as f:
        for raw in f:
            line=raw.strip()
            if not line:
                if buf: yield from chunk_text_piece(buf); buf=''
                continue
            candidate=(buf+' '+line).strip()
            if len(candidate)>=limit: yield from chunk_text_piece(candidate); buf=''
            else: buf=candidate
    if buf: yield from chunk_text_piece(buf)

def chunks_from_stdin()->Iterator[str]:
    buf=''; limit=profile()['chunkChars']
    for raw in sys.stdin:
        line=raw.strip()
        if not line:
            if buf: yield from chunk_text_piece(buf); buf=''
            continue
        candidate=(buf+' '+line).strip()
        if len(candidate)>=limit: yield from chunk_text_piece(candidate); buf=''
        else: buf=candidate
    if buf: yield from chunk_text_piece(buf)


def fix_wav_header(path:Path):
    data=path.read_bytes()
    if len(data)<44 or data[:4]!=b'RIFF' or data[8:12]!=b'WAVE': raise RuntimeError('Pocket output is not a WAV')
    b=bytearray(data); struct.pack_into('<I',b,4,len(b)-8)
    pos=12
    while pos+8<=len(b):
        name=bytes(b[pos:pos+4]); size=struct.unpack_from('<I',b,pos+4)[0]
        if name==b'data': struct.pack_into('<I',b,pos+4,len(b)-(pos+8)); break
        pos+=8+size+(size&1)
        if pos>len(b): break
    path.write_bytes(b)


def duration(path:Path)->float:
    with wave.open(str(path),'rb') as w: return w.getnframes()/float(w.getframerate())


def synthesize_chunk(text:str,index:int,p:dict)->Path:
    AUDIO_ROOT.mkdir(parents=True,exist_ok=True)
    work=AUDIO_ROOT/f'.adam-{os.getpid()}-{index}'
    work.mkdir(parents=True,exist_ok=True)
    cmd=[str(POCKET_PHONE),'generate','--text',text,'--voice',p['voiceValue'],'--language',p['language']]
    proc=subprocess.run(cmd,cwd=work,text=True,capture_output=True,timeout=180,check=False)
    if proc.returncode: raise RuntimeError((proc.stderr or proc.stdout or f'PocketTTS failed ({proc.returncode})')[-3000:])
    generated=work/'tts_output.wav'
    if not generated.is_file(): raise RuntimeError('PocketTTS completed without tts_output.wav')
    fix_wav_header(generated)
    final=AUDIO_ROOT/f'adam-{os.getpid()}-{index}.wav'; generated.replace(final)
    try: work.rmdir()
    except OSError: pass
    return final


def run_rish(command:str,timeout:float=20.0)->str:
    rish=find_rish()
    if not rish: raise RuntimeError('ADAM VOICE BLOCKED: Shizuku rish unavailable')
    proc=subprocess.run([str(rish),'-c',command],text=True,capture_output=True,timeout=timeout,check=False)
    if proc.returncode: raise RuntimeError((proc.stderr or proc.stdout or f'rish failed ({proc.returncode})')[-3000:])
    return proc.stdout


def play_home_center(path:Path)->float:
    seconds=duration(path)
    component='com.dclar.homecenter/.PocketTtsPlaybackActivity'
    command='am start -W -n '+shlex.quote(component)+' --es file '+shlex.quote(str(path))
    run_rish(command,20)
    time.sleep(max(0.05,seconds+0.12))
    return seconds


def speak(chunks:Iterable[str],provider='auto'):
    if provider=='termux': raise RuntimeError('BLOCKED: system TTS is not Adam')
    d=doctor()
    if not d['ok']: raise RuntimeError('ADAM VOICE BLOCKED: '+d['blockedReason'])
    p=profile(); count=chars=0; seconds=0.0; files=[]
    try:
        for index,text_chunk in enumerate(chunks):
            count+=1; chars+=len(text_chunk)
            wav=synthesize_chunk(text_chunk,index,p); files.append(wav)
            seconds+=play_home_center(wav)
            try: wav.unlink()
            except OSError: pass
        return {'ok':True,'provider':'pocket-home-center','transport':'shizuku-rish','voiceProfile':p['id'],'voice':p['voiceValue'],
                'textChunks':count,'characters':chars,'audioSeconds':round(seconds,3),'batching':False,'prefetchChunks':0}
    finally:
        for wav in files:
            try: wav.unlink()
            except OSError: pass


def main():
    ap=argparse.ArgumentParser(prog='fortress-read',description='Adam: Pocket TTS through Home Center playback launched via Shizuku/rish')
    ap.add_argument('--doctor',action='store_true'); ap.add_argument('--profile',action='store_true'); ap.add_argument('--file')
    ap.add_argument('--provider',choices=['auto','pocket','termux'],default='auto'); ap.add_argument('text',nargs='*'); a=ap.parse_args()
    if a.doctor: out=doctor()
    elif a.profile: out=profile()
    elif a.file: out=speak(chunks_from_file(a.file),a.provider)
    elif a.text: out=speak(chunks_from_text(' '.join(a.text)),a.provider)
    else: out=speak(chunks_from_stdin(),a.provider)
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__': main()
