#Requires -Version 5.1
<#
CAULDRON STORAGE AUDIT / GUARDED CLEANUP
Default Audit is read-only. Use CleanCaches only after reviewing audit report.
PocketTTS / voice profiles / Hugging Face models / Ollama models / source projects protected.
#>
[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
param(
 [ValidateSet('Audit','CleanCaches')][string]$Mode='Audit',
 [switch]$RemoveChatterboxVenv,
 [int]$TempMinimumAgeDays=14
)
$ErrorActionPreference='Continue'
$ProgressPreference='SilentlyContinue'
$homePath=[Environment]::GetFolderPath('UserProfile')
$local=[Environment]::GetFolderPath('LocalApplicationData')
$documents=[Environment]::GetFolderPath('MyDocuments')
$work=Join-Path $documents 'CauldronStorageAudits'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$logPath=Join-Path $work "cauldron-storage-$stamp.log"
$csvPath=Join-Path $work "cauldron-storage-$stamp.csv"
$script:rows=New-Object 'System.Collections.Generic.List[object]'
$script:messages=New-Object 'System.Collections.Generic.List[string]'
function Say([string]$msg) {
 $line=(Get-Date -Format 'HH:mm:ss')+' '+$msg
 Write-Output $line
 $script:messages.Add($line)|Out-Null
}
function TotalSize([string]$path) {
 if(-not(Test-Path -LiteralPath $path)){return [long]0}
 $sum=[long]0
 try {
  $obj=Get-Item -LiteralPath $path -Force -ErrorAction Stop
  if(-not $obj.PSIsContainer){return [long]$obj.Length}
  $stack=New-Object 'System.Collections.Generic.Stack[string]'
  $stack.Push($path)
  while($stack.Count -gt 0) {
   $dir=$stack.Pop()
   try {
    foreach($item in (Get-ChildItem -LiteralPath $dir -Force -ErrorAction SilentlyContinue)) {
     if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){continue}
     if($item.PSIsContainer){$stack.Push($item.FullName)}else{$sum += [long]$item.Length}
    }
   }catch{}
  }
 }catch{}
 return $sum
}
function Record([string]$category,[string]$path,[string]$policy,[string]$note='') {
 $present=Test-Path -LiteralPath $path
 $bytes=if($present){TotalSize $path}else{[long]0}
 $script:rows.Add([pscustomobject]@{Category=$category;GiB=[math]::Round($bytes/1GB,3);Bytes=$bytes;Exists=[bool]$present;Policy=$policy;Path=$path;Note=$note})|Out-Null
}
function RemoveGuarded([string]$path,[string]$label) {
 if(-not(Test-Path -LiteralPath $path)){Say "SKIP missing: $label";return}
 $full=[IO.Path]::GetFullPath($path).TrimEnd('\')
 $protected=@(
  (Join-Path $documents 'Codex\Venice\PocketTTS'),
  (Join-Path $homePath '.ollama\models'),
  (Join-Path $homePath '.cache\huggingface'),
  (Join-Path $homePath 'workspace'),
  (Join-Path $homePath 'Documents')
 )
 foreach($p in $protected){
  $p=[IO.Path]::GetFullPath($p).TrimEnd('\')
  if($full -ieq $p -or $full.StartsWith($p+'\\',[StringComparison]::OrdinalIgnoreCase)){
   $allowedChatterVenv=@(
    (Join-Path $homePath 'workspace\\ritsu-chatterbox-turbo\\.venv'),
    (Join-Path $homePath 'workspace\\ritsu-chatterbox-turbo\\venv')
   )
   if(-not (@($allowedChatterVenv|Where-Object{$full -ieq [IO.Path]::GetFullPath($_).TrimEnd('\\')}).Count -gt 0)){
    throw "REFUSING protected path: $full"
   }
  }
 }
 if($PSCmdlet.ShouldProcess($full,"Delete $label")){
  try{Remove-Item -LiteralPath $full -Force -Recurse -ErrorAction Stop;Say "REMOVED: $label ($full)"}
  catch{Say "FAILED: $label : $($_.Exception.Message)"}
 }
}
Say 'CAULDRON STORAGE REPORT; audit is read-only unless -Mode CleanCaches.'
Say "Host=$env:COMPUTERNAME; User=$env:USERNAME; Mode=$Mode; RemoveChatterboxVenv=$RemoveChatterboxVenv"
Say "Reports: $logPath"
Get-CimInstance Win32_LogicalDisk -Filter 'DriveType = 3' -ErrorAction SilentlyContinue|ForEach-Object {
 Say ("DRIVE {0} | free {1:N2} GiB | total {2:N2} GiB | used {3:N1}%" -f $_.DeviceID,($_.FreeSpace/1GB),($_.Size/1GB),(100*(1-$_.FreeSpace/$_.Size)))
}
$specs=@(
 @('cache','pip',(Join-Path $local 'pip\Cache'),'CLEANABLE','Download/build cache'),
 @('cache','whisper',(Join-Path $homePath '.cache\whisper'),'MANUAL','Speech recognition model'),
 @('cache','huggingface',(Join-Path $homePath '.cache\huggingface'),'PROTECTED','May hold Pocket TTS models'),
 @('cache','puppeteer',(Join-Path $homePath '.cache\puppeteer'),'MANUAL','Browser binary cache'),
 @('cache','codex-runtimes',(Join-Path $homePath '.cache\codex-runtimes'),'MANUAL','Developer tooling'),
 @('cache','firebase',(Join-Path $homePath '.cache\firebase'),'MANUAL','Developer tooling'),
 @('cache','home-center',(Join-Path $homePath '.cache\home-center'),'MANUAL','Home Center tools'),
 @('models','ollama',(Join-Path $homePath '.ollama\models'),'PROTECTED','LLM models are not TTS models'),
 @('voice','PocketTTS',(Join-Path $documents 'Codex\Venice\PocketTTS'),'PROTECTED','Preserve decoder patch and profiles'),
 @('voice','Chatterbox workspace',(Join-Path $homePath 'workspace\ritsu-chatterbox-turbo'),'MANUAL','Potential retired TTS, inspect'),
 @('voice','Venice old',(Join-Path $documents 'Codex\Venice\venice-vbp-01a-20260811'),'MANUAL','Inspect'),
 @('temp','user TEMP',[IO.Path]::GetTempPath().TrimEnd('\'),'AGE-GATED','Only old items'),
 @('storage','Downloads',(Join-Path $homePath 'Downloads'),'MANUAL','User files'),
 @('storage','Desktop',(Join-Path $homePath 'Desktop'),'MANUAL','User files')
)
Say 'SCANNING...'
foreach($spec in $specs){Record $spec[0] $spec[2] $spec[3] ($spec[1]+': '+$spec[4])}
$hfHub=Join-Path $homePath '.cache\huggingface\hub'
if(Test-Path -LiteralPath $hfHub){
 foreach($folder in (Get-ChildItem -LiteralPath $hfHub -Force -Directory -ErrorAction SilentlyContinue)){
  if($folder.Name -like 'models--*' -or $folder.Name -like 'datasets--*'){
   Record 'hf-repository' $folder.FullName 'MANUAL' 'Do not delete shared caches automatically'
  }
 }
}
Say 'OLLAMA MODEL INVENTORY'
if(Get-Command ollama -ErrorAction SilentlyContinue){
 try{(& ollama list 2>&1)|ForEach-Object{Say "OLLAMA: $_"}}catch{}
}
Say 'RELEVANT PROCESS INVENTORY'
Get-Process -ErrorAction SilentlyContinue|Where-Object{$_.ProcessName -match 'python|ollama|pocket|chatterbox|comfy|ffmpeg|uvicorn|node'}|Select-Object -First 35|ForEach-Object{Say "PROC: $($_.ProcessName) PID=$($_.Id)"}
$chatter=Join-Path $homePath 'workspace\ritsu-chatterbox-turbo'
if(Test-Path -LiteralPath $chatter){
 foreach($sub in (Get-ChildItem -LiteralPath $chatter -Force -Directory -ErrorAction SilentlyContinue)){
  Record 'chatterbox-subdir' $sub.FullName 'MANUAL' 'Only .venv or venv may be optionally removed'
 }
}
Say 'TOP 25 MEASURED LOCATIONS'
$script:rows|Sort-Object Bytes -Descending|Select-Object -First 25|ForEach-Object{Say ("{0,7:N3} GiB | {1,-10} | {2} | {3}" -f $_.GiB,$_.Policy,$_.Category,$_.Path)}
if($Mode -eq 'CleanCaches'){
 Say 'CLEANUP selected: pip cache, stale user TEMP, optionally retired Chatterbox venv.'
 RemoveGuarded (Join-Path $local 'pip\Cache') 'pip build/download cache'
 $cutoff=(Get-Date).AddDays(-[math]::Max(1,$TempMinimumAgeDays))
 $tempPath=[IO.Path]::GetTempPath().TrimEnd('\')
 if(Test-Path -LiteralPath $tempPath){
  foreach($item in (Get-ChildItem -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue)){
   if($item.LastWriteTime -ge $cutoff){continue}
   if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){continue}
   if($PSCmdlet.ShouldProcess($item.FullName,"Delete stale user TEMP item")){
    try{Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction Stop;Say "REMOVED TEMP: $($item.FullName)"}
    catch{Say "TEMP SKIPPED: $($item.FullName): $($_.Exception.Message)"}
   }
  }
 }
 if($RemoveChatterboxVenv){
  $voices=@(Get-Process -ErrorAction SilentlyContinue|Where-Object{$_.ProcessName -match 'python|chatterbox|uvicorn'})
  if($voices.Count -gt 0){Say 'REFUSED Chatterbox venv cleanup: Python/voice processes running'}
  else{foreach($venvName in @('.venv','venv')){RemoveGuarded (Join-Path $chatter $venvName) "retired Chatterbox $venvName"}}
 }
}
$script:rows|Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Say "CSV saved: $csvPath"
Say "LOG saved: $logPath"
$script:messages|Set-Content -LiteralPath $logPath -Encoding UTF8
Say 'Complete. PocketTTS, HF, Ollama, project source protected.'
