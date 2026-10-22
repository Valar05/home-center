#requires -Version 5.1
<#
Ritsu / THECAULDRON firewall repair campaign.
Run from an elevated PowerShell session, or launch normally with -Apply to request UAC.
Default mode is read-only. Scope: Pixel's Tailscale IP -> THECAULDRON:19643/TCP.
Never modifies the Android receiver, bearer token, relay implementation, or audio generation.
#>
[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$NoElevate
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ruleName = 'Ritsu Tailscale Audio Relay 19643'
$hostIp = '100.68.37.106'
$phoneIp = '100.117.17.119'
$port = 19643
$root = Join-Path $env:LOCALAPPDATA 'Ritsu\campaign-receipts'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
function Fail([string]$message) { throw "[RITSU FIREWALL] $message" }
function IsAdmin {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Snapshot {
    $rules = @(Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)
    foreach ($rule in $rules) {
        $p = $rule | Get-NetFirewallPortFilter
        $a = $rule | Get-NetFirewallAddressFilter
        [pscustomobject]@{
            Name = $rule.DisplayName
            Enabled = "$($rule.Enabled)"
            Direction = "$($rule.Direction)"
            Action = "$($rule.Action)"
            Protocol = "$($p.Protocol)"
            LocalPort = "$($p.LocalPort)"
            LocalAddress = "$($a.LocalAddress)"
            RemoteAddress = "$($a.RemoteAddress)"
        }
    }
}
try {
    Write-Host '[RITSU FIREWALL] PREFLIGHT'
    $listener = @(Get-NetTCPConnection -LocalAddress $hostIp -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    if ($listener.Count -ne 1) { Fail "Expected exactly one listener on ${hostIp}:${port}; found $($listener.Count)" }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener[0].OwningProcess)"
    if (-not $process -or $process.CommandLine -notmatch 'embodiment_campaign[\\/]relay.py') {
        Fail 'Listener is not the expected existing Ritsu Python relay'
    }
    Write-Host "[RITSU FIREWALL] Relay PID $($listener[0].OwningProcess) verified"
    $before = @(Snapshot)
    if ($before.Count -gt 1) { Fail 'Multiple campaign-named rules found; manual review required' }
    if ($before.Count -eq 1) {
        $b = $before[0]
        if ($b.Enabled -eq 'True' -and $b.Direction -eq 'Inbound' -and $b.Action -eq 'Allow' -and
            $b.Protocol -eq 'TCP' -and $b.LocalPort -eq "$port" -and
            $b.LocalAddress -eq $hostIp -and $b.RemoteAddress -eq $phoneIp) {
            Write-Host '[RITSU FIREWALL] PASS: Existing exact scoped rule; no change'
            exit 0
        }
        Fail 'Existing rule differs from expected scope; refusing destructive replacement'
    }
    if (-not $Apply) {
        Write-Host "[RITSU FIREWALL] DRY RUN: Would allow TCP $phoneIp -> ${hostIp}:$port only"
        Write-Host '[RITSU FIREWALL] To apply: .\ritsu-firewall-repair-20261021.ps1 -Apply'
        exit 0
    }
    if (-not (IsAdmin)) {
        if ($NoElevate) { Fail 'Administrator rights required' }
        Write-Host '[RITSU FIREWALL] Requesting elevation (Windows UAC)'
        $scriptPath = $MyInvocation.MyCommand.Path
        if (-not $scriptPath) { Fail 'Must run script from a saved .ps1 file to elevate' }
        $args = @('-NoProfile','-ExecutionPolicy','Bypass','-File', ('"' + $scriptPath + '"'), '-Apply','-NoElevate')
        $child = Start-Process powershell.exe -Verb RunAs -Wait -PassThru -ArgumentList $args
        if ($child.ExitCode -ne 0) { Fail "Elevated script exited $($child.ExitCode)" }
        Write-Host '[RITSU FIREWALL] Elevated repair reported exit 0'
        exit 0
    }
    Write-Host '[RITSU FIREWALL] APPLY: creating restricted rule'
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP `
      -LocalPort $port -LocalAddress $hostIp -RemoteAddress $phoneIp -Profile Any -Enabled True | Out-Null
    $after = @(Snapshot)
    if ($after.Count -ne 1 -or $after[0].Enabled -ne 'True' -or
        $after[0].Action -ne 'Allow' -or $after[0].Direction -ne 'Inbound' -or
        $after[0].Protocol -ne 'TCP' -or $after[0].LocalPort -ne "$port" -or
        $after[0].LocalAddress -ne $hostIp -or $after[0].RemoteAddress -ne $phoneIp) {
        Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        Fail 'Readback mismatch; removed campaign-created rule'
    }
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    $receipt = Join-Path $root "firewall-$stamp.json"
    [pscustomobject]@{
        status = 'FIREWALL_RULE_VERIFIED_NOT_PHONE_HEARD'
        at = (Get-Date).ToString('o')
        rule = $after[0]
        relayPid = $listener[0].OwningProcess
        source = $MyInvocation.MyCommand.Path
        sourceSha256 = (Get-FileHash $MyInvocation.MyCommand.Path -Algorithm SHA256).Hash
    } | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $receipt
    Write-Host "[RITSU FIREWALL] PASS: Rule verified; receipt=$receipt"
    Write-Host '[RITSU FIREWALL] Phone /health and actual audible playback require separate verification'
    exit 0
}
catch {
    Write-Error "[RITSU FIREWALL] BLOCKED: $($_.Exception.Message)"
    exit 1
}
