param([switch]$KeepLogs)
$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'HomeCenter\ComputerHands'
$taskName='HomeCenterComputerHands'
$task=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if($task){try{Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue}catch{};Unregister-ScheduledTask -TaskName $taskName -Confirm:$false}
if(Test-Path -LiteralPath $root){
  if($KeepLogs){
    Get-ChildItem -LiteralPath $root -Force | Where-Object Name -ne 'worker.log' | Remove-Item -Recurse -Force
  } else { Remove-Item -LiteralPath $root -Recurse -Force }
}
[ordered]@{ok=$true;taskRemoved=$true;localStateRemoved=$true;driveFilesTouched=$false;fileLayer='drive_sync'}|ConvertTo-Json
