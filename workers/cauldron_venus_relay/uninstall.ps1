$ErrorActionPreference = "Stop"
$InstallRoot = Join-Path $env:LOCALAPPDATA "Fortress\VenusCauldronRelay\v1"
$TaskName = "Fortress Venus Cauldron Relay"
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
if (Test-Path $InstallRoot) {
    $Quarantine = "$InstallRoot.disabled.$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
    Move-Item $InstallRoot $Quarantine
    Write-Host "Worker disabled and moved to $Quarantine. Revoke its Helm Center token separately."
} else {
    Write-Host "Worker task removed; no install directory was present."
}

