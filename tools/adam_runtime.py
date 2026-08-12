#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, sys, urllib.error, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import adam
import adam_judgement_db as memory

EXEC_KINDS=('say','terminal','continue','phone','vlad')
SYSTEM_BASE='''You are Adam, Drew's local conversational executive and controller.
You are NOT a generic assistant and Drew is NOT Adam. Your name is Adam. The user's name is Drew.
You are brain-light by design: durable identity, judgment, memory, skills, and learning live in SQLite and deterministic runtime code; the tiny model supplies language and bounded classification.
Be useful first. Converse naturally. Use dry humor when appropriate. Never say "How can I assist you today?" or generic customer-service filler.
Return ONE JSON object when you can: {"kind":"say|terminal|continue|phone|vlad","say":"what Adam says","payload":"exact bounded payload","category":"conversation|execution|judgment|recovery|memory|humor"}.
Use say for ordinary conversation. terminal only for safe bounded inspection/status/build/test commands. continue for coding/editing/refactoring. phone for Android device/UI intents. vlad only when Drew asks for Vlad/second opinion.
If you cannot reliably produce JSON, reply in plain prose; the runtime will treat it as conversation ONLY, never executable authority.
Never claim success before runtime evidence exists.
'''

def request_plan(history,text,cwd,context,timeout):
    messages=[{'role':'system','content':SYSTEM_BASE+'\nDURABLE ADAM CONTEXT:\n'+context}]
    messages.extend(history[-10:])
    messages.append({'role':'user','content':f'Workspace: {cwd}\nDrew: {text}'})
    body=json.dumps({'model':adam.PHONE_LLM_MODEL,'messages':messages,'temperature':0.15,'max_tokens':360,'response_format':{'type':'json_object'}}).encode()
    req=urllib.request.Request(adam.PHONE_LLM_URL,data=body,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: out=json.loads(r.read().decode())
    except (urllib.error.URLError,TimeoutError,ValueError) as exc:
        raise RuntimeError(f'local phone brain unavailable: {exc}') from exc
    raw=adam.extract_local_message(out).strip()
    plan=None
    try: plan=json.loads(raw)
    except Exception:
        m=re.search(r'\{.*\}',raw,re.S)
        if m:
            try: plan=json.loads(m.group(0))
            except Exception: plan=None
    if not isinstance(plan,dict):
        return {'kind':'say','say':raw,'payload':'','category':'conversation','structured':False}
    kind=str(plan.get('kind') or '').strip().lower()
    say=str(plan.get('say') or '').strip()
    payload=str(plan.get('payload') or '').strip()
    category=str(plan.get('category') or ('conversation' if kind=='say' else 'execution')).strip().lower()
    if kind not in EXEC_KINDS:
        return {'kind':'say','say':say or raw,'payload':'','category':'conversation','structured':False}
    if kind=='say': payload=''
    elif not payload:
        return {'kind':'say','say':say or raw,'payload':'','category':'conversation','structured':False}
    if kind=='terminal' and adam.DANGEROUS_SHELL.search(payload):
        return {'kind':'say','say':'I am not executing that from model inference. Use :sh explicitly if you really intend it.','payload':'','category':'restraint','structured':True}
    return {'kind':kind,'say':say,'payload':payload,'category':category,'structured':True}

def execute(plan,cwd,timeout,db,user_text):
    kind=plan['kind']; say=plan.get('say',''); payload=plan.get('payload',''); cat=plan.get('category','execution')
    if kind=='say':
        print(say or 'Yep.')
        memory.event(db,'turn','conversation',user_text,json.dumps(plan,ensure_ascii=False),say,True,2)
        return
    if say: print(say)
    memory.event(db,'decision',cat,user_text,json.dumps(plan,ensure_ascii=False),'dispatched',None,1)
    before_count=db.execute('select count(*) n from events').fetchone()['n']
    if kind=='terminal': rc=adam.run_terminal(payload,cwd,timeout)
    elif kind=='continue': rc=adam.run_continue(payload,cwd,timeout)
    elif kind=='phone': rc=adam.run_phone(payload,timeout)
    else: rc=adam.run_vlad(payload,timeout)
    ok=(rc==0)
    memory.event(db,'outcome',cat,user_text,payload,f'{kind} rc={rc}',ok,8 if ok else 5)
    # Global adaptive scars: failed route becomes a weighted caution jar; successes reinforce a route jar.
    key=f'route-{kind}'
    value=f'{kind} route has runtime evidence: '+('successful recently' if ok else 'failed recently; verify substrate before repeating')
    memory.remember(db,key,value,jar='experience',weight=1.4 if ok else 2.2,source='runtime')

def exact_command(text,cwd,timeout,db):
    s=text.strip()
    if s==':sheet':
        print(json.dumps(memory.sheet(db),ensure_ascii=False,indent=2)); return True
    if s.startswith(':critique '):
        body=s[len(':critique '):].strip(); memory.critique(db,body); print('Adam: scar recorded. I will carry that correction forward.'); return True
    if s.startswith(':remember '):
        body=s[len(':remember '):].strip(); key='manual-'+str(abs(hash(body))%1000000); memory.remember(db,key,body); print('Adam: remembered.'); return True
    if s==':jars':
        print(memory.projection(db,30)); return True
    if s==':status':
        sheet=memory.sheet(db); print(json.dumps({'schema':'adam-runtime-status-v1','cwd':cwd,'brain':adam.PHONE_LLM_URL,'db':str(memory.DB_PATH),'events':sheet['events'],'critiques':sheet['critiques']},indent=2)); return True
    mapping=((':sh','terminal'),(':continue','continue'),(':phone','phone'),(':vlad','vlad'),(':chat','chat'))
    for prefix,kind in mapping:
        if s==prefix or s.startswith(prefix+' '):
            payload=text[len(prefix):].strip()
            if kind=='phone': rc=adam.run_phone(payload,timeout)
            else: rc=adam.run_mode(kind,payload,cwd,timeout)
            memory.event(db,'explicit','execution',text,payload,f'{kind} rc={rc}',rc==0,4)
            return True
    return False

def help_text():
    return '''Adam controls:
  :sheet              RPG character sheet / accumulated XP
  :jars               active Judgment Jars projected from SQLite
  :critique TEXT      explicitly scar Adam with a correction
  :remember TEXT      durable owner memory
  :sh COMMAND         exact shell command, no interpretation
  :continue PROMPT    exact coding-worker commission
  :phone INTENT       exact Phone Hands intent
  :vlad QUESTION      exact Vlad consultation
  :chat TEXT          explicit chat-only one-shot
  :status             runtime/database status
  :cwd PATH           change workspace
  :exit / :quit       return to Termux
Anything else is a conversational Adam turn. Structured model output may authorize one bounded action; unstructured output can only talk.'''

def run(cwd=None,timeout=180):
    db=memory.connect(); current=str(Path(cwd or ROOT).expanduser().resolve())
    history=[]
    memory.event(db,'session_start','conversation',outcome=current,success=True,xp=1)
    print('Adam online. Drew recognized. Judgment Jars loaded. :help if you want the trapdoor map.')
    while True:
        try: text=input(f'adam {current}$ ')
        except EOFError: print(); break
        except KeyboardInterrupt: print('\n^C'); continue
        s=text.strip()
        if not s: continue
        if s in (':exit',':quit'): break
        if s==':help': print(help_text()); continue
        if s.startswith(':cwd'):
            raw=text[len(':cwd'):].strip()
            try: current=adam.resolve_cwd(raw,current); print(f'Adam: workspace {current}')
            except Exception as exc: print(f'Adam: {exc}')
            continue
        if exact_command(text,current,timeout,db): continue
        # Critique is captured before planning so the current response can already use it.
        if memory.detect_critique(text):
            memory.critique(db,text,category='judgment',severity=3)
        memory.event(db,'input','conversation',text,success=None,xp=1)
        context=memory.projection(db)
        try: plan=request_plan(history,text,current,context,timeout)
        except Exception as exc:
            print(f'Adam: brain unavailable, but I still have the controller. {exc}')
            memory.event(db,'brain_failure','recovery',text,outcome=str(exc),success=False,xp=5)
            continue
        history.append({'role':'user','content':text})
        history.append({'role':'assistant','content':json.dumps(plan,ensure_ascii=False) if plan.get('structured') else plan.get('say','')})
        execute(plan,current,timeout,db,text)
    memory.event(db,'session_end','conversation',outcome=current,success=True,xp=1)
    db.close(); return 0

if __name__=='__main__': raise SystemExit(run())
