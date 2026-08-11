#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import hashlib, json, os, re, sys, time, xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
from android_phone_hands_bridge import ui_dump, foreground
from android_window_composer import execute as window_execute
from android_phone_status_tts import execute as tts_execute

STATE=Path(os.path.expanduser('~/.local/state/home-center/voice-nerve.json'))
LOG=Path(os.path.expanduser('~/.local/state/home-center/voice-nerve-events.jsonl'))
POLL=float(os.getenv('HC_VOICE_NERVE_POLL_SECONDS','0.7'))
COOLDOWN=float(os.getenv('HC_VOICE_NERVE_COOLDOWN_SECONDS','2.0'))

COMMANDS=[
    (re.compile(r'\b(?:adam[, ]+)?(?:show|open|focus)(?: me)? (?:the )?(?:terminal|termux)\b',re.I), {'action':'window_swap','app':'termux'}, 'Terminal.'),
    (re.compile(r'\b(?:adam[, ]+)?(?:show|open|focus)(?: me)? (?:the )?(?:browser|chrome)\b',re.I), {'action':'window_swap','app':'chrome'}, 'Browser.'),
    (re.compile(r'\b(?:adam[, ]+)?(?:back to|show|focus)(?: me)? (?:chatgpt|chat gpt|chat)\b',re.I), {'action':'window_focus','app':'chatgpt'}, 'ChatGPT.'),
    (re.compile(r'\b(?:adam[, ]+)?(?:pair|split|compose).*(?:chatgpt|chat gpt).*(?:termux|terminal)\b',re.I), {'action':'window_compose','primary':'chatgpt','secondary':'termux'}, 'ChatGPT and Termux paired.'),
    (re.compile(r'\b(?:adam[, ]+)?(?:swap|switch).*(?:termux|terminal)\b',re.I), {'action':'window_swap','app':'termux'}, 'Terminal.'),
    (re.compile(r'\b(?:adam[, ]+)?(?:swap|switch).*(?:chrome|browser)\b',re.I), {'action':'window_swap','app':'chrome'}, 'Browser.'),
    (re.compile(r'\b(?:adam[, ]+)?voice nerve status\b',re.I), {'action':'voice_status'}, 'Voice nerve active.'),
]


def log(event:dict):
    LOG.parent.mkdir(parents=True,exist_ok=True)
    with LOG.open('a',encoding='utf-8') as f: f.write(json.dumps(event,ensure_ascii=False)+'\n')


def texts(xml:str)->list[str]:
    try: root=ET.fromstring(xml)
    except Exception: return []
    out=[]
    for node in root.iter():
        for key in ('text','content-desc'):
            v=(node.attrib.get(key) or '').strip()
            if v and len(v)<=500: out.append(v)
    return out


def normalize(s:str)->str:
    return re.sub(r'\s+',' ',s).strip()


def choose(lines:list[str]):
    # Newest UI text tends to occur later in the hierarchy. Search backwards.
    for raw in reversed(lines[-120:]):
        text=normalize(raw)
        for pattern,action,spoken in COMMANDS:
            if pattern.search(text): return text,action,spoken
    return None


def load_state():
    try: return json.loads(STATE.read_text())
    except Exception: return {}


def save_state(d):
    STATE.parent.mkdir(parents=True,exist_ok=True)
    STATE.write_text(json.dumps(d,indent=2)+'\n')


def run_once(state:dict):
    fg=foreground()
    # Only inspect while ChatGPT exists in the current window focus context.
    # In native split mode uiautomator can expose both window hierarchies.
    xml=ui_dump()
    found=choose(texts(xml))
    if not found: return state,None
    utterance,action,spoken=found
    digest=hashlib.sha256(utterance.lower().encode()).hexdigest()
    now=time.time()
    if digest==state.get('lastDigest') and now-float(state.get('lastAt',0))<30: return state,None
    if now-float(state.get('lastAt',0))<COOLDOWN: return state,None
    if action.get('action')=='voice_status': result={'ok':True,'status':'active'}
    else: result=window_execute(action)
    tts_execute({'action':'status_say','text':spoken})
    event={'at':now,'utterance':utterance,'action':action,'result':result,'foreground':fg}
    log(event)
    state={'lastDigest':digest,'lastAt':now,'lastUtterance':utterance,'lastAction':action}
    save_state(state)
    return state,event


def loop(once=False):
    state=load_state()
    print('Home Center voice nerve online',flush=True)
    while True:
        try:
            state,event=run_once(state)
            if event: print(json.dumps(event,ensure_ascii=False),flush=True)
            if once: return
        except KeyboardInterrupt: raise
        except Exception as exc:
            log({'at':time.time(),'error':str(exc)})
            if once: raise
        time.sleep(POLL)

if __name__=='__main__': loop('--once' in sys.argv)
