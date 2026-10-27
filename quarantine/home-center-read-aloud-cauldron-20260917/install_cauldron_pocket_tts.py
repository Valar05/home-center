#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,json,time
from pathlib import Path
from home_center_mcp_client import HomeCenterMcp
from pocket_tts_cauldron_backend import _run_action,_run_shell,cauldron_status
ROOT=Path(__file__).resolve().parents[1];PACKAGE=ROOT/'workers'/'cauldron_pocket_tts_worker';STAGE=r'C:\Users\Public\HomeCenterPocketTtsBootstrapV2'
def shell(client,kind,payload,command,timeout=180):return _run_shell(client,f"ptts-{kind}-"+hashlib.sha256(payload).hexdigest()[:24],command,timeout)
def main()->int:
 client=HomeCenterMcp(timeout=60);status=cauldron_status(client);shell(client,'mkdir',STAGE.encode(),f"New-Item -ItemType Directory -Force -Path '{STAGE}'|Out-Null;'STAGE_READY'")
 for filename in ('bootstrap.ps1','render_section.py','pocket_tts_render_v2.py','requirements.txt'):
  data=(PACKAGE/filename).read_bytes();remote=STAGE+'\\'+filename;desired=hashlib.sha256(data).digest()
  shell(client,'clear',filename.encode()+desired+b'-clear',f"[IO.File]::WriteAllBytes('{remote}',[byte[]]@());'CLEARED'")
  for index in range(0,len(data),2250):
   block=data[index:index+2250];encoded=base64.b64encode(block).decode();command=f"$b=[Convert]::FromBase64String('{encoded}');$f=[IO.File]::Open('{remote}',[IO.FileMode]::Append,[IO.FileAccess]::Write);try{{$f.Write($b,0,$b.Length)}}finally{{$f.Dispose()}};'APPENDED'"
   shell(client,'chunk',filename.encode()+desired+index.to_bytes(4,'big'),command)
 install_root=r'C:\Users\Public\HomeCenterPocketTtsInstallV2';ready=install_root+r'\READY-v2.json';log=STAGE+r'\bootstrap.log'
 arguments=f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{STAGE}\\bootstrap.ps1" -InstallRoot "{install_root}"'
 launch_id='ptts-launch-'+hashlib.sha256((arguments+str(time.time_ns())).encode()).hexdigest()[:24]
 _run_action(client,launch_id,'process.start',{'command':'powershell.exe','arguments':arguments,'workingDirectory':STAGE},120)
 for attempt in range(90):
  probe=f"if(Test-Path '{ready}'){{Get-Content -Raw '{ready}'}}elseif(Test-Path '{log}.err'){{$e=Get-Content -Raw '{log}.err';if($e){{$e}}else{{'PENDING'}}}}else{{'PENDING'}}"
  output=shell(client,'probe',attempt.to_bytes(2,'big')+str(time.time_ns()).encode(),probe)
  if 'pocket-tts-render-v2' in output:break
  if output!='PENDING' and output.strip():raise RuntimeError('Cauldron bootstrap failed: '+output[-500:])
  time.sleep(5)
 else:raise RuntimeError('Cauldron bootstrap did not publish readiness within 15 minutes')
 print(json.dumps({'status':'ready','workerId':status.get('workerId'),'contractVersion':'pocket-tts-render-v2','transport':'home-center-computer-hands'}));return 0
if __name__=='__main__':raise SystemExit(main())
