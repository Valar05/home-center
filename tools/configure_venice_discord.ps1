[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ExpectedPowerShell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$ExpectedPowerShellSha256 = '7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5'
$ExpectedTrustBodySha256 = '47f4390a8a4accbb32b56ccd44aa606151526b5529bf122fecbb3a6e87a6b2c1'
$TrustBody = [IO.Path]::Combine($PSScriptRoot, 'configure_venice_discord_trusted.ps1')
$RepoRoot = [IO.Path]::GetFullPath([IO.Path]::Combine($PSScriptRoot, '..'))

function Get-ByteSha256 {
  param([byte[]]$Bytes)
  $sha = [Security.Cryptography.SHA256]::Create()
  try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
  finally { $sha.Dispose() }
}

function Get-GovernedUtf8Bytes {
  param([string]$Path)
  $raw = [IO.File]::ReadAllBytes($Path)
  $utf8 = [Text.UTF8Encoding]::new($false, $true)
  $text = $utf8.GetString($raw).Replace("`r`n", "`n")
  if ($text.Contains("`r")) { throw 'The governed trust body contains an unsupported carriage return.' }
  return $utf8.GetBytes($text)
}

$powerShellItem = [IO.FileInfo]::new($ExpectedPowerShell)
if (-not $powerShellItem.Exists -or ($powerShellItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
  throw 'The governed PowerShell executable is unavailable.'
}
if ((Get-ByteSha256 ([IO.File]::ReadAllBytes($ExpectedPowerShell))) -ne $ExpectedPowerShellSha256) {
  throw 'The governed PowerShell executable hash changed.'
}
$trustBodyBytes = Get-GovernedUtf8Bytes $TrustBody
if ((Get-ByteSha256 $trustBodyBytes) -ne $ExpectedTrustBodySha256) {
  throw 'The reviewed Venice trust body changed.'
}
$trustBodySource = [Text.Encoding]::UTF8.GetString($trustBodyBytes)
$trustBodyEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($trustBodySource))
$trustBodyBytes = $null
$trustBodySource = $null

$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $ExpectedPowerShell
$startInfo.Arguments = '-NoLogo -NoProfile -ExecutionPolicy Bypass -OutputFormat Text -EncodedCommand ' + $trustBodyEncoded
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardInput = $false
$startInfo.RedirectStandardOutput = $false
$startInfo.RedirectStandardError = $false
$startInfo.CreateNoWindow = $false
$startInfo.EnvironmentVariables.Clear()
$startInfo.EnvironmentVariables['SystemRoot'] = 'C:\Windows'
$startInfo.EnvironmentVariables['WINDIR'] = 'C:\Windows'
$startInfo.EnvironmentVariables['TEMP'] = 'C:\Users\dclar\AppData\Local\Temp'
$startInfo.EnvironmentVariables['TMP'] = 'C:\Users\dclar\AppData\Local\Temp'
$startInfo.EnvironmentVariables['USERPROFILE'] = 'C:\Users\dclar'
$startInfo.EnvironmentVariables['HOMEDRIVE'] = 'C:'
$startInfo.EnvironmentVariables['HOMEPATH'] = '\Users\dclar'
$startInfo.EnvironmentVariables['APPDATA'] = 'C:\Users\dclar\AppData\Roaming'
$startInfo.EnvironmentVariables['LOCALAPPDATA'] = 'C:\Users\dclar\AppData\Local'
$startInfo.EnvironmentVariables['ProgramData'] = 'C:\ProgramData'
$startInfo.EnvironmentVariables['ProgramFiles'] = 'C:\Program Files'
$startInfo.EnvironmentVariables['ProgramFiles(x86)'] = 'C:\Program Files (x86)'
$startInfo.EnvironmentVariables['CommonProgramFiles'] = 'C:\Program Files\Common Files'
$startInfo.EnvironmentVariables['PATHEXT'] = '.COM;.EXE;.BAT;.CMD'
$startInfo.EnvironmentVariables['PATH'] = 'C:\Windows\System32'
$startInfo.EnvironmentVariables['VENICE_REPO_ROOT'] = $RepoRoot

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $startInfo
[void]$process.Start()
$process.WaitForExit()
$trustBodyEncoded = $null
if ($process.ExitCode -ne 0) { throw 'The governed Venice configuration process failed.' }
