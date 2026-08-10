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
Use only the listed Phone Hands actions. Never invent shell commands.
Return exactly one JSON object and no prose:
{"done":false,"say":"brief user-facing status","action":{"action":"home"}}
or {"done":true,"say":"brief final response","action":null}.
Use UI evidence. Prefer stopping over guessing. Never perform purchases, account-security changes, destructive deletion, permission escalation, messaging other people, or privacy-sensitive capture without explicit human instruction.
/no_think
'''

def request_json(url, *, method='GET', body=None, timeout=30):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(url,data=data,method=method)
    req.add_header('Content-Type','application/json')
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode())

def observe():
    # Deliberately call the same Phone Hands implementation directly on-device.
    # This avoids weakening the remote bridge's tailnet-only ingress policy.
    return hands_observe(True,False)

def act(action):
    if not isinstance(action,dict) or action.get('action') not in ALLOWED:
        raise ValueError('planner requested disallowed action')
    return hands_act(action)

def llm(messages):
    payload={'model':MODEL,'messages':messages,'temperature':0.1,'max_tokens':220,'response_format':{'type':'json_object'}}
    out=request_json(LLM_URL,method='POST',body=payload,timeout=60)
    text=out['choices'][0]['message']['content'].strip()
    try: return json.loads(text)
    except json.JSONDecodeError:
        m=re.search(r'\{.*\}',text,re.S)
        if not m: raise
        return json.loads(m.group(0))

def journal(event):
    JOURNAL.parent.mkdir(parents=True,exist_ok=True)
    with JOURNAL.open('a') as f: f.write(json.dumps({'ts':time.time(),**event},ensure_ascii=False)+'\n')

def execute(intent):
    messages=[{'role':'system','content':SYSTEM},{'role':'user','content':'User intent: '+intent}]
    last_say=''
    for step in range(MAX_STEPS):
        obs=observe()
        evidence={'foreground':obs.get('foreground'),'display':obs.get('display'),'ui_xml':obs.get('ui_xml','')[:24000]}
        messages.append({'role':'user','content':'Current phone evidence:\n'+json.dumps(evidence,ensure_ascii=False)})
        plan=llm(messages)
        journal({'kind':'plan','intent':intent,'step':step,'plan':plan,'foreground':obs.get('foreground')})
        last_say=str(plan.get('say') or '')
        if plan.get('done') or plan.get('action') is None:
            return {'ok':True,'say':last_say,'steps':step,'done':True}
        result=act(plan['action'])
        messages.append({'role':'assistant','content':json.dumps(plan)})
        messages.append({'role':'user','content':'Action result: '+json.dumps(result,ensure_ascii=False)})
    return {'ok':False,'say':last_say or 'I stopped because I hit my local action limit.','steps':MAX_STEPS,'done':False}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('intent',nargs='+')
    a=p.parse_args(); print(json.dumps(execute(' '.join(a.intent)),ensure_ascii=False))
