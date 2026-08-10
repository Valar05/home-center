#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, subprocess, sys, tempfile, time
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


def android_speech_to_text()->str:
    p=subprocess.run(['termux-speech-to-text'],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or 'termux-speech-to-text failed')
    return p.stdout.strip()


def transcribe_file(wav:str)->str:
    if not STT_CMD:
        raise RuntimeError('file STT requested but HC_PHONE_STT_CMD is empty')
    return run_cmd(STT_CMD,wav=wav)


def vlad_heard_speech(wav:str)->bool:
    """Vlad the Impalementer: local voice-activity gate.

    HC_PHONE_VLAD_CMD must contain {wav}; exit 0 means the captured chunk contains
    speech. When Vlad is not installed, Android SpeechRecognizer is used directly.
    """
    if not VAD_CMD: return True
    return subprocess.run(VAD_CMD.replace('{wav}',wav),shell=True).returncode==0


def record_once(path:str)->None:
    duration=os.getenv('HC_PHONE_LISTEN_SECONDS','6')
    subprocess.run(['termux-microphone-record','-f',path,'-l',duration],check=True)
    subprocess.run(['termux-microphone-record','-q'],check=False)


def listen_once()->str:
    # Bootstrap path: Android's recognizer gives us a working custom assistant
    # immediately. Once offline Sherpa adapters are configured, capture a local
    # audio chunk, let Vlad gate it, and transcribe locally.
    if not STT_CMD and not VAD_CMD:
        return android_speech_to_text()
    fd,path=tempfile.mkstemp(prefix='hc-voice-',suffix='.wav'); os.close(fd)
    try:
        record_once(path)
        if not vlad_heard_speech(path): return ''
        return transcribe_file(path)
    finally:
        try: os.unlink(path)
        except OSError: pass


def normalize_intent(text:str)->str|None:
    t=text.strip()
    if not t: return None
    low=t.lower()
    if WAKE_WORD and WAKE_WORD in low:
        idx=low.find(WAKE_WORD)
        return t[idx+len(WAKE_WORD):].lstrip(' ,:;-') or 'What is on my screen?'
    if os.getenv('HC_PHONE_REQUIRE_WAKE_WORD','1')=='1': return None
    return t


def loop()->None:
    mode='offline-adapter' if STT_CMD else 'Android SpeechRecognizer bootstrap'
    print(f'Phone voice assistant online; wake word={WAKE_WORD!r}; ears={mode}; VAD=Vlad the Impalementer')
    while True:
        try:
            text=listen_once()
            intent=normalize_intent(text)
            if not intent: continue
            result=execute(intent)
            speak(str(result.get('say') or 'Done.'))
            with (STATE/'phone-voice.jsonl').open('a') as f:
                f.write(json.dumps({'ts':time.time(),'heard':text,'intent':intent,'result':result},ensure_ascii=False)+'\n')
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f'voice-loop error: {exc}',file=sys.stderr)
            time.sleep(1)

if __name__=='__main__': loop()
