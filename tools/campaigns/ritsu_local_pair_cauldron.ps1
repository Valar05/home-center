#requires -Version 5.1
<#
THECAULDRON Ritsu Local Link pairing. Run Install once, then open a new
Windows PowerShell and type ritsupair. Does not create or rotate credentials.
#>
[CmdletBinding()]
param(
 [ValidateSet('Install','Show','Status','Doctor','Remove')][string]$Mode='Show',
 [string]$ProfilePath='',
 [string]$TokenFile=''
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ip='100.68.37.106'
$origin='http://100.68.37.106:19646'
$begin='# BEGIN HOME_CENTER_RITSUPAIR_DIRECT_V1'
$end='# END HOME_CENTER_RITSUPAIR_DIRECT_V1'
function Guard([bool]$ok,[string]$code){if(-not $ok){throw ('RITSUPAIR_BLOCKED='+$code)}}
function ManagedFolder {return (Join-Path $env:LOCALAPPDATA 'HomeCenter\RitsuLocalPair')}
function ManagedScript{return (Join-Path (ManagedFolder) 'ritsu_local_pair_cauldron.ps1')}
function ProfileFile{
 if($ProfilePath){return $ProfilePath}
 $docs=[Environment]::GetFolderPath('MyDocuments')
 Guard (-not [string]::IsNullOrWhiteSpace($docs)) 'documents_unavailable'
 return (Join-Path $docs 'WindowsPowerShell\Microsoft.PowerShell_profile.ps1')
}
function AliasBlock {
 return (@'
# BEGIN HOME_CENTER_RITSUPAIR_DIRECT_V1
function global:ritsupair {
  param([ValidateSet('Show','Status','Doctor')][string]$Mode='Show')
  & powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File (Join-Path $env:LOCALAPPDATA 'HomeCenter\RitsuLocalPair\ritsu_local_pair_cauldron.ps1') -Mode $Mode
}
# END HOME_CENTER_RITSUPAIR_DIRECT_V1
'@).Trim()
}
function SaveText([string]$dest,[string]$value){
 New-Item -ItemType Directory -Path (Split-Path $dest -Parent) -Force | Out-Null
 $tmp=$dest+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
 try {
   [IO.File]::WriteAllText($tmp,$value,(New-Object Text.UTF8Encoding($false)))
   Move-Item -LiteralPath $tmp -Destination $dest -Force
 } finally {if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force}}
}
function InstallAlias {
 $profile=ProfileFile; $helper=ManagedScript; $block=AliasBlock
 $current=if(Test-Path -LiteralPath $profile -PathType Leaf){[IO.File]::ReadAllText($profile)}else{''}
 $a=$current.IndexOf($begin,[StringComparison]::Ordinal)
 $b=$current.IndexOf($end,[StringComparison]::Ordinal)
 Guard (($a -ge 0) -eq ($b -ge 0)) 'partial_alias_markers'
 if($a -ge 0){
   $prior=$current.Substring($a,$b+$end.Length-$a).Replace([string][char]13,'')
   Guard ($prior -ceq $block.Replace([string][char]13,'')) 'owned_alias_changed'
   Guard (Test-Path -LiteralPath $helper -PathType Leaf) 'installed_helper_missing'
   Guard ((Get-FileHash $helper -Algorithm SHA256).Hash -eq
          (Get-FileHash $PSCommandPath -Algorithm SHA256).Hash) 'installed_helper_differs'
   Write-Output 'RITSUPAIR_ALIAS=ALREADY_INSTALLED'
   return
 }
 Guard (-not [regex]::IsMatch($current,'(?im)^\s*(function\s+(?:global:)?ritsupair\b|(?:New|Set)-Alias\s+(?:-Name\s+)?ritsupair\b)')) 'existing_foreign_alias'
 if(Test-Path -LiteralPath $helper -PathType Leaf){
   Guard ((Get-FileHash $helper -Algorithm SHA256).Hash -eq
          (Get-FileHash $PSCommandPath -Algorithm SHA256).Hash) 'existing_helper_preserved'
 }else{
   New-Item -ItemType Directory -Path (ManagedFolder) -Force|Out-Null
   Copy-Item -LiteralPath $PSCommandPath -Destination $helper -ErrorAction Stop
 }
 Guard ((Get-FileHash $helper -Algorithm SHA256).Hash -eq
        (Get-FileHash $PSCommandPath -Algorithm SHA256).Hash) 'copied_helper_hash_mismatch'
 if($current -and -not $current.EndsWith([string][char]10)){$current+=[Environment]::NewLine}
 if($current){$current+=[Environment]::NewLine}
 SaveText $profile ($current+$block+[Environment]::NewLine)
 Guard ([IO.File]::ReadAllText($profile).Contains($begin)) 'alias_profile_write_failed'
 Write-Output 'RITSUPAIR_ALIAS=INSTALLED'
 Write-Output ('PROFILE='+$profile)
 Write-Output 'NEXT=Open a new Windows PowerShell and type ritsupair'
}
function RemoveAlias {
 $profile=ProfileFile
 if(-not(Test-Path -LiteralPath $profile -PathType Leaf)){Write-Output 'RITSUPAIR_ALIAS=NOT_PRESENT';return}
 $current=[IO.File]::ReadAllText($profile)
 $a=$current.IndexOf($begin,[StringComparison]::Ordinal)
 $b=$current.IndexOf($end,[StringComparison]::Ordinal)
 if($a -lt 0 -and $b -lt 0){Write-Output 'RITSUPAIR_ALIAS=NOT_PRESENT';return}
 Guard ($a -ge 0 -and $b -gt $a) 'partial_alias_markers'
 $prior=$current.Substring($a,$b+$end.Length-$a).Replace([string][char]13,'')
 Guard ($prior -ceq (AliasBlock).Replace([string][char]13,'')) 'edited_alias_refuses_removal'
 SaveText $profile ($current.Substring(0,$a)+$current.Substring($b+$end.Length))
 Write-Output 'RITSUPAIR_ALIAS=REMOVED'
}
function LoadToken {
 $file=if($TokenFile){$TokenFile}else{Join-Path ([Environment]::GetFolderPath('UserProfile')) '.ritsu-control\local-link\device-token'}
 Guard (Test-Path -LiteralPath $file -PathType Leaf) 'existing_local_server_token_missing'
 $entry=Get-Item -LiteralPath $file -Force
 Guard (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'token_symlink_refused'
 Guard ($entry.Length -ge 64 -and $entry.Length -le 68) 'unexpected_token_size'
 $secret=[IO.File]::ReadAllText($entry.FullName,[Text.Encoding]::UTF8).Trim()
 Guard ($secret -cmatch '^[a-f0-9]{64}$') 'unexpected_token_format'
 return $secret
}
function VerifyGateway([string]$token){
 $cmd=Get-Command tailscale.exe -ErrorAction SilentlyContinue
 $exe=if($cmd){$cmd.Source}else{Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'}
 Guard (Test-Path -LiteralPath $exe -PathType Leaf) 'tailscale_not_installed'
 $ips=@(& $exe ip -4 2>$null)
 Guard ($LASTEXITCODE -eq 0) 'tailscale_not_connected'
 Guard (@($ips|Where-Object {$_.Trim() -eq $ip}).Count -eq 1) 'cauldron_tailnet_identity_mismatch'
 $req=[Net.HttpWebRequest][Net.WebRequest]::Create($origin+'/v1/ritsu/status')
 $req.Method='GET';$req.AllowAutoRedirect=$false
 $req.Timeout=6000;$req.ReadWriteTimeout=6000;$req.Proxy=$null
 $req.Headers.Add('Authorization','Bearer '+$token)
 try{
   $res=[Net.HttpWebResponse]$req.GetResponse()
   try{
     Guard ([int]$res.StatusCode -eq 200) 'gateway_http_rejected'
     $reader=New-Object IO.StreamReader($res.GetResponseStream())
     try{$body=$reader.ReadToEnd()}finally{$reader.Dispose()}
     Guard ($body.Length -le 10000) 'gateway_reply_oversized'
     $data=ConvertFrom-Json -InputObject $body
     Guard ($data.ok -eq $true -and $data.transport -eq 'tailscale-sse' -and
            [int]$data.cloudOps -eq 0) 'not_the_expected_local_service'
   }finally{$res.Dispose()}
 }catch{throw 'RITSUPAIR_BLOCKED=local_gateway_unreachable_or_token_rejected'}
}
function ShowPairing([string]$token,[string]$gatewayState){
 Add-Type -AssemblyName System.Windows.Forms
 Add-Type -AssemblyName System.Drawing
 Guard ([Threading.Thread]::CurrentThread.GetApartmentState() -eq
        [Threading.ApartmentState]::STA) 'windows_sta_required'
 $window=New-Object Windows.Forms.Form
 $window.Text='Ritsu Control | THECAULDRON pairing'
 $window.Width=710;$window.Height=310;$window.StartPosition='CenterScreen'
 $window.FormBorderStyle='FixedDialog';$window.MaximizeBox=$false
 $title=New-Object Windows.Forms.Label
 $title.SetBounds(18,16,655,43)
 $title.Text='On your phone: Ritsu Control > More > Pair THECAULDRON.'+
     [Environment]::NewLine+$(if($gatewayState -eq 'VERIFIED'){'Server answered; enter the private address and token.'}else{'Server not responding: token shown for setup, connection is UNVERIFIED.'})
 $window.Controls.Add($title)
 $address=New-Object Windows.Forms.TextBox
 $address.SetBounds(18,77,652,28)
 $address.ReadOnly=$true;$address.Text=$origin
 $window.Controls.Add($address)
 $hint=New-Object Windows.Forms.Label
 $hint.SetBounds(18,124,652,22)
 $hint.Text='Device token (masked until you reveal it locally)'
 $window.Controls.Add($hint)
 $field=New-Object Windows.Forms.TextBox
 $field.SetBounds(18,149,652,28)
 $field.ReadOnly=$true;$field.UseSystemPasswordChar=$true
 $field.Font=New-Object Drawing.Font('Consolas',12)
 $field.Text=$token;$window.Controls.Add($field)
 $reveal=New-Object Windows.Forms.CheckBox
 $reveal.SetBounds(18,195,635,23)
 $reveal.Text='Reveal locally to enter this in my phone'
 $reveal.Add_CheckedChanged({$field.UseSystemPasswordChar=-not $reveal.Checked})
 $window.Controls.Add($reveal)
 $close=New-Object Windows.Forms.Button
 $close.SetBounds(555,233,115,30);$close.Text='Done'
 $close.Add_Click({$window.Close()});$window.Controls.Add($close)
 try{[void]$window.ShowDialog()}finally{$field.Text='';$window.Dispose()}
}
switch($Mode){
 'Doctor'{
   Write-Output 'RITSUPAIR_DOCTOR=PASS'
   Write-Output ('DIRECT_ENDPOINT='+$origin)
   Write-Output ('TOKEN_FILE_PRESENT='+[bool](Test-Path (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.ritsu-control\local-link\device-token')))
   Write-Output 'SECRET_EXPOSED=NO'
 }
 'Install'{InstallAlias}
 'Remove'{RemoveAlias}
 'Status'{
   $secret=LoadToken;VerifyGateway $secret;$secret=$null
   Write-Output 'RITSU_LOCAL_LINK=VERIFIED'
   Write-Output ('DIRECT_ENDPOINT='+$origin)
   Write-Output 'PHONE_PAIRED=NOT_ESTABLISHED_BY_SERVER_STATUS'
 }
 'Show'{
   $secret=LoadToken
   $gateway='VERIFIED'
   try{VerifyGateway $secret}catch{$gateway='UNAVAILABLE'}
   ShowPairing $secret $gateway;$secret=$null
   Write-Output ('RITSUPAIR_GATEWAY='+$gateway)
   Write-Output 'RITSUPAIR_DIALOG=CLOSED'
   Write-Output 'PHONE_PAIRED=REQUIRES_ANDROID_CONFIRMATION'
 }
}
