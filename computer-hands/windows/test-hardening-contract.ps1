param([string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$paths=@(
  'computer-hands/windows/repair.ps1',
  'computer-hands/windows/home-center-hands.ps1',
  'computer-hands/windows/watchdog.ps1',
  'computer-hands/windows/fortress-sentinel.ps1',
  'computer-hands/windows/launch.ps1',
  'computer-hands/windows/harden.ps1'
)
foreach($rel in $paths){
  $path=Join-Path $Root $rel
  $tokens=$null;$errors=$null
  [System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)|Out-Null
  if($errors.Count){ throw "parse failed $rel : $($errors[0].Message)" }
}
function Need([string]$File,[string]$Text){
  $body=Get-Content -LiteralPath (Join-Path $Root $File) -Raw
  if(-not $body.Contains($Text)){ throw "$File missing contract: $Text" }
}
function Forbid([string]$File,[string]$Text){
  $body=Get-Content -LiteralPath (Join-Path $Root $File) -Raw
  if($body.Contains($Text)){ throw "$File contains forbidden contract: $Text" }
}
Forbid 'computer-hands/windows/repair.ps1' "Run repair from the normal interactive Windows account."
Need 'computer-hands/windows/home-center-hands.ps1' 'home-center-computer-hands-cloud-health-v1'
Need 'computer-hands/windows/home-center-hands.ps1' 'poll_error_threshold_exit'
Need 'computer-hands/windows/watchdog.ps1' 'cloud_health_stale_'
Need 'computer-hands/windows/watchdog.ps1' 'RestartCooldownSeconds'
Need 'computer-hands/windows/fortress-sentinel.ps1' 'SetThreadExecutionState'
Need 'computer-hands/windows/fortress-sentinel.ps1' 'actions.runner'
Need 'computer-hands/windows/fortress-sentinel.ps1' 'Ensure-Throne'
Need 'computer-hands/windows/fortress-sentinel.ps1' 'Ensure-Tailscale'
Need 'computer-hands/windows/harden.ps1' 'standby-timeout-ac 0'
Need 'computer-hands/windows/harden.ps1' 'hibernate-timeout-ac 0'
Need 'computer-hands/windows/harden.ps1' '5ca83367-6e45-459f-a27b-476b1d01c936 0'
Need 'computer-hands/windows/harden.ps1' '-WakeToRun'
Need 'computer-hands/windows/harden.ps1' 'RestartCount 999'
Need 'computer-hands/windows/harden.ps1' 'RepetitionInterval (New-TimeSpan -Minutes 1)'
'CAULDRON_HARDENING_SOURCE_OK'
