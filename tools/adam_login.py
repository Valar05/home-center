#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.parse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hands_router as hands

DEFAULT_USERNAME='input[autocomplete="username"],input[type="email"],input[name*="email" i],input[name*="user" i]'
DEFAULT_PASSWORD='input[type="password"],input[autocomplete="current-password"]'
DEFAULT_SUBMIT='button[type="submit"],input[type="submit"]'

def require_login_url(raw):
 url=urllib.parse.urlparse(str(raw or '').strip())
 if url.scheme not in {'http','https'} or not url.netloc: raise ValueError('login URL must be http/https')
 host=(url.hostname or '').lower()
 if url.scheme!='https' and host not in {'localhost','127.0.0.1','::1'}: raise ValueError('credential login requires https except localhost')
 return url

def compile_login(url,username_selector=DEFAULT_USERNAME,password_selector=DEFAULT_PASSWORD,submit_selector=DEFAULT_SUBMIT,ttl_seconds=180,max_attempts=1):
 parsed=require_login_url(url)
 ttl=max(30,min(int(ttl_seconds),600)); attempts=max(1,min(int(max_attempts),2)); now=int(time.time()*1000)
 lease={'schema':'adam-login-lease-v1','permission':'login_with_autofill','origin':f'{parsed.scheme}://{parsed.netloc}','explicitUserAuthorization':True,'issuedAtMs':now,'expiresAtMs':now+ttl*1000,'maxAttempts':attempts}
 payload={'url':parsed.geturl(),'usernameSelector':username_selector,'passwordSelector':password_selector,'submitSelector':submit_selector,'lease':lease}
 blob=base64.b64encode(json.dumps(payload,separators=(',',':')).encode()).decode()
 command=(
  "$p=Join-Path $env:LOCALAPPDATA 'HomeCenter\\BrowserNerve\\adam-autofill-login.ps1'; "
  "if(-not (Test-Path -LiteralPath $p)){throw 'Adam Browser Nerve autofill executor is not installed'}; "
  f"& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $p -InputJsonBase64 '{blob}'"
 )
 steps=[{'op':'shell.exec','args':{'command':command},'expect':{'ok':True}}]
 job=hands.enqueue('drew','THECAULDRON',steps,ttl=ttl,max_runtime=min(ttl,120))
 return {'schema':'adam-login-plan-v1','ok':True,'origin':lease['origin'],'leaseExpiresAtMs':lease['expiresAtMs'],'job':job,'response':f"Login authorized for {lease['origin']} and queued. Credential values will not be returned."}

def main():
 ap=argparse.ArgumentParser(prog='adam-login')
 ap.add_argument('url'); ap.add_argument('--username-selector',default=DEFAULT_USERNAME); ap.add_argument('--password-selector',default=DEFAULT_PASSWORD); ap.add_argument('--submit-selector',default=DEFAULT_SUBMIT); ap.add_argument('--ttl',type=int,default=180); ap.add_argument('--max-attempts',type=int,default=1)
 args=ap.parse_args()
 try:result=compile_login(args.url,args.username_selector,args.password_selector,args.submit_selector,args.ttl,args.max_attempts)
 except Exception as exc:result={'schema':'adam-login-plan-v1','ok':False,'error':f'{type(exc).__name__}: {exc}','response':str(exc)}
 print(json.dumps(result,ensure_ascii=False,sort_keys=True)); return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
