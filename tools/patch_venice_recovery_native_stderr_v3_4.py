from pathlib import Path

files = [
    Path('computer-hands/windows/repair.ps1'),
    Path('staging/venice-phase1/install-shadow-v2.ps1'),
    Path('staging/venice-phase1/recover-hands-and-install-shadow-v2.ps1'),
]

for p in files:
    s = p.read_text(encoding='utf-8')
    old = '& git -C $RepoPath fetch origin main'
    new = '& git -C $RepoPath fetch --quiet origin main'
    if old in s:
        s = s.replace(old, new)
    elif new not in s:
        raise SystemExit(f'git fetch anchor missing in {p}')
    p.write_text(s, encoding='utf-8')

# The one-shot wrapper must use separate child stdout/stderr capture, never 2>&1.
wrapper = files[2].read_text(encoding='utf-8')
required = [
    'function Invoke-CapturedPowerShell',
    '$psi.RedirectStandardOutput = $true',
    '$psi.RedirectStandardError = $true',
    '$repairProcess = Invoke-CapturedPowerShell',
    '$phaseProcess = Invoke-CapturedPowerShell',
]
for marker in required:
    if marker not in wrapper:
        raise SystemExit(f'wrapper capture marker missing: {marker}')
if '$repairRaw = (& powershell.exe' in wrapper or '$phaseRaw = (& powershell.exe' in wrapper:
    raise SystemExit('legacy merged child invocation still present')

# The installer still launches the small shadow patch as a child; replace merged
# 2>&1 capture with temp-file redirection + exit-code authority.
installer_path = files[1]
installer = installer_path.read_text(encoding='utf-8')
old_block = '''$patchOutput = (& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $patchTemp -RuntimeRoot $RuntimeRoot 2>&1 | Out-String)\n$patchExit = $LASTEXITCODE'''
new_block = '''$patchStdout = Join-Path $env:TEMP 'venice-shadow-patch.stdout.txt'\n$patchStderr = Join-Path $env:TEMP 'venice-shadow-patch.stderr.txt'\nRemove-Item -LiteralPath $patchStdout,$patchStderr -Force -ErrorAction SilentlyContinue\n$patchProcess = Start-Process powershell.exe -ArgumentList @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$patchTemp,'-RuntimeRoot',$RuntimeRoot) -Wait -PassThru -NoNewWindow -RedirectStandardOutput $patchStdout -RedirectStandardError $patchStderr\n$patchExit = $patchProcess.ExitCode\n$patchOutput = if (Test-Path -LiteralPath $patchStdout) { Get-Content -LiteralPath $patchStdout -Raw } else { '' }\n$patchErrorOutput = if (Test-Path -LiteralPath $patchStderr) { Get-Content -LiteralPath $patchStderr -Raw } else { '' }'''
if old_block in installer:
    installer = installer.replace(old_block, new_block)
elif '$patchProcess = Start-Process powershell.exe' not in installer:
    raise SystemExit('installer shadow child anchor missing')
installer = installer.replace('shadowPatchError = $patchOutput.Trim()', "shadowPatchError = (($patchOutput + \"`n\" + $patchErrorOutput).Trim())")
installer_path.write_text(installer, encoding='utf-8')

print('Venice recovery native stderr v3.4 patch applied')
