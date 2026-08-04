[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ExpectedOrigin = 'https://github.com/Valar05/home-center.git'
$ExpectedGit = 'C:\Program Files\Git\cmd\git.exe'
$ExpectedGitSha256 = 'fec691d80fccc35fcc309fbc9f720536c1d795b8a562ec169f28c9923da9600f'
$ExpectedPowerShell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$ExpectedPowerShellSha256 = '7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5'
$ExpectedNode = 'C:\Program Files\nodejs\node.exe'
$ExpectedNodeSha256 = '77bdff912b1c569b3e693fe126f619337c3e9d73dafbc4d0bf1d4f1f6a145761'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$InnerScript = Join-Path $PSScriptRoot 'configure_venice_discord_inner.ps1'

function Assert-TrustedRuntimeFile {
  param([string]$Path, [string]$Sha256)
  $item = Get-Item -LiteralPath $Path -ErrorAction Stop
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Trusted runtime file is a reparse point: $Path" }
  $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actual -ne $Sha256) { throw "Trusted runtime hash does not match the reviewed launcher: $Path" }
}

$blockedNames = @(
  'NODE_OPTIONS', 'NODE_PATH', 'NODE_DEBUG', 'NODE_DEBUG_NATIVE',
  'NODE_EXTRA_CA_CERTS', 'NODE_TLS_REJECT_UNAUTHORIZED', 'NODE_V8_COVERAGE',
  'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
  'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'SSL_CERT_FILE', 'SSL_CERT_DIR'
)
$blocked = Get-ChildItem Env: | Where-Object { $blockedNames -contains $_.Name }
if ($blocked) {
  throw ('Refusing one-shot token handling while unsafe environment overrides are set: ' + (($blocked.Name | Sort-Object) -join ', '))
}
foreach ($path in @($ExpectedGit, $ExpectedPowerShell, $ExpectedNode, $InnerScript)) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required governed file is missing: $path" }
}
Assert-TrustedRuntimeFile -Path $ExpectedGit -Sha256 $ExpectedGitSha256
Assert-TrustedRuntimeFile -Path $ExpectedPowerShell -Sha256 $ExpectedPowerShellSha256
Assert-TrustedRuntimeFile -Path $ExpectedNode -Sha256 $ExpectedNodeSha256

$origin = (& $ExpectedGit -C $RepoRoot remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0 -or $origin -ne $ExpectedOrigin) { throw 'The repository origin is not the governed Home Center remote.' }
$head = (& $ExpectedGit -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $head -notmatch '^[0-9a-f]{40}$') { throw 'The local Home Center commit could not be resolved.' }
$remoteLine = (& $ExpectedGit -C $RepoRoot ls-remote --exit-code origin refs/heads/main).Trim()
if ($LASTEXITCODE -ne 0 -or $remoteLine -notmatch '^([0-9a-f]{40})\s+refs/heads/main$') {
  throw 'The governed origin/main commit could not be resolved.'
}
if ($head -ne $Matches[1]) { throw 'One-shot Discord configuration requires HEAD to equal current origin/main.' }
$status = & $ExpectedGit -C $RepoRoot status --porcelain --untracked-files=all
if ($LASTEXITCODE -ne 0 -or $status) { throw 'One-shot Discord configuration requires a completely clean worktree.' }

function Quote-ProcessArgument {
  param([string]$Value)
  if ($Value.Contains('"')) { throw 'Unexpected quote in a trusted process argument.' }
  return '"' + $Value + '"'
}

$arguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $InnerScript)
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $ExpectedPowerShell
$startInfo.Arguments = ($arguments | ForEach-Object { Quote-ProcessArgument ([string]$_) }) -join ' '
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
$startInfo.EnvironmentVariables['PATH'] = ((Split-Path -Parent $ExpectedNode), 'C:\Windows\System32' -join ';')
$startInfo.EnvironmentVariables['VENICE_TRUSTED_ONE_SHOT_LAUNCHER'] = '1'
$startInfo.EnvironmentVariables['VENICE_TRUSTED_NODE'] = $ExpectedNode
$startInfo.EnvironmentVariables['VENICE_TRUSTED_NODE_SHA256'] = $ExpectedNodeSha256

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $startInfo
[void]$process.Start()
$process.WaitForExit()
if ($process.ExitCode -ne 0) { throw 'The short-lived Venice configuration process failed.' }
[pscustomobject]@{ok=$true; secretProcessExited=$true; botTokenPersisted=$false; sourceCommit=$head} | ConvertTo-Json -Compress
