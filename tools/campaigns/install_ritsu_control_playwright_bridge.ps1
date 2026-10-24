param([ValidateSet("install","doctor","status","receipts")][string]$Action="install")
$ErrorActionPreference="Stop"
$ProgressPreference="SilentlyContinue"
$root=Join-Path $env:LOCALAPPDATA "RitsuControlBridge"
$file=Join-Path $root "ritsu_control_playwright_bridge.mjs"
$receipt=Join-Path $root "campaign-last-receipt.json"
$sourceRevision="5d57e79ab025ec6d3b65187176fc7c8357ffa502"
$sourceUrl="https://raw.githubusercontent.com/Valar05/home-center/$sourceRevision/tools/campaigns/ritsu_control_playwright_bridge.mjs"
New-Item -ItemType Directory -Path $root -Force | Out-Null
function Record([string]$phase,[string]$message,[bool]$ok) {
  $data=[ordered]@{phase=$phase;message=$message;ok=$ok;timestamp=(Get-Date).ToUniversalTime().ToString("o");entrypoint=$file}
  $data | ConvertTo-Json -Compress | Set-Content -Path $receipt -Encoding UTF8
  Write-Output ("RITSU_BRIDGE_CAMPAIGN="+($data|ConvertTo-Json -Compress))
}
try {
  if($Action -eq "receipts") {if(Test-Path $receipt){Get-Content $receipt};exit 0}
  if($Action -eq "status") {
    Record "status" ($(if(Test-Path $file){"script_installed"}else{"script_not_installed"})) (Test-Path $file)
    exit $(if(Test-Path $file){0}else{2})
  }
  if($Action -eq "install"){
    $candidate=Join-Path $root "ritsu_control_playwright_bridge.pending.mjs"
    Invoke-WebRequest -Uri $sourceUrl -OutFile $candidate -UseBasicParsing -TimeoutSec 30
    if((Get-Item $candidate).Length -lt 4000){throw "Source truncated"}
    & node --check $candidate
    if($LASTEXITCODE -ne 0){throw "Node syntax check failed"}
    if(Test-Path $file){
      if((Get-FileHash $file -Algorithm SHA256).Hash -ne (Get-FileHash $candidate -Algorithm SHA256).Hash) {
        Copy-Item $file ($file+".backup-"+(Get-Date -Format "yyyyMMddHHmmss")) -ErrorAction Stop
      }
    }
    Move-Item $candidate $file -Force
  }
  if(!(Test-Path $file)){throw "Playwright bridge not installed"}
  & node $file --doctor
  if($LASTEXITCODE -ne 0){throw "Playwright browser doctor failed with exit "+$LASTEXITCODE}
  Record "doctor" ("playwright_live_cdp_probe_succeeded;sha256="+(Get-FileHash $file -Algorithm SHA256).Hash) $true
  exit 0
}catch{
  Record "blocked" ([string]$_.Exception.Message) $false
  exit 1
}
