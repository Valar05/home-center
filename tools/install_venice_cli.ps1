param(
    [string]$BinDir = (Join-Path $HOME 'bin'),
    [switch]$NoPathUpdate
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$source = Join-Path $PSScriptRoot 'venice_cli.ps1'
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing Venice CLI source: $source" }
[IO.Directory]::CreateDirectory($BinDir) | Out-Null
$scriptTarget = Join-Path $BinDir 'venice.ps1'
$cmdTarget = Join-Path $BinDir 'venice.cmd'
Copy-Item -LiteralPath $source -Destination $scriptTarget -Force

$cmd = @'
@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0venice.ps1" %*
exit /b %ERRORLEVEL%
'@
[IO.File]::WriteAllText($cmdTarget, $cmd, [Text.Encoding]::ASCII)

$pathChanged = $false
if (-not $NoPathUpdate) {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $entries = @($userPath -split ';' | Where-Object { $_ })
    if (-not ($entries | Where-Object { $_.TrimEnd('\') -ieq $BinDir.TrimEnd('\') })) {
        $newPath = (@($entries) + @($BinDir)) -join ';'
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        $pathChanged = $true
    }
}

[ordered]@{
    ok = $true
    command = 'venice'
    script = $scriptTarget
    launcher = $cmdTarget
    pathUpdated = $pathChanged
    note = if ($pathChanged) { 'Open a new terminal for the user PATH update to be visible.' } else { 'Existing PATH was preserved.' }
} | ConvertTo-Json -Depth 5
