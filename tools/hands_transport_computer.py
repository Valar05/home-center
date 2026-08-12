#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

MCP_URL=os.environ.get('HOME_CENTER_MCP_URL','https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp')
TOKEN_CONFIG=Path(os.environ.get('HOME_CENTER_CODEX_CONFIG','~/.config/home-center/codex-hub.json')).expanduser()
SUPPORTED={'system.status','screen.capture','window.list','process.list','window.focus','input.type','input.key','input.mouse','process.start','process.stop','shell.exec','clipboard.get','clipboard.set'}

def decode_job(value):
 padding='='*((4-len(value)%4)%4)
 return json.loads(base64.urlsafe_b64decode((value+padding).encode()).decode())

def parse_json(text,label):
 try:return json.loads(text)
 except Exception as exc:raise RuntimeError(f'{label} did not return JSON: {str(text)[:500]}') from exc

def parse_mcp(text,label):
 data=[line[5:].strip() for line in str(text or '').splitlines() if line.startswith('data:')]
 return parse_json('\n'.join(data) if data else text,label)

def refresh_access_token(refresh,gateway):
 req=urllib.request.Request((gateway or 'https://us-central1-home-center-dclar.cloudfunctions.net')+'/termuxTokenRefresh',data=json.dumps({'refreshToken':refresh}).encode(),headers={'content-type':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=30) as response:body=parse_json(response.read().decode(),'termuxTokenRefresh')
 if not body.get('ok') or not body.get('access_token'):raise RuntimeError('Home Center token refresh failed')
 return body

def bearer_token():
 explicit=os.environ.get('HOME_CENTER_MCP_BEARER_TOKEN','').strip()
 if explicit:return explicit
 if not TOKEN_CONFIG.exists():raise RuntimeError(f'Home Center token config missing: {TOKEN_CONFIG}')
 current=parse_json(TOKEN_CONFIG.read_text(encoding='utf-8'),str(TOKEN_CONFIG))
 if current.get('accessToken') and int(current.get('expiresAtMs') or 0)>int(time.time()*1000)+60000:return current['accessToken']
 refresh=current.get('refreshToken')
 if not refresh:raise RuntimeError('Home Center token config has no usable refresh token')
 body=refresh_access_token(refresh,current.get('gatewayBase'))
 current['accessToken']=body['access_token']; current['refreshToken']=body.get('refresh_token',refresh); current['expiresAtMs']=int(time.time()*1000)+int(body.get('expires_in',3300))*1000; current['refreshedAt']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
 TOKEN_CONFIG.parent.mkdir(parents=True,exist_ok=True); TOKEN_CONFIG.write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8'); os.chmod(TOKEN_CONFIG,0o600)
 return current['accessToken']

class Mcp:
 def __init__(self):self.token=bearer_token();self.counter=0
 def post(self,method,params):
  self.counter+=1; body={'jsonrpc':'2.0','id':f'hands-{self.counter}','method':method,'params':params}
  req=urllib.request.Request(MCP_URL,data=json.dumps(body).encode(),headers={'authorization':'Bearer '+self.token,'content-type':'application/json','accept':'application/json, text/event-stream'},method='POST')
  try:
   with urllib.request.urlopen(req,timeout=45) as response:text=response.read().decode()
  except urllib.error.HTTPError as exc:raise RuntimeError(f'MCP HTTP {exc.code}: {exc.read().decode("utf-8","replace")[:700]}') from exc
  payload=parse_mcp(text,method)
  if payload.get('error'):raise RuntimeError(f"MCP error: {payload['error']}")
  return payload
 def init(self):return self.post('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'hands-router-computer-transport','version':'1'}})
 def drive(self,operation,args):
  payload=self.post('tools/call',{'name':'drive_operation','arguments':{'operation':operation,'args':args}})
  content=((payload.get('result') or {}).get('content') or [])
  text=next((item.get('text','') for item in content if item.get('type')=='text'),'')
  outer=parse_json(text,operation)
  if outer.get('completed') is False:raise RuntimeError(f'{operation} did not complete: {outer}')
  return outer.get('result',outer)

def request_id(job):
 raw=str(job.get('id') or 'job').replace('/','-')
 return ('hr-'+raw)[:150]

def step_args(step):
 op=step['op']; args=dict(step.get('args') or {})
 if op not in SUPPORTED:raise NotImplementedError(op)
 return {'action':op,'arguments':args}

def expected_failure(expected,actual):
 if not expected:return None
 if not isinstance(actual,dict):return 'result_not_object'
 for key,value in expected.items():
  if actual.get(key)!=value:return f'expect_mismatch:{key}'
 return None

def verify_result(job,result):
 steps=job.get('steps') or []
 if len(steps)==1:
  mismatch=expected_failure(steps[0].get('expect') or {},result)
  return mismatch
 rows=result.get('steps') if isinstance(result,dict) else None
 if not isinstance(rows,list):return 'packet_steps_missing'
 by_id={row.get('id'):row for row in rows if isinstance(row,dict)}
 for index,step in enumerate(steps):
  row=by_id.get(f'step-{index+1:02d}')
  if not row:return f'packet_step_missing:{index}'
  actual=row.get('result') if isinstance(row.get('result'),dict) else {'ok':row.get('ok')}
  mismatch=expected_failure(step.get('expect') or {},actual)
  if mismatch:return f'{mismatch}:step-{index+1:02d}'
 return None

def execute(job):
 if job.get('target')!='THECAULDRON':return {'rc':78,'status':'unconfigured','reason':'computer_hands_target_unsupported'}
 steps=job.get('steps') or []
 try:mapped=[step_args(step) for step in steps]
 except NotImplementedError as exc:return {'rc':78,'status':'unsupported','reason':f'computer_hands_op_unsupported:{exc}'}
 mcp=Mcp();mcp.init();rid=request_id(job);worker=os.environ.get('HC_HANDS_COMPUTER_WORKER','windows-hands-01');lane=os.environ.get('HC_HANDS_COMPUTER_LANE','hands-router')
 if len(mapped)==1:
  action=mapped[0]['action']; arguments=mapped[0]['arguments']
 else:
  action='packet.execute'; arguments={'stopOnError':True,'label':f'Hands Router {job.get("id")}', 'steps':[{'id':f'step-{i+1:02d}','action':row['action'],'arguments':row['arguments']} for i,row in enumerate(mapped)]}
 create=mcp.drive('computer_hands.request.create',{'requestId':rid,'workerId':worker,'laneId':lane,'action':action,'arguments':arguments,'approved':True,'highRiskApproved':True})
 ticket=create.get('ticketId') or ('hands-'+rid)
 deadline=time.monotonic()+max(5,min(int(job.get('maxRuntimeSeconds') or 120),300))
 last=None
 while time.monotonic()<deadline:
  last=mcp.drive('computer_hands.request.status',{'ticketId':ticket})
  state=last.get('status')
  if state in {'completed','failed','cancelled'}:
   result=last.get('result') or {}; mismatch=verify_result(job,result)
   ok=state=='completed' and result.get('ok') is not False and mismatch is None
   return {'rc':0 if ok else 65,'status':state,'ticketId':ticket,'result':result,'expectFailure':mismatch,'workerId':worker}
  time.sleep(1.0)
 try:mcp.drive('computer_hands.request.cancel',{'requestId':('cancel-'+rid)[:150],'ticketId':ticket,'reason':'Hands Router transport timeout before fallback'})
 except Exception:pass
 return {'rc':124,'status':'timeout','ticketId':ticket,'lastStatus':last,'cancelRequested':True}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--job-b64',required=True);args=ap.parse_args()
 try:result=execute(decode_job(args.job_b64))
 except Exception as exc:result={'rc':125,'status':'failed','reason':f'{type(exc).__name__}: {exc}'}
 print(json.dumps(result,ensure_ascii=False,sort_keys=True));return int(result.get('rc') or 0)
if __name__=='__main__':raise SystemExit(main())
