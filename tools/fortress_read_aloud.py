#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path
from typing import Iterable, Iterator

REPO=Path(os.environ.get('FORTRESS_HOME_CENTER','/storage/emulated/0/Documents/GodotProjects/home-center'))
VOICE_CONFIG=Path(os.environ.get('FORTRESS_ADAM_VOICE_CONFIG',str(REPO/'config/fortress-adam-voice.json')))
DEFAULT_CHUNK=700


def profile():
    raw=json.loads(VOICE_CONFIG.read_text(encoding='utf-8')) if VOICE_CONFIG.exists() else {}
    delivery=raw.get('delivery',{})
    voice=raw.get('voice',{})
    return {
        'id':raw.get('id','adam-phone'),
        'displayName':raw.get('displayName','Adam'),
        'language':raw.get('language','english'),
        'voiceKind':voice.get('kind','builtin'),
        'voiceValue':voice.get('value','michael'),
        'chunkChars':int(os.environ.get('FORTRESS_READ_ALOUD_CHUNK',delivery.get('chunkChars',DEFAULT_CHUNK))),
        'tempo':float(delivery.get('tempo',1.0)),
        'volume':float(delivery.get('volume',1.0)),
        'prefetchChunks':int(delivery.get('prefetchChunks',0)),
        'style':delivery.get('style',''),
    }


def doctor():
    p=profile()
    try:
        import pocket_tts  # noqa: F401
        pocket=True
    except Exception:
        pocket=False
    ffplay=shutil.which('ffplay')
    termux=shutil.which('termux-tts-speak')
    return {
      'ok': bool((pocket and ffplay) or termux),
      'preferred': 'pocket-stream' if pocket and ffplay else ('termux' if termux else ''),
      'voiceProfile':p,
      'pocketPython': pocket,
      'ffplay': ffplay or '',
      'termux': termux or '',
      'textChunkChars': p['chunkChars'],
      'prefetchChunks': 0,
      'batching': False,
      'cloudFallback': False,
    }


def chunk_text_piece(text:str) -> Iterator[str]:
    limit=profile()['chunkChars']
    text=' '.join(str(text or '').split()).strip()
    while text:
        if len(text)<=limit:
            yield text
            return
        window=text[:limit+1]
        cuts=[window.rfind(x) for x in ('. ','? ','! ','; ',': ', ', ')]
        cut=max(cuts)
        if cut < limit//3:
            cut=window.rfind(' ')
        if cut < limit//3:
            cut=limit
        else:
            cut += 1
        yield text[:cut].strip()
        text=text[cut:].strip()


def chunks_from_text(text:str) -> Iterator[str]:
    yield from chunk_text_piece(text)


def chunks_from_file(path:str) -> Iterator[str]:
    p=Path(path).expanduser()
    if not p.is_absolute(): p=(Path.cwd()/p).resolve()
    if not p.exists() or not p.is_file(): raise FileNotFoundError(path)
    buf=''
    limit=profile()['chunkChars']
    with p.open('r',encoding='utf-8',errors='replace') as f:
        for raw in f:
            line=raw.strip()
            if not line:
                if buf:
                    yield from chunk_text_piece(buf)
                    buf=''
                continue
            candidate=(buf+' '+line).strip()
            if len(candidate)>=limit:
                yield from chunk_text_piece(candidate)
                buf=''
            else:
                buf=candidate
    if buf:
        yield from chunk_text_piece(buf)


def chunks_from_stdin() -> Iterator[str]:
    buf=''
    limit=profile()['chunkChars']
    for raw in sys.stdin:
        line=raw.strip()
        if not line:
            if buf:
                yield from chunk_text_piece(buf); buf=''
            continue
        candidate=(buf+' '+line).strip()
        if len(candidate)>=limit:
            yield from chunk_text_piece(candidate); buf=''
        else:
            buf=candidate
    if buf: yield from chunk_text_piece(buf)


