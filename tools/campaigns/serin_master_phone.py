#!/usr/bin/env python3
"""Serin mastering controller: Git-pinned Windows worker over existing cauldron SSH."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
import ritsu_asmr_phone as core

WINDOWS_PATH='tools/campaigns/serin_master_windows.ps1'
MASTER='SERIN_ASMR_HR_003_MASTER_V1'
SOURCE='SERIN_ASMR_HR_003'

def q(s):
    return "'"+str(s).replace("'","''")+"'"

def pinned_source():
    commit,_=core.review_source()
    source=subprocess.check_output(['git','-C',str(core.ROOT),'show',commit+':'+WINDOWS_PATH],timeout=40)
    local=(core.ROOT/WINDOWS_PATH).read_bytes()
    if source!=local:
        raise RuntimeError('Mastering source differs from checked-in Git revision')
    return commit,hashlib.sha256(source).hexdigest().upper()

def remote_script(commit,digest,install):
    base=r"""
$ErrorActionPreference='Stop'
$p=Join-Path $env:LOCALAPPDATA 'RitsuASMR\code\__SHA__\serin_master_windows.ps1'
if(!(Test-Path -LiteralPath $p)){
 __INSTALL__
}
if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -cne '__SHA__'){throw 'MASTER_SCRIPT_DIGEST_MISMATCH'}
"""
    fetch=r"""
 $dir=Split-Path -Parent $p
 New-Item -ItemType Directory -Force -Path $dir|Out-Null
 $tmp=$p+'.'+[guid]::NewGuid().ToString('N')+'.incoming'
 try{
  Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Valar05/home-center/__COMMIT__/tools/campaigns/serin_master_windows.ps1' -OutFile $tmp -TimeoutSec 40
  if((Get-FileHash -LiteralPath $tmp -Algorithm SHA256).Hash -cne '__SHA__'){throw 'DOWNLOADED_SCRIPT_DIGEST_MISMATCH'}
  Move-Item -LiteralPath $tmp -Destination $p
 }finally{if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp}}
"""
    nofetch="throw 'PINNED_MASTER_SCRIPT_NOT_INSTALLED: use start first'"
    return base.replace('__INSTALL__',fetch if install else nofetch).replace('__SHA__',digest).replace('__COMMIT__',commit)


def guarded_ps(script,stage):
    """Accept a physically emitted standalone marker despite PTY control formatting.

    Reconcile only a zero-exit result from the exact just-issued request.
    Never accept success inferred from a substring, command echo or old receipt.
    """
    try:
        return core.ps(script,quiet=True,stage=stage)
    except core.RemoteFailure:
        stage_path=core.STATE/'last-remote-stage.txt'
        output_path=core.STATE/'last-remote-transport.txt'
        if not stage_path.exists() or not output_path.exists():
            raise
        detail=stage_path.read_text(encoding='utf-8',errors='replace')
        if not detail.startswith(stage+' ') or not detail.endswith(' exit=0'):
            raise
        raw=output_path.read_text(encoding='utf-8',errors='replace')
        clean=re.sub(r'\x1b\][^\x07]*(?:\x07|\x1b\\)','',raw)
        clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',clean)
        clean=clean.replace('\x00','').replace('\ufeff','').replace('\u200b','')
        # Windows PTY may insert CR, backspace or visual line-control characters.
        lines=[re.sub(r'[\x00-\x1f\x7f]','',line).strip()
               for line in clean.splitlines()]
        if 'RITSU_ASMR_REMOTE_OK=1' not in lines:
            raise
        return raw

def run(verb,commit,digest):
    if verb=='start':
        # Split install and execution into bounded SSH calls; never send media.
        staged=remote_script(commit,digest,True)
        staged+="\n[Console]::WriteLine('RITSU_ASMR_REMOTE_OK=1')\n"
        guarded_ps(staged,stage='serin-master-install')
    script=remote_script(commit,digest,False)
    script+="""
$raw=& $p -Verb __VERB__ 2>&1
if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw ('MASTER_WORKER_EXIT_'+$LASTEXITCODE+' '+(($raw|Out-String).Trim()))}
$line=($raw|Out-String).Trim()
$parsed=$line|ConvertFrom-Json -ErrorAction Stop
$payload=[Text.Encoding]::UTF8.GetBytes(($parsed|ConvertTo-Json -Compress -Depth 12))
$encoded=[Convert]::ToBase64String($payload)
$hash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($payload))).Replace('-','')
[Console]::WriteLine(('JSTART:'+$encoded.Length))
for($i=0;$i -lt $encoded.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$encoded.Substring($i,[Math]::Min(16,$encoded.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$hash.Substring($i,16)))}
[Console]::WriteLine('RITSU_ASMR_REMOTE_OK=1')
""".replace('__VERB__',verb)
    return core.extract_result(guarded_ps(script,stage='serin-master-'+verb))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('verb',choices=['start','status','receipt'])
    args=p.parse_args()
    try:
        commit,digest=pinned_source()
        print('CAMPAIGN=SERIN_MASTER_V1\nSOURCE_EPISODE='+SOURCE+
              '\nMASTER_EPISODE='+MASTER+'\nSOURCE_COMMIT='+commit+
              '\nMASTER_SCRIPT_SHA256='+digest,flush=True)
        result=run('status' if args.verb=='receipt' else args.verb,commit,digest)
        print('WINDOWS_RESULT='+json.dumps(result,sort_keys=True,separators=(',',':')))
        print('REMOTE_OPERATION_CONFIRMED=YES')
        if args.verb=='receipt' and result.get('phase')!='rendered_not_delivered':
            raise RuntimeError('Master not yet complete')
        if args.verb=='receipt':
            print('NEXT=python3 tools/campaigns/ritsu_asmr_phone.py drop --episode '+MASTER)
        elif args.verb=='start':
            print('NEXT=python3 tools/campaigns/serin_master_phone.py status')
        return 0
    except Exception as e:
        print('STATUS=BLOCKED\nERROR='+type(e).__name__+': '+str(e)[:600],file=sys.stderr)
        print('Do not re-dispatch blindly; reconcile existing master task and receipt first.',file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
