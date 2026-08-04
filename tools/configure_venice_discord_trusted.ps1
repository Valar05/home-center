[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ExpectedOrigin = 'https://github.com/Valar05/home-center.git'
$ExpectedGit = 'C:\Program Files\Git\mingw64\bin\git.exe'
$ExpectedGitSha256 = 'fe0e064c8283dc50b1ce11a8b90d2ec1b68b5dc714ff0b8a8534bb9c43d1d02e'
$ExpectedCredentialManager = 'C:\Program Files\Git\mingw64\bin\git-credential-manager.exe'
$ExpectedCredentialManagerSha256 = '4f8409fac2ee580ac525611a09314775a6b18639251dd3de8f66b5bf8dcb6f6a'
$ExpectedRemoteHttps = 'C:\Program Files\Git\mingw64\libexec\git-core\git-remote-https.exe'
$ExpectedRemoteHttpsSha256 = '88c65fdef1a1e6d61eb597c1d2efee3696739634f5029d1c17fccddfadd564d2'
$ExpectedPowerShell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$ExpectedPowerShellSha256 = '7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5'
$ExpectedNode = 'C:\Program Files\nodejs\node.exe'
$ExpectedNodeSha256 = '77bdff912b1c569b3e693fe126f619337c3e9d73dafbc4d0bf1d4f1f6a145761'
$ExpectedInnerSha256 = '0fa1a0d95b3ffc8bcb53f35a522cc273c0fc4384cafc8f2577f3e79fd406355b'
$ExpectedNodeSourceSha256 = '5645117ae1f4be629f954d42574ff9929a00b34f7156dc26b0daafd49b0b9762'
$ExpectedDiscordContractSha256 = '14a6e709c0dd2d17b0841c572b3069b5f663e807e26d11f4a4dcbd96ee073629'

$currentExecutable = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
if (-not [IO.Path]::GetFullPath($currentExecutable).Equals($ExpectedPowerShell, [StringComparison]::OrdinalIgnoreCase)) {
  throw 'The trust body is not running under the governed PowerShell executable.'
}
if (-not $env:VENICE_REPO_ROOT) { throw 'The governed repository root was not supplied.' }
$RepoRoot = [IO.Path]::GetFullPath($env:VENICE_REPO_ROOT)
$ToolsRoot = [IO.Path]::Combine($RepoRoot, 'tools')
$InnerScript = [IO.Path]::Combine($ToolsRoot, 'configure_venice_discord_inner.ps1')
$NodeScript = [IO.Path]::Combine($ToolsRoot, 'configure_venice_discord.mjs')
$DiscordContract = [IO.Path]::Combine($RepoRoot, 'functions', 'venice_discord_contract.json')

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
  if ($text.Contains("`r")) { throw "Governed source contains an unsupported carriage return: $Path" }
  return $utf8.GetBytes($text)
}

function Assert-TrustedRuntimeFile {
  param([string]$Path, [string]$Sha256)
  $item = [IO.FileInfo]::new($Path)
  if (-not $item.Exists) { throw "Required governed file is missing: $Path" }
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Trusted runtime file is a reparse point: $Path" }
  $actual = Get-ByteSha256 ([IO.File]::ReadAllBytes($Path))
  if ($actual -ne $Sha256) { throw "Trusted runtime hash does not match the reviewed executable: $Path" }
}

Assert-TrustedRuntimeFile -Path $ExpectedGit -Sha256 $ExpectedGitSha256
Assert-TrustedRuntimeFile -Path $ExpectedCredentialManager -Sha256 $ExpectedCredentialManagerSha256
Assert-TrustedRuntimeFile -Path $ExpectedRemoteHttps -Sha256 $ExpectedRemoteHttpsSha256
Assert-TrustedRuntimeFile -Path $ExpectedPowerShell -Sha256 $ExpectedPowerShellSha256
Assert-TrustedRuntimeFile -Path $ExpectedNode -Sha256 $ExpectedNodeSha256

$innerBytes = Get-GovernedUtf8Bytes $InnerScript
$nodeBytes = Get-GovernedUtf8Bytes $NodeScript
$contractBytes = Get-GovernedUtf8Bytes $DiscordContract
if ((Get-ByteSha256 $innerBytes) -ne $ExpectedInnerSha256) { throw 'The reviewed inner launcher source changed.' }
if ((Get-ByteSha256 $nodeBytes) -ne $ExpectedNodeSourceSha256) { throw 'The reviewed Node configurator source changed.' }
if ((Get-ByteSha256 $contractBytes) -ne $ExpectedDiscordContractSha256) { throw 'The reviewed Discord contract changed.' }

