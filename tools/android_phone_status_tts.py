#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import os, shutil, subprocess

MAX_CHARS=int(os.getenv('HC_PHONE_STATUS_TTS_MAX_CHARS','280'))
TIMEOUT=float(os.getenv('HC_PHONE_STATUS_TTS_TIMEOUT','8'))


def _clean(text:str)->str:
    value=' '.join(str(text or '').split()).strip()
    if not value:
        raise ValueError('status_say requires text')
    return value[:MAX_CHARS]


def doctor()->dict:
    exe=shutil.which('termux-tts-speak')
    return {
      'ok': bool(exe),
      'provider': 'termux-tts-speak' if exe else '',
      'executable': exe or '',
      'maxChars': MAX_CHARS,
      'cloudFallback': False,
    }


def say(text:str, rate:float|None=None, pitch:float|None=None)->dict:
    value=_clean(text)
    exe=shutil.which('termux-tts-speak')
    if not exe:
        raise RuntimeError('termux-tts-speak not installed; install Termux:API package/app for fast local status TTS')
    cmd=[exe]
    if rate is not None:
        cmd += ['-r', str(max(0.5,min(float(rate),2.0)))]
    if pitch is not None:
        cmd += ['-p', str(max(0.5,min(float(pitch),2.0)))]
    cmd.append(value)
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=TIMEOUT,check=False)
    if p.returncode != 0:
        raise RuntimeError((p.stdout or f'termux-tts-speak failed ({p.returncode})')[-2000:])
    return {'ok':True,'provider':'termux-tts-speak','text':value,'rate':rate,'pitch':pitch}


def execute(action:dict)->dict:
    kind=str(action.get('action') or '')
    if kind=='status_tts_doctor': return doctor()
    if kind=='status_say': return say(str(action.get('text') or ''),action.get('rate'),action.get('pitch'))
    raise ValueError(f'unsupported status TTS action: {kind}')
