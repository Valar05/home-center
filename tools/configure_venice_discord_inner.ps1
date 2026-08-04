[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ExpectedNode = 'C:\Program Files\nodejs\node.exe'
$ExpectedEndpoint = 'https://us-central1-home-center-dclar.cloudfunctions.net/veniceDiscordInteractions'
$ExpectedNodeSourceSha256 = $env:VENICE_NODE_SOURCE_SHA256
$token = $null
$secureToken = $null

if ($env:VENICE_TRUSTED_ONE_SHOT_LAUNCHER -ne '1') {
  throw 'Use tools/configure_venice_discord.ps1 to start the short-lived token process.'
}
if ($env:VENICE_TRUSTED_NODE -ne $ExpectedNode -or -not $env:VENICE_NODE_SOURCE_BASE64) {
  throw 'The one-shot launcher did not provide the governed Node runtime and source.'
}
if (-not $env:VENICE_DISCORD_CONTRACT_BASE64 -or -not $env:VENICE_DISCORD_CONTRACT_SHA256) {
  throw 'The one-shot launcher did not provide the governed Discord contract.'
}
$nodeItem = Microsoft.PowerShell.Management\Get-Item -LiteralPath $ExpectedNode -ErrorAction Stop
if ($nodeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'The governed Node runtime is a reparse point.' }
$nodeHash = (Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $ExpectedNode -Algorithm SHA256).Hash.ToLowerInvariant()
if ($nodeHash -ne $env:VENICE_TRUSTED_NODE_SHA256) { throw 'The governed Node runtime hash changed.' }
$nodeBytes = [Convert]::FromBase64String($env:VENICE_NODE_SOURCE_BASE64)
$sha = [Security.Cryptography.SHA256]::Create()
try { $nodeSourceHash = ([BitConverter]::ToString($sha.ComputeHash($nodeBytes))).Replace('-', '').ToLowerInvariant() }
finally { $sha.Dispose() }
if ($nodeSourceHash -ne $ExpectedNodeSourceSha256) { throw 'The governed Node source hash changed.' }
$nodeBytes = $null

function Quote-ProcessArgument {
  param([string]$Value)
  if ($Value.Contains('"')) { throw 'Unexpected quote in a trusted process argument.' }
  return '"' + $Value + '"'
}

try {
  $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
  $startInfo.FileName = $ExpectedNode
  $nodeBootstrap = "await import('data:text/javascript;base64,'+process.env.VENICE_NODE_SOURCE_BASE64)"
  $startInfo.Arguments = (@('--input-type=module', '--eval', $nodeBootstrap, '--', '--endpoint', $ExpectedEndpoint) | ForEach-Object {
    Quote-ProcessArgument ([string]$_)
  }) -join ' '
  $startInfo.UseShellExecute = $false
  $startInfo.RedirectStandardInput = $true
  $startInfo.RedirectStandardOutput = $true
  $startInfo.RedirectStandardError = $true
  $startInfo.CreateNoWindow = $true
  $startInfo.EnvironmentVariables.Clear()
  foreach ($name in @('SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'ProgramFiles', 'PATHEXT')) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ($value) { $startInfo.EnvironmentVariables[$name] = $value }
  }
  $startInfo.EnvironmentVariables['PATH'] = (Split-Path -Parent $ExpectedNode)
  $startInfo.EnvironmentVariables['VENICE_TRUSTED_ONE_SHOT_NODE'] = '1'
  $startInfo.EnvironmentVariables['VENICE_TRUSTED_NODE'] = $ExpectedNode
  $startInfo.EnvironmentVariables['VENICE_TRUSTED_NODE_SHA256'] = $nodeHash
  $startInfo.EnvironmentVariables['VENICE_NODE_SOURCE_BASE64'] = $env:VENICE_NODE_SOURCE_BASE64
  $startInfo.EnvironmentVariables['VENICE_DISCORD_CONTRACT_BASE64'] = $env:VENICE_DISCORD_CONTRACT_BASE64
  $startInfo.EnvironmentVariables['VENICE_DISCORD_CONTRACT_SHA256'] = $env:VENICE_DISCORD_CONTRACT_SHA256

  $process = [System.Diagnostics.Process]::new()
  $process.StartInfo = $startInfo
  [void]$process.Start()
  $ready = $process.StandardOutput.ReadLine()
  if ($ready -ne 'VENICE_ONE_SHOT_READY') {
    $startupError = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($startupError) { [Console]::Error.Write($startupError) }
    throw 'The governed Discord configurator did not become ready.'
  }

  $secureToken = Read-Host -AsSecureString -Prompt 'Drew: paste the newly reset Discord bot token once; the clipboard will be cleared immediately and token rotation remains required'
  try {
    Microsoft.PowerShell.Management\Set-Clipboard -Value ''
  }
  catch {
    throw 'The launcher could not clear the clipboard, so the token was not used. Clear the clipboard and retry.'
  }
  $tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
  try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer) }
  if ($token.Length -lt 30 -or $token.Length -gt 200 -or $token -notmatch '^[A-Za-z0-9._-]+$') {
    throw 'The concealed value is not a Discord bot token.'
  }

  $process.StandardInput.Write($token)
  $process.StandardInput.Close()
  $token = $null
  $standardOutput = $process.StandardOutput.ReadToEnd()
  $standardError = $process.StandardError.ReadToEnd()
  $process.WaitForExit()
  if ($process.ExitCode -ne 0) {
    if ($standardError) { [Console]::Error.Write($standardError) }
    throw 'Discord rejected the one-shot Venice configuration.'
  }
  [Console]::Out.Write($standardOutput)
}
finally {
  $token = $null
  if ($secureToken) { $secureToken.Dispose() }
  $secureToken = $null
}