$env:GIT_CONFIG_NOSYSTEM = '1'
$env:GIT_CONFIG_GLOBAL = 'NUL'
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'Never'
$env:PATH = 'C:\Program Files\Git\cmd;C:\Program Files\Git\mingw64\bin;C:\Windows\System32'
$gitLocalTrust = @('-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=NUL')
$head = (& $ExpectedGit @gitLocalTrust -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $head -notmatch '^[0-9a-f]{40}$') { throw 'The local Home Center commit could not be resolved.' }

$gitRemoteTrust = @(
  '-c', 'credential.helper=',
  '-c', 'credential.helper=manager',
  '-c', 'http.sslBackend=schannel',
  '-c', 'http.sslVerify=true',
  '-c', 'http.proxy=',
  '-c', 'https.proxy=',
  '-c', 'http.https://github.com/.sslVerify=true',
  '-c', 'http.https://github.com/.proxy='
)
$remoteLine = (& $ExpectedGit @gitRemoteTrust -C 'C:\Windows\System32' ls-remote --exit-code $ExpectedOrigin refs/heads/main).Trim()
if ($LASTEXITCODE -ne 0 -or $remoteLine -notmatch '^([0-9a-f]{40})\s+refs/heads/main$') {
  throw 'The governed origin/main commit could not be resolved.'
}
if ($head -ne $Matches[1]) { throw 'One-shot Discord configuration requires HEAD to equal current origin/main.' }

$innerSource = [Text.Encoding]::UTF8.GetString($innerBytes)
$innerEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($innerSource))
$nodeSourceBase64 = [Convert]::ToBase64String($nodeBytes)
$discordContractBase64 = [Convert]::ToBase64String($contractBytes)
$innerBytes = $null
$nodeBytes = $null
$contractBytes = $null
$innerSource = $null

$arguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-OutputFormat', 'Text', '-EncodedCommand', $innerEncoded)
$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $ExpectedPowerShell
$startInfo.Arguments = $arguments -join ' '
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardInput = $false
$startInfo.RedirectStandardOutput = $false
$startInfo.RedirectStandardError = $false
$startInfo.CreateNoWindow = $false
$startInfo.EnvironmentVariables.Clear()
foreach ($name in @(
  'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH',
  'APPDATA', 'LOCALAPPDATA', 'ProgramData', 'ProgramFiles', 'ProgramFiles(x86)',
  'CommonProgramFiles', 'PATHEXT'
)) {
  $value = [Environment]::GetEnvironmentVariable($name)
  if ($value) { $startInfo.EnvironmentVariables[$name] = $value }
}
$startInfo.EnvironmentVariables['PATH'] = (([IO.Path]::GetDirectoryName($ExpectedNode)), 'C:\Windows\System32' -join ';')
$startInfo.EnvironmentVariables['VENICE_TRUSTED_ONE_SHOT_LAUNCHER'] = '1'
$startInfo.EnvironmentVariables['VENICE_TRUSTED_NODE'] = $ExpectedNode
$startInfo.EnvironmentVariables['VENICE_TRUSTED_NODE_SHA256'] = $ExpectedNodeSha256
$startInfo.EnvironmentVariables['VENICE_NODE_SOURCE_BASE64'] = $nodeSourceBase64
$startInfo.EnvironmentVariables['VENICE_NODE_SOURCE_SHA256'] = $ExpectedNodeSourceSha256
$startInfo.EnvironmentVariables['VENICE_DISCORD_CONTRACT_BASE64'] = $discordContractBase64
$startInfo.EnvironmentVariables['VENICE_DISCORD_CONTRACT_SHA256'] = $ExpectedDiscordContractSha256

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $startInfo
[void]$process.Start()
$process.WaitForExit()
$innerEncoded = $null
$nodeSourceBase64 = $null
$discordContractBase64 = $null
if ($process.ExitCode -ne 0) { throw 'The short-lived Venice configuration process failed.' }
[pscustomobject]@{
  ok=$true
  secretProcessExited=$true
  botTokenPersistedLocally=$false
  botTokenStillValidAtDiscord=$true
  revocationRequired=$true
  sourceCommit=$head
} | Microsoft.PowerShell.Utility\ConvertTo-Json -Compress
