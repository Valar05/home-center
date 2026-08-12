#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path
from typing import Iterable, Iterator

MAX_CHUNK=int(os.environ.get('FORTRESS_READ_ALOUD_CHUNK','700'))
VOICE=os.environ.get('FORTRESS_POCKET_TTS_VOICE','alba')
LANGUAGE=os.environ.get('FORTRESS_POCKET_TTS_LANGUAGE','english')


def doctor():
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
      'pocketPython': pocket,
      'ffplay': ffplay or '',
      'termux': termux or '',
      'textChunkChars': MAX_CHUNK,
      'prefetchChunks': 0,
      'batching': False,
      'cloudFallback': False,
    }


def chunk_text_piece(text:str) -> Iterator[str]:
    text=' '.join(str(text or '').split()).strip()
    while text:
        if len(text)<=MAX_CHUNK:
            yield text
            return
        window=text[:MAX_CHUNK+1]
        cuts=[window.rfind(x) for x in ('. ','? ','! ','; ',': ', ', ')]
        cut=max(cuts)
        if cut < MAX_CHUNK//3:
            cut=window.rfind(' ')
        if cut < MAX_CHUNK//3:
            cut=MAX_CHUNK
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
    # Never read the whole document. Accumulate only enough prose to make one
    # bounded synthesis chunk, yield it, then forget it.
    buf=''
    with p.open('r',encoding='utf-8',errors='replace') as f:
        for raw in f:
            line=raw.strip()
            if not line:
                if buf:
                    yield from chunk_text_piece(buf)
                    buf=''
                continue
            candidate=(buf+' '+line).strip()
            if len(candidate)>=MAX_CHUNK:
                yield from chunk_text_piece(candidate)
                buf=''
            else:
                buf=candidate
    if buf:
        yield from chunk_text_piece(buf)


def chunks_from_stdin() -> Iterator[str]:
    buf=''
    for raw in sys.stdin:
        line=raw.strip()
        if not line:
            if buf:
                yield from chunk_text_piece(buf); buf=''
            continue
        candidate=(buf+' '+line).strip()
        if len(candidate)>=MAX_CHUNK:
            yield from chunk_text_piece(candidate); buf=''
        else:
            buf=candidate
    if buf: yield from chunk_text_piece(buf)


def speak_pocket(chunks:Iterable[str]):
    from pocket_tts import TTSModel
    ffplay=shutil.which('ffplay')
    if not ffplay: raise RuntimeError('ffplay unavailable for Pocket streaming playback')
    model=TTSModel.load_model(language=LANGUAGE)
    voice=model.get_state_for_audio_prompt(VOICE)
    player=subprocess.Popen(
        [ffplay,'-loglevel','error','-nodisp','-autoexit','-f','f32le','-ar',str(model.sample_rate),'-ac','1','pipe:0'],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    count=0; chars=0; audio_chunks=0
    try:
        assert player.stdin is not None
        for text_chunk in chunks:
            count+=1; chars+=len(text_chunk)
            # generate_audio_stream yields bounded PCM tensors. Writing each one
            # directly to ffplay provides natural backpressure: no audio batch,
            # no giant WAV, no unbounded prefetch queue.
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
    return {'ok':True,'provider':'pocket-stream','textChunks':count,'audioChunks':audio_chunks,'characters':chars,'batching':False,'prefetchChunks':0}


def speak_termux(chunks:Iterable[str]):
    exe=shutil.which('termux-tts-speak')
    if not exe: raise RuntimeError('termux-tts-speak unavailable')
    count=0; chars=0
    for chunk in chunks:
        count+=1; chars+=len(chunk)
        p=subprocess.run([exe,chunk],text=True,capture_output=True,timeout=90,check=False)
        if p.returncode: raise RuntimeError((p.stderr or p.stdout or f'Termux TTS failed ({p.returncode})')[-3000:])
    return {'ok':True,'provider':'termux','textChunks':count,'characters':chars,'batching':False,'prefetchChunks':0}


def speak(chunks:Iterable[str],provider='auto'):
    d=doctor(); selected=provider
    if selected=='auto': selected=d['preferred']
    if selected=='pocket': selected='pocket-stream'
    if selected=='pocket-stream': return speak_pocket(chunks)
    if selected=='termux': return speak_termux(chunks)
    raise RuntimeError('no local streaming TTS provider available')


def main():
    ap=argparse.ArgumentParser(prog='fortress-read',description='Pocket-first bounded streaming read aloud for Fortress')
    ap.add_argument('--doctor',action='store_true')
    ap.add_argument('--file')
    ap.add_argument('--provider',choices=['auto','pocket','termux'],default='auto')
    ap.add_argument('text',nargs='*')
    a=ap.parse_args()
    if a.doctor:
        out=doctor()
    elif a.file:
        out=speak(chunks_from_file(a.file),a.provider)
    elif a.text:
        out=speak(chunks_from_text(' '.join(a.text)),a.provider)
    else:
        out=speak(chunks_from_stdin(),a.provider)
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__': main()
