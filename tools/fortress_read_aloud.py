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
        'engine':raw.get('engine','pocket-tts'),
        'voiceKind':voice.get('kind','builtin'),
        'voiceValue':voice.get('value','michael'),
        'chunkChars':int(os.environ.get('FORTRESS_READ_ALOUD_CHUNK',delivery.get('chunkChars',DEFAULT_CHUNK))),
        'tempo':float(delivery.get('tempo',1.0)),
        'volume':float(delivery.get('volume',1.0)),
        'pitchSemitones':float(delivery.get('pitchSemitones',0.0)),
        'prefetchChunks':int(delivery.get('prefetchChunks',0)),
        'style':delivery.get('style',''),
        'canonicalProvider':'pocket-stream',
        'allowSystemFallback':False,
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
    canonical_ok=bool(pocket and ffplay)
    return {
      'ok': canonical_ok,
      'preferred': 'pocket-stream' if canonical_ok else '',
      'canonicalProvider':'pocket-stream',
      'voiceProfile':p,
      'pocketPython': pocket,
      'ffplay': ffplay or '',
      'termuxFallbackPresent': termux or '',
      'systemFallbackAllowed': False,
      'blockedReason': '' if canonical_ok else ('ffplay missing' if pocket else 'pocket_tts missing'),
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
        if cut < limit//3: cut=window.rfind(' ')
        if cut < limit//3: cut=limit
        else: cut += 1
        yield text[:cut].strip(); text=text[cut:].strip()


def chunks_from_text(text:str) -> Iterator[str]: yield from chunk_text_piece(text)


def chunks_from_file(path:str) -> Iterator[str]:
    p=Path(path).expanduser()
    if not p.is_absolute(): p=(Path.cwd()/p).resolve()
    if not p.exists() or not p.is_file(): raise FileNotFoundError(path)
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


def chunks_from_stdin() -> Iterator[str]:
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


def _voice_prompt(model,p): return model.get_state_for_audio_prompt(p['voiceValue'])


def speak_pocket(chunks:Iterable[str]):
    from pocket_tts import TTSModel
    p=profile(); ffplay=shutil.which('ffplay')
    if not ffplay: raise RuntimeError('ADAM VOICE BLOCKED: Pocket TTS is installed but ffplay is missing; system TTS fallback is forbidden')
    model=TTSModel.load_model(language=p['language']); voice=_voice_prompt(model,p)
    filters=[]
    tempo=max(0.5,min(p['tempo'],2.0))
    if abs(tempo-1.0)>0.001: filters.append(f'atempo={tempo:.3f}')
    # Pitch shift while restoring duration. asetrate changes pitch+speed; aresample and
    # reciprocal atempo restore timing without batching the stream.
    semis=max(-12.0,min(p['pitchSemitones'],12.0))
    if abs(semis)>0.01:
        factor=2.0**(semis/12.0)
        filters += [f'asetrate={model.sample_rate}*{factor:.8f}',f'aresample={model.sample_rate}',f'atempo={1.0/factor:.6f}']
    if abs(p['volume']-1.0)>0.001: filters.append(f"volume={max(0.0,min(p['volume'],2.0)):.3f}")
    cmd=[ffplay,'-loglevel','error','-nodisp','-autoexit','-f','f32le','-ar',str(model.sample_rate),'-ac','1']
    if filters: cmd += ['-af',','.join(filters)]
    cmd += ['pipe:0']
    player=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    count=chars=audio_chunks=0
    try:
        assert player.stdin is not None
        for text_chunk in chunks:
            count+=1; chars+=len(text_chunk)
            for pcm in model.generate_audio_stream(voice,text_chunk,copy_state=True):
                player.stdin.write(pcm.detach().cpu().float().numpy().tobytes()); player.stdin.flush(); audio_chunks+=1
        player.stdin.close(); rc=player.wait(timeout=120)
        if rc:
            err=(player.stderr.read().decode('utf-8','replace') if player.stderr else '')[-3000:]
            raise RuntimeError(err or f'ffplay failed ({rc})')
    except Exception:
        try: player.kill()
        except Exception: pass
        raise
    return {'ok':True,'provider':'pocket-stream','voiceProfile':p['id'],'voice':p['voiceValue'],'pitchSemitones':p['pitchSemitones'],'tempo':p['tempo'],'textChunks':count,'audioChunks':audio_chunks,'characters':chars,'batching':False,'prefetchChunks':0}


def speak(chunks:Iterable[str],provider='auto'):
    # Adam's canonical voice is Pocket. Do not launder Android system TTS into success.
    if provider in {'auto','pocket'}: return speak_pocket(chunks)
    if provider=='termux': raise RuntimeError('BLOCKED: system Termux TTS is not Adam and is forbidden for canonical Adam speech')
    raise RuntimeError('unsupported provider')


def main():
    ap=argparse.ArgumentParser(prog='fortress-read',description='Adam: Pocket-only bounded streaming read aloud for Fortress')
    ap.add_argument('--doctor',action='store_true'); ap.add_argument('--profile',action='store_true'); ap.add_argument('--file')
    ap.add_argument('--provider',choices=['auto','pocket','termux'],default='auto'); ap.add_argument('text',nargs='*')
    a=ap.parse_args()
    if a.doctor: out=doctor()
    elif a.profile: out=profile()
    elif a.file: out=speak(chunks_from_file(a.file),a.provider)
    elif a.text: out=speak(chunks_from_text(' '.join(a.text)),a.provider)
    else: out=speak(chunks_from_stdin(),a.provider)
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__': main()
