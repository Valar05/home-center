#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, textwrap
from pathlib import Path

HOME=Path.home()
REPO=Path(os.environ.get('FORTRESS_HOME_CENTER','/storage/emulated/0/Documents/GodotProjects/home-center'))
MAX_CHUNK=int(os.environ.get('FORTRESS_READ_ALOUD_CHUNK','900'))
POCKET_CMD=os.environ.get('FORTRESS_POCKET_TTS_CMD','pocket-tts')


def _chunks(text:str):
    text=' '.join(str(text or '').split()).strip()
    if not text: return []
    out=[]
    while text:
        if len(text)<=MAX_CHUNK:
            out.append(text); break
        cut=max(text.rfind('. ',0,MAX_CHUNK),text.rfind('? ',0,MAX_CHUNK),text.rfind('! ',0,MAX_CHUNK),text.rfind(', ',0,MAX_CHUNK))
        if cut<MAX_CHUNK//3: cut=MAX_CHUNK
        else: cut+=1
        out.append(text[:cut].strip()); text=text[cut:].strip()
    return out


def doctor():
    pocket=shutil.which(POCKET_CMD)
    termux=shutil.which('termux-tts-speak')
    return {'ok':bool(pocket or termux),'preferred':'pocket' if pocket else ('termux' if termux else ''),'pocket':pocket or '','termux':termux or '','maxChunk':MAX_CHUNK,'cloudFallback':False}


def _speak_pocket(chunk:str):
    exe=shutil.which(POCKET_CMD)
    if not exe: raise RuntimeError('Pocket TTS executable not available')
    # Default contract: Pocket-compatible CLI reads text from stdin and exits after playback.
    p=subprocess.run([exe],input=chunk,text=True,capture_output=True,timeout=180,check=False)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout or f'Pocket TTS failed ({p.returncode})')[-3000:])


def _speak_termux(chunk:str):
    exe=shutil.which('termux-tts-speak')
    if not exe: raise RuntimeError('termux-tts-speak unavailable')
    p=subprocess.run([exe,chunk],text=True,capture_output=True,timeout=60,check=False)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout or f'Termux TTS failed ({p.returncode})')[-3000:])


def speak(text:str, provider='auto'):
    chunks=_chunks(text)
    if not chunks: raise ValueError('read aloud requires text')
    d=doctor()
    selected=provider
    if selected=='auto': selected=d['preferred']
    if selected not in {'pocket','termux'}: raise RuntimeError('no local TTS provider available')
    for chunk in chunks:
        (_speak_pocket if selected=='pocket' else _speak_termux)(chunk)
    return {'ok':True,'provider':selected,'chunks':len(chunks),'characters':sum(len(x) for x in chunks)}


def read_file(path:str,provider='auto'):
    p=Path(path).expanduser()
    if not p.is_absolute(): p=(Path.cwd()/p).resolve()
    if not p.exists() or not p.is_file(): raise FileNotFoundError(path)
    return speak(p.read_text(encoding='utf-8',errors='replace'),provider)


def main():
    ap=argparse.ArgumentParser(prog='fortress-read',description='Pocket-first offline read aloud for Fortress')
    ap.add_argument('--doctor',action='store_true')
    ap.add_argument('--file')
    ap.add_argument('--provider',choices=['auto','pocket','termux'],default='auto')
    ap.add_argument('text',nargs='*')
    a=ap.parse_args()
    if a.doctor: out=doctor()
    elif a.file: out=read_file(a.file,a.provider)
    else:
        text=' '.join(a.text) if a.text else sys.stdin.read()
        out=speak(text,a.provider)
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__': main()
