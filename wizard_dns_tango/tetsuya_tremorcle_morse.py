#!/usr/bin/env python3
"""Tetsuya Tremorcle Morse: haptics encode truthful work state, never fake progress."""
from __future__ import annotations
import json, os, subprocess, time
from pathlib import Path

STATE=Path(os.environ.get('WDT_STATE', Path.home()/'.local/state/wizard-dns-tango'))
EVENTS=STATE/'events.jsonl'; OUT=STATE/'tremorcles.jsonl'; RELEASE=STATE/'TREMORCLES_RELEASED'
STATE.mkdir(parents=True, exist_ok=True)
MORSE={c:v for c,v in {
'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....','I':'..','J':'.---','K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.','Q':'--.-','R':'.-.','S':'...','T':'-','U':'..-','V':'...-','W':'.--','X':'-..-','Y':'-.--','Z':'--..'
}.items()}
WORDS={'dispatch':'GO','working':'WORK','receipt':'PROOF','canary_pass':'GREEN','canary_fail':'NO','blocked':'HELP','delivered':'DONE','mockray':'FIX'}

def vibrate(ms:int):
    try: subprocess.run(['termux-vibrate','-d',str(ms),'-f'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2)
    except Exception: pass

def tremor_word(word:str):
    for li,ch in enumerate(word.upper()):
        code=MORSE.get(ch,'')
        for i,s in enumerate(code):
            vibrate(55 if s=='.' else 170)
            if i+1<len(code): time.sleep(.07)
        if li+1<len(word): time.sleep(.18)

def emit(kind:str,evidence:dict):
    word=WORDS.get(kind,'FIX')
    # No celebratory DONE/GREEN without explicit evidence state.
    if kind in {'delivered','canary_pass'} and not evidence.get('verified',False):
        kind='mockray'; word='FIX'
    tremor_word(word)
    rec={'at':time.time(),'kind':kind,'morse_word':word,'evidence':evidence}
    with OUT.open('a') as f: f.write(json.dumps(rec,sort_keys=True)+'\n')

def tail():
    EVENTS.touch(exist_ok=True)
    with EVENTS.open() as f:
        f.seek(0,2)
        while not RELEASE.exists():
            line=f.readline()
            if not line: time.sleep(.25); continue
            try: ev=json.loads(line)
            except Exception: continue
            kind=str(ev.get('kind','working'))
            if kind in WORDS: emit(kind,ev)

if __name__=='__main__': tail()
