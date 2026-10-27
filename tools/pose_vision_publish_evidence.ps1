#Requires -Version 5.1
$ErrorActionPreference='Stop'
$src='C:\Users\dclar\workspace\pose-vision-sam21\evidence'
$dst='G:\My Drive\Panzer-PoseLab-20261024\ModelAudit-20261026'
if($env:COMPUTERNAME -ine 'THECAULDRON'){throw 'Wrong machine'}
$report=Join-Path $src 'panzer-sam-probe-20261026\receipt.json'
if(-not(Test-Path -LiteralPath $report)){throw 'No completed SAM benchmark receipt'}
$entries=(Get-Content -LiteralPath $report -Raw|ConvertFrom-Json).results
if($entries.Count -ne 3){throw 'Expected three tested source sheets'}
New-Item -ItemType Directory -Path $dst -Force|Out-Null
$inputs=@(
 @('panzer-source-audit-20261026\source-inventory.json','source-inventory.json'),
 @('panzer-sam-probe-20261026\receipt.json','sam-benchmark-receipt.json')
)
foreach($name in @('hulls','turrets','barrels')){
 $inputs+= ,@("panzer-source-audit-20261026\$name-components.png","$name-components.png")
 foreach($image in @('input-crop.png','original-alpha.png','sam-mask.png','mask-disagreement.png','prompt-crop.png')){
  $inputs+= ,@("panzer-sam-probe-20261026\$name\$image","$name-$image")
 }
}
$copied=0
foreach($entry in $inputs){
 $source=Join-Path $src $entry[0]
 $dest=Join-Path $dst $entry[1]
 if(-not(Test-Path -LiteralPath $source)){throw "Missing evidence source: $source"}
 $a=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
 if(Test-Path -LiteralPath $dest){
  $b=(Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash
  if($a -ne $b){throw "Existing different evidence, refusing overwrite: $dest"}
 }else{
  Copy-Item -LiteralPath $source -Destination $dest -ErrorAction Stop
  $b=(Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash
  if($a -ne $b){throw "Hash readback failed: $dest"}
 }
 $copied++
}
Write-Output ('DRIVE_EVIDENCE_VERIFIED='+$copied)
Write-Output ('DRIVE_DESTINATION='+$dst)
Write-Output 'SOURCE_IMAGES_UNCHANGED=1'
Write-Output 'VISUAL_REVIEW=REQUIRED'
