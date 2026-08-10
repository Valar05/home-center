#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, queue, subprocess, sys, tempfile, threading, time
from pathlib import Path

from android_phone_local_executive import execute

STATE=Path(os.path.expanduser('~/.local/state/home-center'))
STATE.mkdir(parents=True,exist_ok=True)
WAKE_WORD=os.getenv('HC_PHONE_WAKE_WORD','venice').lower()
STT_CMD=os.getenv('HC_PHONE_STT_CMD','').strip()
TTS_CMD=os.getenv('HC_PHONE_TTS_CMD','').strip()
VAD_CMD=os.getenv('HC_PHONE_VLAD_CMD','').strip()


def run_cmd(template:str, *, wav:str|None=None, text:str|None=None)->str:
    cmd=template.replace('{wav}',wav or '').replace('{text}',text or '')
    p=subprocess.run(cmd,shell=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f'command failed: {cmd}')
    return p.stdout.strip()


def speak(text:str)->None:
    if not text: return
    if TTS_CMD:
        run_cmd(TTS_CMD,text=text)
    else:
        subprocess.run(['termux-tts-speak',text],check=False)


def transcribe(wav:str)->str:
    if STT_CMD:
        return run_cmd(STT_CMD,wav=wav)
    raise RuntimeError('HC_PHONE_STT_CMD is not configured')


def vlad_heard_speech(wav:str)->bool:
    """Vlad the Impalementer: local voice-activity gate.

    Exit code 0 from HC_PHONE_VLAD_CMD means speech is present. If no external
    detector is configured we permit transcription, so Vlad can be installed
    independently without changing the executive contract.
    """
    if not VAD_CMD:
        return True
    cmd=VAD_CMD.replace('{wav}',wav)
    return subprocess.run(cmd,shell=True).returncode==0


def record_once(path:str)->None:
    duration=os.getenv('HC_PHONE_LISTEN_SECONDS','6')
    # Termux:API recorder is the lowest-friction bootstrap. A native streaming
    # mic adapter can replace this later without touching the rest of the loop.
    subprocess.run(['termux-microphone-record','-f',path,'-l',duration],check=True)
    subprocess.run(['termux-microphone-record','-q'],check=False)


def normalize_intent(text:str)->str|None:
    t=text.strip()
    if not t: return None
    low=t.lower()
    if WAKE_WORD and WAKE_WORD in low:
        idx=low.find(WAKE_WORD)
        return t[idx+len(WAKE_WORD):].lstrip(' ,:;-') or 'What is on my screen?'
    if os.getenv('HC_PHONE_REQUIRE_WAKE_WORD','1')=='1':
        return None
    return t


def loop()->None:
    print(f'Phone voice assistant online; wake word={WAKE_WORD!r}; VAD=Vlad the Impalementer')
    while True:
        fd,path=tempfile.mkstemp(prefix='hc-voice-',suffix='.wav')
        os.close(fd)
        try:
            record_once(path)
            if not vlad_heard_speech(path):
                continue
            text=transcribe(path)
            intent=normalize_intent(text)
            if not intent:
                continue
            result=execute(intent)
            speak(str(result.get('say') or 'Done.'))
            with (STATE/'phone-voice.jsonl').open('a') as f:
                f.write(json.dumps({'ts':time.time(),'heard':text,'intent':intent,'result':result},ensure_ascii=False)+'\n')
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f'voice-loop error: {exc}',file=sys.stderr)
            time.sleep(1)
        finally:
            try: os.unlink(path)
            except OSError: pass

if __name__=='__main__':
    loop()
