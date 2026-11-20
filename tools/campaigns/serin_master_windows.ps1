param(
 [ValidateSet('start','work','status')][string]$Verb='status'
)
$ErrorActionPreference='Stop'
$SourceId='SERIN_ASMR_HR_003'
$MasterId='SERIN_ASMR_HR_003_MASTER_V1'
$SourceSha='8D2A5A5AE5A750993233E7859C076B928433B3A93FFFD83AB00F39D9BFB099F1'
$ExpectedVoice='B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5'
$Root=Join-Path $env:LOCALAPPDATA 'RitsuASMR\runs'
$SrcDir=Join-Path $Root $SourceId
$DstDir=Join-Path $Root $MasterId
$Src=Join-Path $SrcDir ($SourceId+'.wav')
$Dst=Join-Path $DstDir ($MasterId+'.wav')
$Status=Join-Path $DstDir 'status.json'
$Receipt=Join-Path $DstDir 'receipt.json'
$Task='RitsuASMR-Master-'+$MasterId
$Pitch=0.8908987181403393
$Tempo=0.98
function Save-Json([string]$Path,[object]$Data){
 $tmp=$Path+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
 $json=$Data|ConvertTo-Json -Depth 12
 [IO.File]::WriteAllText($tmp,$json,[Text.UTF8Encoding]::new($false))
 Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Read-Json([string]$Path){
 if(!(Test-Path -LiteralPath $Path)){throw "MISSING_RECEIPT: $Path"}
 return Get-Content -LiteralPath $Path -Raw -Encoding UTF8|ConvertFrom-Json
}
function Hash([string]$Path){return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()}
function Check-Source{
 if(!(Test-Path -LiteralPath $Src -PathType Leaf)){throw 'SOURCE_WAV_MISSING'}
 if((Hash $Src) -cne $SourceSha){throw 'SOURCE_WAV_HASH_MISMATCH'}
 $r=Read-Json (Join-Path $SrcDir 'receipt.json')
 if($r.phase -cne 'rendered_not_delivered' -or
    $r.episodeId -cne $SourceId -or
    $r.profile -cne 'whisper' -or
    $r.voiceSha256.ToUpperInvariant() -cne $ExpectedVoice -or
    $r.wavSha256.ToUpperInvariant() -cne $SourceSha -or
    [long]$r.bytes -ne (Get-Item -LiteralPath $Src).Length){
  throw 'SOURCE_RENDER_RECEIPT_MISMATCH'
 }
}
function Check-Wav([string]$Path){
 $f=[IO.File]::OpenRead($Path)
 try{
  $reader=[IO.BinaryReader]::new($f)
  if([Text.Encoding]::ASCII.GetString($reader.ReadBytes(4)) -cne 'RIFF'){throw 'WAV_RIFF_MISSING'}
  [void]$reader.ReadUInt32()
  if([Text.Encoding]::ASCII.GetString($reader.ReadBytes(4)) -cne 'WAVE'){throw 'WAV_HEADER_MISSING'}
  $format=$null;$dataBytes=0
  while($f.Position+8 -le $f.Length){
   $type=[Text.Encoding]::ASCII.GetString($reader.ReadBytes(4))
   $size=[long]$reader.ReadUInt32();$start=$f.Position
   if($size -gt $f.Length-$start){throw 'WAV_CHUNK_OVERFLOW'}
   if($type -ceq 'fmt '){
    if($size -lt 16){throw 'WAV_FMT_SHORT'}
    $format=@{codec=$reader.ReadUInt16();channels=$reader.ReadUInt16();rate=$reader.ReadUInt32();bps=0}
    [void]$reader.ReadUInt32();[void]$reader.ReadUInt16()
    $format.bps=$reader.ReadUInt16()
   }
   if($type -ceq 'data'){$dataBytes+=$size}
   $f.Position=$start+$size+($size%2)
  }
  if(!$format -or $format.codec -ne 1 -or $format.channels -ne 1 -or $format.rate -ne 24000 -or $format.bps -ne 16 -or $dataBytes -le 0 -or $dataBytes%2){throw 'WAV_PCM_FORMAT_MISMATCH'}
  return [math]::Round($dataBytes/48000.0,3)
 }finally{$f.Dispose()}
}
function Ffmpeg-Path{
 $cmd=Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
 if(!$cmd){throw 'FFMPEG_NOT_FOUND_NO_SUBSTITUTION'}
 return $cmd.Source
}
function Check-Rubberband([string]$Exe){
 $filters=& $Exe -hide_banner -filters 2>&1
 if($LASTEXITCODE -ne 0 -or !($filters -match '\brubberband\b')){throw 'FFMPEG_RUBBERBAND_FILTER_MISSING_NO_SUBSTITUTION'}
}
function Report{
 if(!(Test-Path -LiteralPath $Status)){return @{phase='not_started';episodeId=$MasterId;sourceId=$SourceId}}
 $s=Read-Json $Status
 $t=Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue
 $s|Add-Member -NotePropertyName taskState -NotePropertyValue $(if($t){[string]$t.State}else{'Missing'}) -Force
 if($s.phase -eq 'mastering' -and (!$t -or $t.State -ne 'Running')){
  $s|Add-Member -NotePropertyName observation -NotePropertyValue 'worker_not_confirmed; inspect log and task, do not restart blindly' -Force
 }
 return $s
}
if($Verb -eq 'status'){Report|ConvertTo-Json -Compress -Depth 12;exit 0}
if($Verb -eq 'start'){
 Check-Source
 [void](Check-Wav $Src)
 $exe=Ffmpeg-Path
 Check-Rubberband $exe
 if(Test-Path -LiteralPath $Dst){
  if(Test-Path -LiteralPath $Receipt){Report|ConvertTo-Json -Compress -Depth 12;exit 0}
  throw 'MASTER_OUTPUT_EXISTS_WITHOUT_RECEIPT'
 }
 if(Test-Path -LiteralPath $Status){
  $old=Read-Json $Status
  if($old.phase -in @('scheduled','mastering','mastered_not_delivered','failed')){Report|ConvertTo-Json -Compress -Depth 12;exit 0}
  throw 'PRIOR_CAMPAIGN_STATE_AMBIGUOUS'
 }
 New-Item -ItemType Directory -Force -Path $DstDir|Out-Null
 $self=(Resolve-Path -LiteralPath $PSCommandPath).Path
 $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$self+'" -Verb work')
 $principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
 $settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew
 $existing=Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue
 if($existing){throw 'PRIOR_TASK_EXISTS_REQUIRES_INSPECTION'}
 Save-Json $Status @{phase='scheduled';episodeId=$MasterId;sourceEpisodeId=$SourceId;sourceSha256=$SourceSha;updatedUtc=[DateTime]::UtcNow.ToString('o')}
 try{
  Register-ScheduledTask -TaskName $Task -Action $action -Principal $principal -Settings $settings -Force|Out-Null
  Start-ScheduledTask -TaskName $Task
 }catch{
  $st=Read-Json $Status;$st.phase='dispatch_uncertain';$st.error=$_.Exception.Message;Save-Json $Status $st
  throw
 }
 Report|ConvertTo-Json -Compress -Depth 12;exit 0
}
# Work mode is invoked only by the detached Windows Scheduled Task.
if($Verb -eq 'work'){
 New-Item -ItemType Directory -Force -Path $DstDir|Out-Null
 $tmp=Join-Path $DstDir 'master.partial.wav'
 try{
  Check-Source
  $sourceDuration=Check-Wav $Src
  $exe=Ffmpeg-Path
  Check-Rubberband $exe
  if(Test-Path -LiteralPath $Dst){throw 'MASTER_EXISTS_REFUSE_OVERWRITE'}
  if(Test-Path -LiteralPath $tmp){throw 'PARTIAL_EXISTS_REFUSE_OVERWRITE'}
  Save-Json $Status @{phase='mastering';episodeId=$MasterId;sourceEpisodeId=$SourceId;sourceSha256=$SourceSha;updatedUtc=[DateTime]::UtcNow.ToString('o')}
  $filter='rubberband=pitch='+$Pitch.ToString('0.0000000000000000',[cultureinfo]::InvariantCulture)+':tempo='+$Tempo.ToString('0.00',[cultureinfo]::InvariantCulture)
  $arguments=@('-nostdin','-hide_banner','-loglevel','error','-n','-i',$Src,'-filter:a',$filter,'-ac','1','-ar','24000','-c:a','pcm_s16le',$tmp)
  & $exe @arguments 2>&1|Out-File -FilePath (Join-Path $DstDir 'ffmpeg.log') -Encoding utf8
  if($LASTEXITCODE -ne 0){throw ('FFMPEG_EXIT_'+$LASTEXITCODE)}
  $duration=Check-Wav $tmp
  if($duration -le 0 -or $duration -lt $sourceDuration*0.98 -or $duration -gt $sourceDuration*1.08){throw 'MASTER_DURATION_OUTSIDE_SAFE_BOUND'}
  Move-Item -LiteralPath $tmp -Destination $Dst
  $digest=Hash $Dst
  $size=(Get-Item -LiteralPath $Dst).Length
  $meta=@{phase='mastered_not_delivered';episodeId=$MasterId;sourceEpisodeId=$SourceId;profile='whisper';voiceSha256=$ExpectedVoice;wavPath=$Dst;wavSha256=$digest;bytes=$size;durationSeconds=$duration;sourceDurationSeconds=$sourceDuration;sourceWavSha256=$SourceSha;pitchSemitones=-2;tempo=0.98;filter=$filter;updatedUtc=[DateTime]::UtcNow.ToString('o')}
  Save-Json $Receipt $meta
  Save-Json $Status $meta
 }catch{
  Save-Json $Status @{phase='failed';episodeId=$MasterId;sourceEpisodeId=$SourceId;lastError=$_.Exception.Message;updatedUtc=[DateTime]::UtcNow.ToString('o')}
  throw
 }
}