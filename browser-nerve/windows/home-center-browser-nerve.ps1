param(
  [string]$ConfigPath = "$env:LOCALAPPDATA\HomeCenter\BrowserNerve\config.json"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Home Center Browser Nerve Windows worker requires Windows.' }

function Read-Config {
  if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "Browser Nerve config not found: $ConfigPath" }
  $cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
  if (-not $cfg.origin -or -not $cfg.workerId -or -not $cfg.tokenPath -or -not $cfg.executorPath) { throw 'Browser Nerve config is incomplete.' }
  return $cfg
}
function Read-WorkerToken([object]$Cfg) {
  if (-not (Test-Path -LiteralPath $Cfg.tokenPath)) { throw 'Browser Nerve token file is missing.' }
  $secure = ((Get-Content -LiteralPath $Cfg.tokenPath -Raw).Trim()) | ConvertTo-SecureString
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

$Cfg = Read-Config
$Token = Read-WorkerToken $Cfg
$Origin = ([string]$Cfg.origin).TrimEnd('/')
$WorkerId = [string]$Cfg.workerId
$Root = Split-Path -Parent $ConfigPath
$LogPath = if ($Cfg.logPath) { [string]$Cfg.logPath } else { Join-Path $Root 'worker.log' }
$ProgressPath = if ($Cfg.progressPath) { [string]$Cfg.progressPath } else { Join-Path $Root 'progress.json' }
$NodePath = if ($Cfg.nodePath) { [string]$Cfg.nodePath } else { (Get-Command node.exe -ErrorAction Stop).Source }
$ExecutorPath = [string]$Cfg.executorPath
$BrowserProfile = if ($Cfg.browserProfile) { [string]$Cfg.browserProfile } else { Join-Path $Root 'chrome-profile' }
$DebugPort = if ($Cfg.debugPort) { [int]$Cfg.debugPort } else { 9223 }
$WorkerVersion = '1.0.0'

function Log([string]$Message) {
  Add-Content -LiteralPath $LogPath -Value "$(Get-Date -Format o) $Message" -Encoding UTF8
  $info = Get-Item -LiteralPath $LogPath -ErrorAction SilentlyContinue
  if ($info -and $info.Length -gt 2MB) {
    Get-Content -LiteralPath $LogPath -Tail 1000 | Set-Content -LiteralPath "$LogPath.tmp" -Encoding UTF8
    Move-Item -Force "$LogPath.tmp" $LogPath
  }
}
function Write-Progress([object]$State) {
  try {
    $payload = [ordered]@{updatedAt=(Get-Date).ToUniversalTime().ToString('o');workerId=$WorkerId;machine=$env:COMPUTERNAME;pid=$PID;state=$State} | ConvertTo-Json -Depth 12
    [IO.File]::WriteAllText("$ProgressPath.tmp", $payload, [Text.UTF8Encoding]::new($false))
    Move-Item -Force "$ProgressPath.tmp" $ProgressPath
  } catch { Log "progress_failed $($_.Exception.Message)" }
}
function Invoke-Api([string]$Method, [string]$Path, [object]$Body = $null) {
  $headers = @{Authorization="Bearer $Token";'X-Home-Center-Worker'=$WorkerId}
  $params = @{Method=$Method;Uri="$Origin/browser-nerve/v1/$Path";Headers=$headers;ContentType='application/json';TimeoutSec=135}
  if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Depth 20 -Compress) }
  Invoke-RestMethod @params
}
function Invoke-Executor([object]$Ticket) {
  $temp = Join-Path $Root ("ticket-{0}.json" -f ([Guid]::NewGuid().ToString('N')))
  try {
    [IO.File]::WriteAllText($temp, ($Ticket | ConvertTo-Json -Depth 30 -Compress), [Text.UTF8Encoding]::new($false))
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $NodePath
    $psi.Arguments = "`"$ExecutorPath`" `"$temp`""
    $psi.WorkingDirectory = $Root
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.EnvironmentVariables['BROWSER_NERVE_ROOT'] = $Root
    $psi.EnvironmentVariables['BROWSER_NERVE_PROFILE'] = $BrowserProfile
    $psi.EnvironmentVariables['BROWSER_NERVE_DEBUG_PORT'] = [string]$DebugPort
    $p = New-Object Diagnostics.Process
    $p.StartInfo = $psi
    [void]$p.Start()
    $stdoutTask = $p.StandardOutput.ReadToEndAsync(); $stderrTask = $p.StandardError.ReadToEndAsync()
    if (-not $p.WaitForExit(125000)) { try { $p.Kill() } catch {}; throw 'Browser action exceeded 125 seconds.' }
    $stdout = $stdoutTask.Result.Trim(); $stderr = $stderrTask.Result.Trim()
    if ($stderr) { Log "executor_stderr $($stderr.Substring(0,[Math]::Min(3000,$stderr.Length)))" }
    $lines = @($stdout -split "`r?`n" | Where-Object { $_.Trim() })
    if (-not $lines.Count) { throw "Browser executor returned no JSON (exit $($p.ExitCode))." }
    $result = $lines[-1] | ConvertFrom-Json
    return $result
  } finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}

Log "worker_start workerId=$WorkerId pid=$PID"
Write-Progress @{phase='worker_start';message='Browser Nerve worker started.'}
while ($true) {
  try {
    $lease = Invoke-Api 'POST' 'lease' @{}
    if (-not $lease.ticket) {
      Write-Progress @{phase='idle';message='Waiting for browser work.'}
      Start-Sleep -Seconds ([Math]::Max(1,[int]$lease.pollAfterSeconds)); continue
    }
    $ticket = $lease.ticket
    Log "ticket_leased id=$($ticket.ticketId) session=$($ticket.sessionId) action=$($ticket.action)"
    Write-Progress @{phase='leased';ticketId=$ticket.ticketId;sessionId=$ticket.sessionId;action=$ticket.action}
    $hb = Invoke-Api 'POST' "tickets/$($ticket.ticketId)/heartbeat" @{phase='running';message="Executing $($ticket.action)";machine=$env:COMPUTERNAME;browser='chrome-cdp';workerVersion=$WorkerVersion}
    if ($hb.cancelRequested -eq $true) { Write-Progress @{phase='cancelled';ticketId=$ticket.ticketId}; continue }
    $result = Invoke-Executor $ticket
    $completion = Invoke-Api 'POST' "tickets/$($ticket.ticketId)/complete" @{result=$result}
    Write-Progress @{phase=$completion.status;ticketId=$ticket.ticketId;sessionId=$ticket.sessionId;action=$ticket.action;episodeId=$completion.episodeId;ok=($result.ok -ne $false)}
    Log "ticket_complete id=$($ticket.ticketId) status=$($completion.status) episode=$($completion.episodeId)"
  } catch {
    Log "poll_or_action_error $($_.Exception.Message)"
    Write-Progress @{phase='error';message=$_.Exception.Message}
    Start-Sleep -Seconds 2
  }
}