def _voice_prompt(model,p):
    value=p['voiceValue']
    # Pocket accepts built-in voice names, local wav/audio references, or exported
    # safetensors voice states through the same prompt-loading API.
    return model.get_state_for_audio_prompt(value)


def speak_pocket(chunks:Iterable[str]):
    from pocket_tts import TTSModel
    p=profile()
    ffplay=shutil.which('ffplay')
    if not ffplay: raise RuntimeError('ffplay unavailable for Pocket streaming playback')
    model=TTSModel.load_model(language=p['language'])
    voice=_voice_prompt(model,p)
    filters=[]
    if abs(p['tempo']-1.0)>0.001: filters.append(f"atempo={max(0.5,min(p['tempo'],2.0)):.3f}")
    if abs(p['volume']-1.0)>0.001: filters.append(f"volume={max(0.0,min(p['volume'],2.0)):.3f}")
    cmd=[ffplay,'-loglevel','error','-nodisp','-autoexit','-f','f32le','-ar',str(model.sample_rate),'-ac','1']
    if filters: cmd += ['-af',','.join(filters)]
    cmd += ['pipe:0']
    player=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    count=0; chars=0; audio_chunks=0
    try:
        assert player.stdin is not None
        for text_chunk in chunks:
            count+=1; chars+=len(text_chunk)
            for pcm in model.generate_audio_stream(voice,text_chunk,copy_state=True):
                raw=pcm.detach().cpu().float().numpy().tobytes()
                player.stdin.write(raw)
                player.stdin.flush()
                audio_chunks+=1
        player.stdin.close()
        rc=player.wait(timeout=120)
        if rc:
            err=(player.stderr.read().decode('utf-8','replace') if player.stderr else '')[-3000:]
            raise RuntimeError(err or f'ffplay failed ({rc})')
    except Exception:
        try: player.kill()
        except Exception: pass
        raise
    return {'ok':True,'provider':'pocket-stream','voiceProfile':p['id'],'voice':p['voiceValue'],'textChunks':count,'audioChunks':audio_chunks,'characters':chars,'batching':False,'prefetchChunks':0}


def speak_termux(chunks:Iterable[str]):
    exe=shutil.which('termux-tts-speak')
    if not exe: raise RuntimeError('termux-tts-speak unavailable')
    count=0; chars=0
    for chunk in chunks:
        count+=1; chars+=len(chunk)
        p=subprocess.run([exe,chunk],text=True,capture_output=True,timeout=90,check=False)
        if p.returncode: raise RuntimeError((p.stderr or p.stdout or f'Termux TTS failed ({p.returncode})')[-3000:])
    return {'ok':True,'provider':'termux','voiceProfile':'system-fallback','textChunks':count,'characters':chars,'batching':False,'prefetchChunks':0}


def speak(chunks:Iterable[str],provider='auto'):
    d=doctor(); selected=provider
    if selected=='auto': selected=d['preferred']
    if selected=='pocket': selected='pocket-stream'
    if selected=='pocket-stream': return speak_pocket(chunks)
    if selected=='termux': return speak_termux(chunks)
    raise RuntimeError('no local streaming TTS provider available')


def main():
    ap=argparse.ArgumentParser(prog='fortress-read',description='Adam: Pocket-first bounded streaming read aloud for Fortress')
    ap.add_argument('--doctor',action='store_true')
    ap.add_argument('--profile',action='store_true')
    ap.add_argument('--file')
    ap.add_argument('--provider',choices=['auto','pocket','termux'],default='auto')
    ap.add_argument('text',nargs='*')
    a=ap.parse_args()
    if a.doctor:
        out=doctor()
    elif a.profile:
        out=profile()
    elif a.file:
        out=speak(chunks_from_file(a.file),a.provider)
    elif a.text:
        out=speak(chunks_from_text(' '.join(a.text)),a.provider)
    else:
        out=speak(chunks_from_stdin(),a.provider)
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__': main()
