[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ExpectedPowerShell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'

# Re-enter under the governed host before any trust decision. The bootstrap uses
# only intrinsic values and fully qualified .NET APIs, so profiles and aliases
# in the caller cannot shadow the verifier.
if ($env:VENICE_TRUSTED_POWERSHELL_BOOTSTRAP -ne '1') {
  if (-not $PSCommandPath -or $PSCommandPath.Contains('"')) { throw 'The governed launcher path is invalid.' }
  $bootstrap = [System.Diagnostics.ProcessStartInfo]::new()
  $bootstrap.FileName = $ExpectedPowerShell
  $bootstrap.Arguments = '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '"'
  $bootstrap.UseShellExecute = $false
  $bootstrap.RedirectStandardInput = $false
  $bootstrap.RedirectStandardOutput = $false
  $bootstrap.RedirectStandardError = $false
  $bootstrap.CreateNoWindow = $false
  $bootstrap.EnvironmentVariables.Clear()
  foreach ($name in @(
    'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH',
    'APPDATA', 'LOCALAPPDATA', 'ProgramData', 'ProgramFiles', 'ProgramFiles(x86)',
    'CommonProgramFiles', 'PATHEXT'
  )) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ($value) { $bootstrap.EnvironmentVariables[$name] = $value }
  }
  $bootstrap.EnvironmentVariables['PATH'] = 'C:\Windows\System32'
  $bootstrap.EnvironmentVariables['VENICE_TRUSTED_POWERSHELL_BOOTSTRAP'] = '1'
  $bootstrapProcess = [System.Diagnostics.Process]::new()
  $bootstrapProcess.StartInfo = $bootstrap
  [void]$bootstrapProcess.Start()
  $bootstrapProcess.WaitForExit()
  exit $bootstrapProcess.ExitCode
}

$ExpectedOrigin = 'https://github.com/Valar05/home-center.git'
$ExpectedGit = 'C:\Program Files\Git\cmd\git.exe'
$ExpectedGitSha256 = 'fec691d80fccc35fcc309fbc9f720536c1d795b8a562ec169f28c9923da9600f'
$ExpectedCredentialManager = 'C:\Program Files\Git\mingw64\bin\git-credential-manager.exe'
$ExpectedCredentialManagerSha256 = '4f8409fac2ee580ac525611a09314775a6b18639251dd3de8f66b5bf8dcb6f6a'
$ExpectedPowerShellSha256 = '7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5'
$ExpectedNode = 'C:\Program Files\nodejs\node.exe'
$ExpectedNodeSha256 = '77bdff912b1c569b3e693fe126f619337c3e9d73dafbc4d0bf1d4f1f6a145761'
$ExpectedInnerSha256 = 'f6421245c4134f1ce36d2e94f76dace3b6fa1faf8aaa1ba7047b955e71854889'
$ExpectedNodeSourceSha256 = '5645117ae1f4be629f954d42574ff9929a00b34f7156dc26b0daafd49b0b9762'
$ExpectedDiscordContractSha256 = '14a6e709c0dd2d17b0841c572b3069b5f663e807e26d11f4a4dcbd96ee073629'
$RepoRoot = [IO.Path]::GetFullPath([IO.Path]::Combine($PSScriptRoot, '..'))
$InnerScript = [IO.Path]::Combine($PSScriptRoot, 'configure_venice_discord_inner.ps1')
$NodeScript = [IO.Path]::Combine($PSScriptRoot, 'configure_venice_discord.mjs')
$DiscordContract = [IO.Path]::Combine($RepoRoot, 'functions', 'venice_discord_contract.json')

function Get-ByteSha256 {
  param([byte[]]$Bytes)
  $sha = [Security.Cryptography.SHA256]::Create()
  try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
  finally { $sha.Dispose() }
}

function Assert-TrustedRuntimeFile {
  param([string]$Path, [string]$Sha256)
  $item = Microsoft.PowerShell.Management\Get-Item -LiteralPath $Path -ErrorAction Stop
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Trusted runtime file is a reparse point: $Path" }
  $actual = (Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actual -ne $Sha256) { throw "Trusted runtime hash does not match the reviewed launcher: $Path" }
}

foreach ($path in @($ExpectedGit, $ExpectedCredentialManager, $ExpectedPowerShell, $ExpectedNode, $InnerScript, $NodeScript, $DiscordContract)) {
  if (-not (Microsoft.PowerShell.Management\Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Required governed file is missing: $path"
  }
}
Assert-TrustedRuntimeFile -Path $ExpectedGit -Sha256 $ExpectedGitSha256
Assert-TrustedRuntimeFile -Path $ExpectedCredentialManager -Sha256 $ExpectedCredentialManagerSha256
Assert-TrustedRuntimeFile -Path $ExpectedPowerShell -Sha256 $ExpectedPowerShellSha256
Assert-TrustedRuntimeFile -Path $ExpectedNode -Sha256 $ExpectedNodeSha256

$innerBytes = [IO.File]::ReadAllBytes($InnerScript)
$nodeBytes = [IO.File]::ReadAllBytes($NodeScript)
$contractBytes = [IO.File]::ReadAllBytes($DiscordContract)
if ((Get-ByteSha256 $innerBytes) -ne $ExpectedInnerSha256) { throw 'The reviewed inner launcher source changed.' }
if ((Get-ByteSha256 $nodeBytes) -ne $ExpectedNodeSourceSha256) { throw 'The reviewed Node configurator source changed.' }
if ((Get-ByteSha256 $contractBytes) -ne $ExpectedDiscordContractSha256) { throw 'The reviewed Discord contract changed.' }

$env:GIT_CONFIG_NOSYSTEM = '1'
$env:GIT_CONFIG_GLOBAL = 'NUL'
$env:PATH = 'C:\Program Files\Git\cmd;C:\Program Files\Git\mingw64\bin;C:\Windows\System32'
$gitTrust = @(
  '-c', 'credential.helper=manager',
  '-c', 'http.sslVerify=true',
  '-c', 'http.proxy=',
  '-c', 'https.proxy='
)
$origin = (& $ExpectedGit @gitTrust -C $RepoRoot remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0 -or $origin -ne $ExpectedOrigin) { throw 'The repository origin is not the governed Home Center remote.' }
$head = (& $ExpectedGit @gitTrust -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $head -notmatch '^[0-9a-f]{40}$') { throw 'The local Home Center commit could not be resolved.' }
$remoteLine = (& $ExpectedGit @gitTrust ls-remote --exit-code $ExpectedOrigin refs/heads/main).Trim()
if ($LASTEXITCODE -ne 0 -or $remoteLine -notmatch '^([0-9a-f]{40})\s+refs/heads/main$') {
  throw 'The governed origin/main commit could not be resolved.'
}
if ($head -ne $Matches[1]) { throw 'One-shot Discord configuration requires HEAD to equal current origin/main.' }
$status = & $ExpectedGit @gitTrust -C $RepoRoot status --porcelain --untracked-files=all
if ($LASTEXITCODE -ne 0 -or $status) { throw 'One-shot Discord configuration requires a completely clean worktree.' }

$innerSource = [Text.Encoding]::UTF8.GetString($innerBytes)
$innerEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($innerSource))
$nodeSourceBase64 = [Convert]::ToBase64String($nodeBytes)
$discordContractBase64 = [Convert]::ToBase64String($contractBytes)
$innerBytes = $null
$nodeBytes = $null
$contractBytes = $null
$innerSource = $null

$arguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', $innerEncoded)
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
