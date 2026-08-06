[CmdletBinding()]
param(
  [Parameter(Position=0)][ValidateSet("status","pause","resume","uninstall")][string]$Action="status",
  [string]$Root="$env:LOCALAPPDATA\HelmCenter\cauldron-voice-farm",
  [switch]$Approved
)
$ErrorActionPreference = "Stop"
$Root = [IO.Path]::GetFullPath($Root)
$ExpectedParent = [IO.Path]::GetFullPath("$env:LOCALAPPDATA\HelmCenter")
if (-not $Root.StartsWith($ExpectedParent, [StringComparison]::OrdinalIgnoreCase) -or $Root -eq $ExpectedParent) { throw "REFUSED_ROOT_OUTSIDE_VOICE_FARM" }
$State = Join-Path $Root "state"
$Paused = Join-Path $State "paused"
switch ($Action) {
  "status" { @{schemaVersion="home-center.cauldron-voice-control-status.v1"; host=$env:COMPUTERNAME; root=$Root; installed=(Test-Path "$Root\install-receipt.json"); paused=(Test-Path $Paused); serviceInstalled=$false; publicListenerCreated=$false} | ConvertTo-Json }
  "pause" { New-Item -ItemType Directory -Force -Path $State | Out-Null; [DateTime]::UtcNow.ToString("o") | Set-Content -Encoding ASCII $Paused; & $MyInvocation.MyCommand.Path status -Root $Root }
  "resume" { if (Test-Path $Paused) { Remove-Item -Force $Paused }; & $MyInvocation.MyCommand.Path status -Root $Root }
  "uninstall" { if (-not $Approved) { throw "UNINSTALL_REQUIRES_APPROVED" }; if (Test-Path $Root) { Remove-Item -LiteralPath $Root -Recurse -Force }; @{removed=(-not (Test-Path $Root)); root=$Root} | ConvertTo-Json }
}
