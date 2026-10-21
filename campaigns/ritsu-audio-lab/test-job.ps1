param([ValidateSet('test')][string]$Stage='test')
$ErrorActionPreference='Continue'
$Root=Join-Path $env:USERPROFILE 'workspace\ritsu-audio-lab'
$Python=Join-Path $Root '.venv\Scripts\python.exe'
$Probe=Join-Path $PSScriptRoot 'probe.py'
$Receipt=Join-Path $Root 'clap-test-receipt.json'
$Stdout=Join-Path $Root 'clap-test.stdout.log'
$Stderr=Join-Path $Root 'clap-test.stderr.log'
$State=Join-Path $Root 'clap-test-state.json'
New-Item -ItemType Directory -Force -Path $Root | Out-Null
@{state='started';at=(Get-Date).ToString('o');stage=$Stage} | ConvertTo-Json | Set-Content $State
try {
  & $Python $Probe $Stage $Receipt 1> $Stdout 2> $Stderr
  $Code=$LASTEXITCODE
  @{state=$(if($Code -eq 0){'completed'}else{'failed'});exitCode=$Code;at=(Get-Date).ToString('o');receipt=$Receipt;stdout=$Stdout;stderr=$Stderr} | ConvertTo-Json | Set-Content $State
} catch {
  $_ | Out-String | Add-Content $Stderr
  @{state='failed';error=$_.Exception.Message;at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content $State
}
