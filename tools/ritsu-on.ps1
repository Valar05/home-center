# ritsu-on.ps1
# Resume the existing Ritsu Pocket TTS service without touching other Python workloads.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Join-Path $HOME 'Documents\Codex\Venice\PocketTTS'
$marker = Join-Path $root 'RITSU_POCKET_MAINTENANCE'
$server = Join-Path $root 'ritsu_pocket_repertoire_server_v2.py'
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $server -PathType Leaf) -or
    -not (Test-Path -LiteralPath $pythonw -PathType Leaf)) {
    throw "Expected Pocket TTS installation not found under $root. Nothing started."
}
# Removing the flag permits the existing watchdog to start the API.
Remove-Item -LiteralPath $marker -Force -ErrorAction SilentlyContinue
Write-Host 'Ritsu Pocket auto-start enabled.'
function Get-RitsuListener {
    $listeners = @(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 10205 -State Listen -ErrorAction SilentlyContinue)
    foreach ($conn in $listeners) {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId = $($conn.OwningProcess)" -ErrorAction SilentlyContinue
        if ($p -and ([string]$p.CommandLine) -match 'ritsu_pocket_repertoire_server_v2\.py') {
            return $p.ProcessId
        }
        Write-Warning "Port 10205 is held by an unrecognized process. Not launching another service."
        return -1
    }
    return $null
}
$existing = Get-RitsuListener
if ($existing -eq -1) { throw 'Port conflict: nothing launched.' }
if ($null -ne $existing) {
    Write-Host "Ritsu Pocket already listening (PID $existing)."
    return
}
# Check whether the existing supervisor is active, so we do not race it.
$supervisor = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
    Where-Object { ([string]$_.CommandLine) -match 'ritsu_pocket_supervisor\.py' })
if ($supervisor.Count -gt 0) {
    Write-Host 'Existing Pocket supervisor detected. Waiting for it to bring the model back.'
    for ($i=0; $i -lt 12; $i++) {
        Start-Sleep -Seconds 5
        $pidFound = Get-RitsuListener
        if ($pidFound -eq -1) { throw 'Unexpected port owner: no process started.' }
        if ($null -ne $pidFound) {
            Write-Host "Ritsu Pocket listening (PID $pidFound)."
            return
        }
    }
    Write-Warning 'Supervisor present but API did not become available within 60 seconds. Check the existing supervisor log.'
    return
}
# Without a supervisor, start precisely the existing known service.
$started = Start-Process -FilePath $pythonw -ArgumentList ('"' + $server + '"') -WorkingDirectory $root -PassThru -WindowStyle Hidden
Write-Host "Ritsu Pocket start requested (PID $($started.Id))."
for ($i=0; $i -lt 12; $i++) {
    Start-Sleep -Seconds 5
    $pidFound = Get-RitsuListener
    if ($pidFound -eq -1) { throw 'Unexpected port owner: startup not verified.' }
    if ($null -ne $pidFound) {
        Write-Host "Ritsu Pocket listening (PID $pidFound)."
        return
    }
}
Write-Warning 'API not listening after 60 seconds. Startup was requested, not verified.'
