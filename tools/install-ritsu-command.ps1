# Install Home Center's two-command Ritsu Pocket launcher into the current user's PATH.
# Run from the checked-out home-center repository, or invoke the installer via -SourceDir.
param([string]$SourceDir = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$dest = Join-Path $HOME 'bin'
$names = @('ritsu.cmd','ritsu.ps1','ritsu-on.ps1','ritsu-off.ps1')
foreach ($name in $names) {
    $source = Join-Path $SourceDir $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing source: $source. Nothing installed." }
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($name in $names) { Copy-Item -LiteralPath (Join-Path $SourceDir $name) -Destination (Join-Path $dest $name) -Force }
$old = [Environment]::GetEnvironmentVariable('Path','User')
$parts = @($old -split ';' | Where-Object { $_ -and $_.Trim() })
if (-not (@($parts | Where-Object { $_.TrimEnd('\') -ieq $dest.TrimEnd('\') }).Count)) {
  [Environment]::SetEnvironmentVariable('Path', (($parts + $dest) -join ';'), 'User')
}
$sessionParts = @($env:Path -split ';' | Where-Object { $_ })
if (-not (@($sessionParts | Where-Object { $_.TrimEnd('\') -ieq $dest.TrimEnd('\') }).Count)) { $env:Path += ';' + $dest }
Write-Host "Installed in $dest and registered in user PATH."
Write-Host 'Open a NEW terminal and run: ritsu status | ritsu off | ritsu on'
Write-Host 'No voice service was started or stopped during installation.'
