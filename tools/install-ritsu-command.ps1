# Installs the 'ritsu on/off/status' command to the current user's PATH.
# Can be run directly after downloading this single installer; fetches its companion scripts.
param([string]$SourceDir = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$dest = Join-Path $HOME 'bin'
$names = @('ritsu.cmd','ritsu.ps1','ritsu-on.ps1','ritsu-off.ps1')
$base = 'https://raw.githubusercontent.com/Valar05/home-center/main/tools/'
$staging = Join-Path ([IO.Path]::GetTempPath()) ('ritsu-cli-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $staging | Out-Null
try {
  foreach ($name in $names) {
    $source = Join-Path $SourceDir $name
    $target = Join-Path $staging $name
    if (Test-Path -LiteralPath $source -PathType Leaf) {
      Copy-Item -LiteralPath $source -Destination $target
    } else {
      Invoke-WebRequest -Uri ($base + $name) -OutFile $target -UseBasicParsing
    }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or (Get-Item $target).Length -eq 0) { throw "Unable to stage $name" }
  }
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  foreach ($name in $names) { Copy-Item -LiteralPath (Join-Path $staging $name) -Destination (Join-Path $dest $name) -Force }
  $old = [Environment]::GetEnvironmentVariable('Path','User')
  $parts = @($old -split ';' | Where-Object { $_ -and $_.Trim() })
  if (-not @($parts | Where-Object { $_.TrimEnd('\') -ieq $dest.TrimEnd('\') }).Count) {
    [Environment]::SetEnvironmentVariable('Path', (($parts + $dest) -join ';'), 'User')
  }
  if (-not @($env:Path -split ';' | Where-Object { $_.TrimEnd('\') -ieq $dest.TrimEnd('\') }).Count) { $env:Path += ';' + $dest }
  Write-Host "Installed Ritsu command in $dest and registered the user PATH."
  Write-Host 'Open a NEW terminal: ritsu status ; ritsu off ; ritsu on'
  Write-Host 'The installer did not start or stop the voice service.'
} finally { Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue }
