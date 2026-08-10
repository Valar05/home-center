#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, re, time, urllib.request
from pathlib import Path

from android_phone_hands_bridge import observe as hands_observe, act as hands_act

LLM_URL=os.getenv('HC_PHONE_LLM_URL','http://127.0.0.1:8790/v1/chat/completions')
MODEL=os.getenv('HC_PHONE_LLM_MODEL','local-phone')
MAX_STEPS=int(os.getenv('HC_PHONE_EXEC_MAX_STEPS','6'))
JOURNAL=Path(os.path.expanduser(os.getenv('HC_PHONE_EXEC_JOURNAL','~/.local/state/home-center/phone-executive.jsonl')))
ALLOWED={'tap','swipe','text','keyevent','home','back','recents','launch','force_stop'}

SYSTEM='''You are the local executive for an Android phone. You are small and conservative.
Return ONE JSON object and nothing else.
Valid examples:
{"done":false,"say":"Going home.","action":{"action":"home"}}
{"done":false,"say":"Going back.","action":{"action":"back"}}
{"done":true,"say":"Termux is foregrounded.","action":null}
Do not copy phrases such as "brief final response" or "brief user-facing status". Those are not valid answers.
Use only Phone Hands actions: tap, swipe, text, keyevent, home, back, recents, launch, force_stop.
Never invent shell commands. Use UI evidence. Prefer stopping over guessing.
Never perform purchases, account-security changes, destructive deletion, permission escalation, messaging other people, or privacy-sensitive capture without explicit human instruction.
'''

def request_json(url, *, method='GET', body=None, timeout=30):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(url,data=data,method=method)
    req.add_header('Content-Type','application/json')
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode())

def observe():
    return hands_observe(True,False)

def act(action):
    if not isinstance(action,dict) or action.get('action') not in ALLOWED:
        raise ValueError('planner requested disallowed action')
    return hands_act(action)

def normalize_intent(intent:str)->str:
    return re.sub(r'[^a-z0-9 ]+',' ',intent.lower()).strip()

def reflex(intent:str):
    t=normalize_intent(intent)
    if t in {'home','go home','go to home','go to the home screen','open home screen','show home screen'}:
        return {'action':'home'}, 'Going home.'
    if t in {'back','go back','press back'}:
        return {'action':'back'}, 'Going back.'
    if t in {'recents','show recents','open recents','recent apps','show recent apps'}:
        return {'action':'recents'}, 'Opening recent apps.'
    return None

def extract_message_text(out):
    try:
        msg=out['choices'][0]['message']
    except (KeyError,IndexError,TypeError) as exc:
        raise RuntimeError('llama-server returned no assistant message: '+json.dumps(out,ensure_ascii=False)[:2000]) from exc
    for key in ('content','reasoning_content'):
        value=msg.get(key)
        if isinstance(value,str) and value.strip():
            return value.strip()
    raise RuntimeError('llama-server returned an empty assistant message: '+json.dumps(out,ensure_ascii=False)[:2000])

def llm(messages):
    payload={'model':MODEL,'messages':messages,'temperature':0,'max_tokens':220,'response_format':{'type':'json_object'}}
    out=request_json(LLM_URL,method='POST',body=payload,timeout=60)
    text=extract_message_text(out)
    try:
        plan=json.loads(text)
    except json.JSONDecodeError as exc:
        m=re.search(r'\{.*\}',text,re.S)
        if m:
            try:
                plan=json.loads(m.group(0))
            except json.JSONDecodeError:
                plan=None
        else:
            plan=None
        if plan is None:
            raise RuntimeError('local model did not return JSON; text='+repr(text[:1000])) from exc
    if not isinstance(plan,dict):
        raise RuntimeError('local model JSON was not an object: '+repr(plan))
    if str(plan.get('say') or '').strip().lower() in {'brief final response','brief user-facing status'}:
        raise RuntimeError('local model copied schema placeholder instead of answering: '+json.dumps(plan,ensure_ascii=False))
    return plan

def journal(event):
    JOURNAL.parent.mkdir(parents=True,exist_ok=True)
    with JOURNAL.open('a') as f: f.write(json.dumps({'ts':time.time(),**event},ensure_ascii=False)+'\n')

def execute(intent):
    fast=reflex(intent)
    if fast:
        action,say=fast
        result=act(action)
        journal({'kind':'reflex','intent':intent,'action':action,'result':result})
        return {'ok':True,'say':say,'steps':1,'done':True,'mode':'reflex'}

    messages=[{'role':'system','content':SYSTEM},{'role':'user','content':'User intent: '+intent}]
    last_say=''
    for step in range(MAX_STEPS):
        obs=observe()
        evidence={'foreground':obs.get('foreground'),'display':obs.get('display'),'ui_xml':obs.get('ui_xml','')[:24000]}
        messages.append({'role':'user','content':'Current phone evidence:\n'+json.dumps(evidence,ensure_ascii=False)})
        plan=llm(messages)
        journal({'kind':'plan','intent':intent,'step':step,'plan':plan,'foreground':obs.get('foreground')})
        last_say=str(plan.get('say') or '').strip()
        if plan.get('done') or plan.get('action') is None:
            return {'ok':True,'say':last_say or 'Done.','steps':step,'done':True,'mode':'planner'}
        result=act(plan['action'])
        messages.append({'role':'assistant','content':json.dumps(plan)})
        messages.append({'role':'user','content':'Action result: '+json.dumps(result,ensure_ascii=False)})
    return {'ok':False,'say':last_say or 'I stopped because I hit my local action limit.','steps':MAX_STEPS,'done':False,'mode':'planner'}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('intent',nargs='+')
    a=p.parse_args(); print(json.dumps(execute(' '.join(a.intent)),ensure_ascii=False))
