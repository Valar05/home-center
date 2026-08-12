#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hands_router as hands

OLLAMA=os.environ.get('OLLAMA_HOST','http://127.0.0.1:11434').rstrip('/')
MODEL=os.environ.get('HC_ADAM_CONTEXT_MODEL',os.environ.get('HC_ADAM_MODEL','qwen2.5-coder:1.5b'))
MAX_FILES=int(os.environ.get('HC_ADAM_CONTEXT_FILES','18'))
MAX_FILE_CHARS=int(os.environ.get('HC_ADAM_CONTEXT_FILE_CHARS','5000'))
MAX_CONTEXT_CHARS=int(os.environ.get('HC_ADAM_CONTEXT_CHARS','24000'))
DEFAULT_ROOTS=(
 '~/.local/state/home-center/chat-context',
 '~/.local/state/home-center/venice-reactor',
 '~/storage/shared/Documents/HomeCenter',
 '~/storage/shared/Documents/Adam',
)
TEXT_SUFFIXES={'.txt','.md','.json','.jsonl','.yaml','.yml'}

def run(command,timeout=20):
 p=subprocess.run(command,text=True,capture_output=True,timeout=timeout)
 return p.returncode,p.stdout,p.stderr

def context_roots():
 raw=os.environ.get('HC_ADAM_CONTEXT_ROOTS','')
 values=[x for x in raw.split(os.pathsep) if x.strip()] if raw else list(DEFAULT_ROOTS)
 return [Path(x).expanduser() for x in values]

def collect_context():
 candidates=[]
 for root in context_roots():
  if not root.exists():continue
  if root.is_file():candidates.append(root);continue
  try:
   for path in root.rglob('*'):
    if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
     try:candidates.append(path)
     except OSError:pass
  except OSError:pass
 candidates=sorted(candidates,key=lambda p:p.stat().st_mtime if p.exists() else 0,reverse=True)[:MAX_FILES]
 chunks=[]
 for path in candidates:
  try:text=path.read_text(encoding='utf-8',errors='replace')[-MAX_FILE_CHARS:]
  except OSError:continue
  chunks.append(f'FILE {path}\n{text}')
 joined='\n\n'.join(chunks)
 return joined[-MAX_CONTEXT_CHARS:], [str(p) for p in candidates]

def installed_packages():
 rish=os.environ.get('HC_RISH','rish')
 try:rc,out,_=run([rish,'-c','pm list packages'],timeout=20)
 except Exception:return []
 if rc:return []
 return sorted(line.split(':',1)[1].strip() for line in out.splitlines() if line.startswith('package:'))

def ask_model(prompt,timeout=90):
 payload=json.dumps({'model':MODEL,'stream':False,'options':{'temperature':0.15,'num_predict':500},'prompt':prompt}).encode()
 req=urllib.request.Request(OLLAMA+'/api/generate',data=payload,headers={'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=timeout) as response:return str(json.loads(response.read().decode()).get('response') or '').strip()
 except (urllib.error.URLError,TimeoutError,ValueError) as exc:raise RuntimeError(f'context_model_unavailable: {exc}') from exc

def parse_choice(text):
 clean=text.strip()
 if clean.startswith('```'):
  clean=clean.split('\n',1)[1] if '\n' in clean else clean
  clean=clean.rsplit('```',1)[0].strip()
 data=json.loads(clean)
 if not isinstance(data,dict):raise ValueError('planner output must be object')
 title=str(data.get('title') or '').strip(); service=str(data.get('service') or '').strip(); reason=str(data.get('reason') or '').strip(); uri=str(data.get('uri') or '').strip(); package=str(data.get('package') or '').strip()
 if not title or not service or not reason or not uri:raise ValueError('planner omitted required field')
 parsed=urllib.parse.urlparse(uri)
 if parsed.scheme not in {'http','https'} or not parsed.netloc:raise ValueError('planner uri must be http/https')
 return {'title':title[:300],'service':service[:120],'reason':reason[:600],'uri':uri[:4096],'package':package[:240]}

def plan_watch(request):
 context,files=collect_context(); packages=installed_packages(); package_text='\n'.join(packages[-600:])
 prompt=f'''You are Adam's media chooser. The user said: {request!r}.
Choose exactly ONE thing that fits the supplied recent personal/project context and can be opened on this Android phone. Prefer a service whose package is installed. YouTube is acceptable. Do not invent a specific streaming title availability unless the context supports it; when uncertain, use a deterministic search URL for the chosen service instead of pretending direct availability.

Return ONLY JSON:
{{"title":"...","service":"...","reason":"...","uri":"https://...","package":"installed.package.or.empty"}}

INSTALLED PACKAGES:
{package_text}

RECENT DURABLE CONTEXT:
{context}
'''
 choice=parse_choice(ask_model(prompt))
 if choice['package'] and choice['package'] not in packages:
  choice['package']=''
 steps=[{'op':'phone.open_uri','args':{'uri':choice['uri'],**({'package':choice['package']} if choice['package'] else {})}}]
 job=hands.enqueue('adam','primary-phone',steps,max_runtime=45)
 return {'schema':'adam-context-plan-v1','ok':True,'intent':'find_something_to_watch','choice':choice,'contextFiles':files,'installedPackageCount':len(packages),'job':job,'response':f"{choice['title']} — {choice['service']}. {choice['reason']} Queued on phone."}

def main():
 ap=argparse.ArgumentParser(prog='adam-contextual'); ap.add_argument('request',nargs='+'); args=ap.parse_args(); request=' '.join(args.request).strip()
 try:result=plan_watch(request)
 except Exception as exc:
  result={'schema':'adam-context-plan-v1','ok':False,'error':f'{type(exc).__name__}: {exc}','response':f'Could not produce a verified media choice: {exc}'}
 print(json.dumps(result,ensure_ascii=False,sort_keys=True))
 return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
