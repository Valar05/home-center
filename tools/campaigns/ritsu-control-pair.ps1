#requires -Version 5.1
<#
.SYNOPSIS
  Ritsu Control pairing helper for THECAULDRON. Existing credential only.
.DESCRIPTION
  Read-only, operator-visible pairing helper. It does not create a token,
  change the live gateway, install an APK, or claim the phone has paired.
  Pass -TokenFile or set HOME_CENTER_RITSU_PHONE_CAPABILITY_FILE in this
  PowerShell session; otherwise choose the existing gateway token file.
  Secrets are never printed, put on the clipboard, written to receipts or sent
  anywhere except the already-bound gateway's authenticated health endpoint.
.EXAMPLE
  powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File .\ritsu-control-pair.ps1 -Mode Show -TokenFile C:\private\phone-only-token
.EXAMPLE
  powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File .\ritsu-control-pair.ps1 -Mode Plan
#>
[CmdletBinding()]
param(
  [ValidateSet('Plan','Show','Status','Receipts')][string]$Mode='Show',
  [string]$TokenFile=$env:HOME_CENTER_RITSU_PHONE_CAPABILITY_FILE,
  [string]$TailnetHost='100.68.37.106'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$origin = 'http://' + $TailnetHost + ':19646'
$receiptDir = Join-Path $env:LOCALAPPDATA 'HomeCenter\RitsuControlPairing'
$script:phase='preflight'
$script:failure='pairing_helper_failed'

function Write-Receipt([string]$state,[string]$detail){
  New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null
  $row = [ordered]@{schema=1;atUtc=[DateTime]::UtcNow.ToString('o');mode=$Mode;state=$state;detail=$detail;
                   endpoint=$origin;credentialEmitted=$false;pairingVerifiedOnPhone=$false}
  $line=ConvertTo-Json -InputObject $row -Compress
  [IO.File]::AppendAllText((Join-Path $receiptDir 'history.jsonl'),$line+[Environment]::NewLine)
  $tmp=Join-Path $receiptDir ([guid]::NewGuid().ToString('N')+'.tmp')
  try {[IO.File]::WriteAllText($tmp,$line);Move-Item -LiteralPath $tmp -Destination (Join-Path $receiptDir 'latest.json') -Force}
  finally {if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force}}
  Write-Output ('RITSU_PAIR '+$state+' '+$detail)
}
function Require([bool]$condition,[string]$code){if(-not $condition){$script:failure=$code;throw 'PAIRING_GATE'}}
function Valid-TailnetHost([string]$hostIp){
  $segments=$hostIp.Split('.')
  if($segments.Count -ne 4){return $false}
  foreach($x in $segments){if($x -notmatch '^(0|[1-9][0-9]{0,2})$' -or [int]$x -gt 255){return $false}}
  return [int]$segments[0] -eq 100 -and [int]$segments[1] -ge 64 -and [int]$segments[1] -le 127
}
function Select-TokenFile{
  Add-Type -AssemblyName System.Windows.Forms
  $dlg=New-Object System.Windows.Forms.OpenFileDialog
  $dlg.Title='Select the EXISTING Home Center phone-only capability file'
  $dlg.CheckFileExists=$true
  $dlg.Multiselect=$false
  $dlg.Filter='All token files (*.*)|*.*'
  if($dlg.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){
    $script:failure='token_file_not_selected';throw 'PAIRING_GATE'
  }
  return $dlg.FileName
}
function Read-ExistingToken([string]$file){
  Require (-not [string]::IsNullOrWhiteSpace($file)) 'token_file_path_required'
  Require (Test-Path -LiteralPath $file -PathType Leaf) 'existing_token_file_not_found'
  $info=Get-Item -LiteralPath $file -Force
  Require (-not (($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) 'token_file_symlink_refused'
  Require ($info.Length -gt 39 -and $info.Length -le 512) 'token_file_size_invalid'
  $token=([IO.File]::ReadAllText($info.FullName,[Text.Encoding]::UTF8)).Trim()
  Require ($token -cmatch '^[A-Za-z0-9_\-=+/]{40,256}$') 'phone_token_format_invalid'
  return $token
}
function Confirm-Gateway([string]$token){
  # The address must match the local host's Tailscale identity. Never send
  # phone credentials to an arbitrary address, even on the tailnet.
  $tailscale=Get-Command tailscale -ErrorAction SilentlyContinue
  if($null -eq $tailscale){
    $tailscalePath='C:\Program Files\Tailscale\tailscale.exe'
    Require (Test-Path -LiteralPath $tailscalePath -PathType Leaf) 'tailscale_cli_unavailable'
  } else {$tailscalePath=$tailscale.Source}
  $ips=@(& $tailscalePath ip -4 2>$null)
  Require ($LASTEXITCODE -eq 0 -and @($ips | Where-Object { $_.Trim() -eq $TailnetHost }).Count -eq 1) 'gateway_host_is_not_local_tailnet_ip'
  $request=[Net.HttpWebRequest][Net.WebRequest]::Create($origin+'/v1/ritsu/health')
  $request.Method='GET';$request.AllowAutoRedirect=$false;$request.Timeout=6000
  $request.ReadWriteTimeout=6000;$request.Proxy=$null
  $request.Headers.Add('Authorization','Bearer '+$token)
  try {
    $response=[Net.HttpWebResponse]$request.GetResponse()
    try {
      Require ([int]$response.StatusCode -eq 200) 'gateway_authentication_failed'
      $reader=New-Object IO.StreamReader($response.GetResponseStream(),[Text.Encoding]::UTF8)
      try {$body=$reader.ReadToEnd()} finally {$reader.Dispose()}
      Require ($body.Length -le 10000) 'gateway_reply_oversized'
      $json=ConvertFrom-Json -InputObject $body
      Require ($json.ok -eq $true -and $json.service -eq 'home-center-ritsu-gateway') 'wrong_gateway_service'
    } finally {$response.Dispose()}
  } catch {
    if($script:failure -eq 'pairing_helper_failed'){$script:failure='gateway_authentication_or_network_unavailable'}
    throw 'PAIRING_GATE'
  }
}
function Show-PairingDialog([string]$token){
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing
  Require ([Threading.Thread]::CurrentThread.GetApartmentState() -eq [Threading.ApartmentState]::STA) 'run_powershell_with_STA'
  $form=New-Object Windows.Forms.Form
  $form.Text='Ritsu Control | Local Pairing'
  $form.Width=720;$form.Height=335;$form.StartPosition='CenterScreen'
  $form.FormBorderStyle='FixedDialog';$form.MaximizeBox=$false;$form.MinimizeBox=$false
  $head=New-Object Windows.Forms.Label
  $head.Left=20;$head.Top=18;$head.Width=650;$head.Height=48
  $head.Text='On Android: Ritsu Control -> More -> Connect Home Center (Tailscale)'+[Environment]::NewLine+'The token below is phone-only. Do not paste it into ChatGPT or a log.'
  $form.Controls.Add($head)
  $label=New-Object Windows.Forms.Label
  $label.Text='Home Center address';$label.Left=20;$label.Top=83;$label.Width=290
  $form.Controls.Add($label)
  $url=New-Object Windows.Forms.TextBox
  $url.Left=20;$url.Top=106;$url.Width=658;$url.ReadOnly=$true;$url.Text=$origin
  $form.Controls.Add($url)
  $secretLabel=New-Object Windows.Forms.Label
  $secretLabel.Text='Separate phone pairing token';$secretLabel.Left=20;$secretLabel.Top=147;$secretLabel.Width=330
  $form.Controls.Add($secretLabel)
  $secret=New-Object Windows.Forms.TextBox
  $secret.Left=20;$secret.Top=172;$secret.Width=658;$secret.Height=26
  $secret.ReadOnly=$true;$secret.UseSystemPasswordChar=$true
  $secret.Font=New-Object System.Drawing.Font -ArgumentList 'Consolas',13
  $secret.Text=$token
  $form.Controls.Add($secret)
  $reveal=New-Object Windows.Forms.CheckBox
  $reveal.Left=20;$reveal.Top=208;$reveal.Width=550
  $reveal.Text='Reveal locally so I can enter it in the phone app'
  $reveal.Add_CheckedChanged({$secret.UseSystemPasswordChar=-not $reveal.Checked})
  $form.Controls.Add($reveal)
  $note=New-Object Windows.Forms.Label
  $note.Left=20;$note.Top=239;$note.Width=660;$note.Height=26
  $note.Text='This helper only verifies the gateway credential. Pairing remains unverified until the Android app connects.'
  $form.Controls.Add($note)
  $close=New-Object Windows.Forms.Button
  $close.Left=578;$close.Top=268;$close.Width=100;$close.Text='Done'
  $close.Add_Click({$form.Close()})
  $form.Controls.Add($close)
  try {[void]$form.ShowDialog()}finally{$secret.Text='';$form.Dispose()}
}
try {
  Require (Valid-TailnetHost $TailnetHost) 'invalid_private_tailnet_host'
  if($Mode -eq 'Plan'){
    Write-Output ('RITSU_PAIR PLAN: verified existing phone-only token; authenticated read-only gateway health; local masked display. Endpoint '+$origin)
    Write-Output 'No token rotation, no gateway restart, no APK installation, no automatic phone pairing.'
    Write-Output 'Use -Mode Show on THECAULDRON desktop. Optional -TokenFile specifies the existing gateway token file.'
    exit 0
  }
  if($Mode -eq 'Receipts'){
    $history=Join-Path $receiptDir 'history.jsonl'
    if(Test-Path -LiteralPath $history){Get-Content -LiteralPath $history -Tail 15}
    else {Write-Output 'RITSU_PAIR NO_RECEIPTS'}
    exit 0
  }
  if([string]::IsNullOrWhiteSpace($TokenFile) -and $Mode -eq 'Show'){
    $TokenFile=Select-TokenFile
  }
  $token=Read-ExistingToken $TokenFile
  Confirm-Gateway $token
  if($Mode -eq 'Show'){
    $script:phase='local_display'
    Show-PairingDialog $token
    Write-Receipt 'gateway_verified' 'local_pairing_dialog_closed_phone_pairing_not_verified'
  }else{
    Write-Receipt 'gateway_verified' 'phone_credential_authorized_gateway_responded_phone_pairing_not_verified'
  }
  $token=$null
}catch{
  Write-Receipt 'blocked' $script:failure
  exit 1
}
