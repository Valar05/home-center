#Requires -Version 5.1
[CmdletBinding()]
param([ValidateSet('Audit','Install','Test')][string]$Mode='Audit',[string]$Image='', [string]$Output='')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
if($env:COMPUTERNAME -ine 'THECAULDRON'){throw 'Wrong host. Aborting.'}
$root=Join-Path $env:USERPROFILE 'workspace\pose-vision-sam21'
$scriptPath=Join-Path $root 'pose_vision_probe.py'
$venv=Join-Path $root '.venv'
$py=Join-Path $venv 'Scripts\python.exe'
$source='https://raw.githubusercontent.com/Valar05/home-center/a54c716b3fa0c7a0d5caff8836dd271bd0946715/tools/pose_vision_probe.py'
$disk=Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
if(-not $disk){throw 'Cannot inspect C drive.'}
Write-Output ('VISION_MODE='+$Mode+' FREE_GIB='+[math]::Round($disk.FreeSpace/1GB,2))
if($Mode -eq 'Audit'){
 Write-Output ('VENV_PRESENT='+(Test-Path $py))
 Write-Output ('PROBE_PRESENT='+(Test-Path $scriptPath))
 & py -0p
 exit 0
}
if($Mode -eq 'Install'){
 if($disk.FreeSpace -lt 10GB){throw 'Under 10 GiB free, refusing installation.'}
 if(-not(Test-Path $py)){
  New-Item -ItemType Directory -Path $root -Force|Out-Null
  & py -3.10 -m venv $venv
  if($LASTEXITCODE -ne 0){throw 'Python 3.10 virtual environment creation failed'}
 }
 & $py -m pip install --disable-pip-version-check --no-cache-dir 'ultralytics==8.3.232'
 if($LASTEXITCODE -ne 0){throw 'Installation failed'}
 Invoke-WebRequest -Uri $source -OutFile $scriptPath -UseBasicParsing
 if(-not(Test-Path $scriptPath)){throw 'Failed to fetch probe from GitHub'}
}
if(-not(Test-Path $py) -or -not(Test-Path $scriptPath)){throw 'Not installed. Run -Mode Install.'}
if(-not $Output){$Output=Join-Path $root 'evidence\smoke'}
$probeArgs=@($scriptPath,'--output',$Output,'--device','cpu')
if($Image){$probeArgs+=@('--image',$Image)}
& $py @probeArgs
if($LASTEXITCODE -ne 0){throw 'Real SAM inference failed.'}
Write-Output ('VISION_PROBE_PASS='+$Output)
Write-Output 'SEMANTIC_LANDMARK_VALIDATION=NOT_TESTED'
