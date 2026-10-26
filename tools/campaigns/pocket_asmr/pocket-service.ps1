#requires -version 5.1
param([ValidateSet('on','off','status','install')][string]$Mode='status')
$ErrorActionPreference='Stop'
$Name='Ritsu Pocket ASMR Gateway'
$Campaign=Join-Path $env:USERPROFILE 'PocketASMRGit\tools\campaigns\pocket_asmr'
$Python='C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\.venv\Scripts\python.exe'
$Gateway=Join-Path $Campaign 'asmr_api.py'
$Secret=Join-Path $env:USERPROFILE 'PocketASMR\gateway-token.txt'
if($Mode -eq 'install'){
  if(!(Test-Path $Python)){throw 'Pocket Python missing'}
  if(!(Test-Path $Gateway)){throw 'Git campaign missing: sync before install'}
  if(!(Test-Path $Secret)){
    New-Item -ItemType Directory -Force (Split-Path $Secret) | Out-Null
    $bytes=New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    [IO.File]::WriteAllText($Secret,[Convert]::ToBase64String($bytes))
  }
  $Action=New-ScheduledTaskAction -Execute $Python -Argument ('"'+$Gateway+'"')
  $Principal=New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
  $Settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $Name -Action $Action -Principal $Principal -Settings $Settings -Force | Out-Null
  Write-Output 'INSTALLED ASMR gateway task; ordinary Pocket voice service unchanged'
  exit
}
$Task=Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
if(!$Task){Write-Output 'ASMR_GATEWAY=not_installed';exit 2}
if($Mode -eq 'on'){
  Start-ScheduledTask -TaskName $Name
  Start-Sleep -Seconds 2
}elseif($Mode -eq 'off'){
  Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}
$Task=Get-ScheduledTask -TaskName $Name
Write-Output ('ASMR_GATEWAY='+$Task.State)
Write-Output 'POCKET_VOICE_UNTOUCHED=true'
