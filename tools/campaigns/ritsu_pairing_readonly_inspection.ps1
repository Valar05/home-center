param([ValidateSet('inspect')][string]$Mode='inspect')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$expected='Valar05/home-center'
$remote=(& git -C $repo remote get-url origin 2>$null)
if ($LASTEXITCODE -ne 0 -or $remote -notmatch 'Valar05[/:]home-center(?:\.git)?$') { throw 'WRONG_REPOSITORY' }
$head=(& git -C $repo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'HEAD_UNAVAILABLE' }
Write-Output "RESOLVED_REPO=$repo"
Write-Output "EXECUTION_DIR=$repo"
$branchLines=@(& git -C $repo branch --show-current)
$branch=if($branchLines.Count -and $branchLines[0]) {[string]$branchLines[0]} else {'DETACHED'}
Write-Output "BRANCH=$branch"
Write-Output "HEAD=$head"
$dir=Join-Path $env:LOCALAPPDATA 'RitsuControlBridge\pairing-inspection'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$receipt=Join-Path $dir 'last-readonly-inspection.json'
$time=(Get-Date).ToUniversalTime().ToString('o')
$ports=@(19646,19647)
$listeners=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $ports -contains $_.LocalPort } | Select-Object LocalAddress,LocalPort,OwningProcess,State)
$procs=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'ritsu-local-server[\\/]server\.mjs|ritsu_control_playwright_bridge\.mjs' } | Select-Object ProcessId,Name,@{N='Role';E={if ($_.CommandLine -match 'server\.mjs') {'server'} else {'browser-bridge'}}})
$tailscaleExe='C:\Program Files\Tailscale\tailscale.exe'
$tailState='unavailable'
if(Test-Path $tailscaleExe) {
 try {
  $ts=(& $tailscaleExe status --json 2>$null | ConvertFrom-Json)
  if($LASTEXITCODE -eq 0){$tailState=[string]$ts.BackendState}
 } catch {$tailState='error'}
}
$privateProbe='unverified'
try {
 $response=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:19647/' -TimeoutSec 3 -ErrorAction Stop
 $privateProbe="HTTP_$([int]$response.StatusCode)"
} catch {
 if($_.Exception.Response){$privateProbe="HTTP_$([int]$_.Exception.Response.StatusCode)"}
 else {$privateProbe='unreachable_or_no_route'}
}
$result=[ordered]@{schema='ritsu-pairing-inspection-v1';timestampUtc=$time;gitHead=$head;machine=$env:COMPUTERNAME;listeners=$listeners;processes=$procs;tailscaleBackend=$tailState;loopback19647Probe=$privateProbe;phonePairing='UNVERIFIED';endToEnd='UNVERIFIED'}
$json=$result | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText($receipt,$json,[Text.UTF8Encoding]::new($false))
Write-Output $json
Write-Output "RECEIPT=$receipt"
