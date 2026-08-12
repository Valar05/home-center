#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, time
from pathlib import Path
from android_operator_overlay import update as overlay_update
from android_phone_status_tts import execute as tts_execute

STATE = Path.home() / '.local/state/home-center/venice-reactor'
EVENTS = STATE / 'audio-events.jsonl'
MAX_EVENT_BYTES = 256 * 1024
MAX_EVENT_ROWS = 1200
MAX_EVENT_AGE_SECONDS = 6 * 60 * 60


def _f(value, default=0.0):
    try: return float(value)
    except Exception: return default


def classify(obs: dict) -> dict:
    rms=_f(obs.get('rms')); peak=_f(obs.get('peak')); zcr=_f(obs.get('zcr'))
    low=_f(obs.get('low')); mid=_f(obs.get('mid')); high=_f(obs.get('high'))
    transient=_f(obs.get('transient')); pulse=_f(obs.get('pulse'))
    silence=bool(obs.get('silence', rms < 0.015))
    total=max(low+mid+high, 1e-9); bass=low/total; bright=high/total; crest=peak/max(rms,1e-6)
    tags=[]
    if silence: tags.append('silence')
    else:
        if rms>0.32 or peak>0.88: tags.append('loud')
        elif rms<0.055: tags.append('quiet')
        if transient>0.72 or crest>7.0: tags.append('impact')
        if bass>0.58: tags.append('bass-heavy')
        if bright>0.52 or zcr>0.25: tags.append('bright/noisy')
        if 0.16<zcr<0.24 and mid/total>0.38: tags.append('voice-like')
        if pulse>0.58: tags.append('rhythmic')
    if not tags: tags.append('steady')
    return {'tags':tags,'rms':round(rms,4),'peak':round(peak,4),'zcr':round(zcr,4),
            'low':round(low,4),'mid':round(mid,4),'high':round(high,4),
            'transient':round(transient,4),'pulse':round(pulse,4),'crest':round(crest,3)}


def react(obs: dict) -> str:
    s=set(classify(obs)['tags'])
    if 'silence' in s: return '...and suddenly, everybody remembers silence exists.'
    if {'impact','loud'} <= s: return 'Oh. That had opinions.'
    if {'bass-heavy','rhythmic'} <= s: return 'The floor has entered the conversation.'
    if {'bright/noisy','loud'} <= s: return 'Subtle. Like a cutlery drawer falling down stairs.'
    if {'voice-like','quiet'} <= s: return 'Someone is being suspiciously intimate with the soundtrack.'
    if 'rhythmic' in s: return 'There it is. The scene found a pulse.'
    if 'impact' in s: return 'That sound was definitely carrying paperwork.'
    if 'quiet' in s: return 'Mm. The audio is leaning in.'
    return 'I am listening to the shape of it.'


def _prune(now=None):
    if not EVENTS.exists(): return
    now=time.time() if now is None else now
    rows=[]
    for raw in EVENTS.read_text(encoding='utf-8',errors='replace').splitlines()[-MAX_EVENT_ROWS:]:
        try:
            row=json.loads(raw)
            if now-float(row.get('ts',now)) <= MAX_EVENT_AGE_SECONDS: rows.append(row)
        except Exception: pass
    encoded=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows)
    while len(encoded.encode('utf-8')) > MAX_EVENT_BYTES and rows:
        rows=rows[len(rows)//8 or 1:]
        encoded=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows)
    EVENTS.write_text(encoded,encoding='utf-8')


def observe(features: dict, source='phone-playback', speak=True):
    STATE.mkdir(parents=True,exist_ok=True)
    summary=classify(features); line=react(features); now=time.time()
    event={'ts':now,'source':source,'audio':summary,'reaction':line}
    with EVENTS.open('a',encoding='utf-8') as f: f.write(json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n')
    if EVENTS.stat().st_size > MAX_EVENT_BYTES: _prune(now)
    overlay_update('VENICE LISTENS\n'+', '.join(summary['tags'])+'\n\nVENICE\n'+line,'Venice')
    if speak and line: tts_execute({'action':'status_say','text':line})
    return {'ok':True,**event,'eventPath':str(EVENTS)}


def mine(limit=200):
    _prune()
    if not EVENTS.exists(): return {'ok':True,'events':0,'tags':[]}
    counts={}; rows=[]
    for raw in EVENTS.read_text(encoding='utf-8',errors='replace').splitlines()[-max(1,min(limit,MAX_EVENT_ROWS)):]:
        try: rows.append(json.loads(raw))
        except Exception: pass
    for row in rows:
        for tag in row.get('audio',{}).get('tags',[]): counts[tag]=counts.get(tag,0)+1
    return {'ok':True,'events':len(rows),'tags':sorted(counts.items(),key=lambda x:(-x[1],x[0]))}


def status():
    _prune(); size=EVENTS.stat().st_size if EVENTS.exists() else 0
    return {'ok':True,'eventPath':str(EVENTS),'bytes':size,'maxBytes':MAX_EVENT_BYTES,
            'maxRows':MAX_EVENT_ROWS,'maxAgeSeconds':MAX_EVENT_AGE_SECONDS,'rawAudioStored':False,'speechRecognition':False}


def execute(payload):
    action=str(payload.get('action') or 'observe')
    if action in {'observe','ingest'}:
        return observe(payload.get('features') or payload.get('audio') or {},payload.get('source','phone-playback'),bool(payload.get('speak',True)))
    if action=='mine': return mine(int(payload.get('limit',200)))
    if action=='status': return status()
    raise ValueError('unsupported Venice reactor action: '+action)

if __name__=='__main__':
    import sys
    print(json.dumps(execute(json.loads(sys.stdin.read() or '{}')),ensure_ascii=False))
