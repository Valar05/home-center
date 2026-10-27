# Windows PowerShell 5.1 contract for direct local-link pairing and alias.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$helper=Join-Path $PSScriptRoot 'ritsu_local_pair_cauldron.ps1'
$t=$null;$parseErrors=$null
[void][Management.Automation.Language.Parser]::ParseFile($helper,[ref]$t,[ref]$parseErrors)
if($parseErrors.Count -gt 0){throw ('RITSUPAIR_TEST=syntax_error '+($parseErrors|Out-String))}
Write-Output 'RITSUPAIR_POWERSHELL_SYNTAX=PASS'
$root=Join-Path $env:RUNNER_TEMP ('ritsu-pair-test-'+[Guid]::NewGuid().ToString('N'))
$original=$env:LOCALAPPDATA
try{
 New-Item -ItemType Directory -Path $root -Force|Out-Null
 $env:LOCALAPPDATA=Join-Path $root 'managed'
 $profile=Join-Path $root 'profile\Microsoft.PowerShell_profile.ps1'
 New-Item -ItemType Directory -Path (Split-Path $profile -Parent) -Force|Out-Null
 $owner='OWNER_CUSTOM_LINES_PRESERVED'
 [IO.File]::WriteAllText($profile,($owner+[Environment]::NewLine))
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helper -Mode Install -ProfilePath $profile
 if($LASTEXITCODE -ne 0){throw 'install_failed'}
 $one=[IO.File]::ReadAllText($profile)
 if(-not $one.Contains($owner) -or -not $one.Contains('function global:ritsupair') -or
    -not $one.Contains('RITSUPAIR_DIRECT_V1')){throw 'profile_alias_or_original_missing'}
 $copy=Join-Path $env:LOCALAPPDATA 'HomeCenter\RitsuLocalPair\ritsu_local_pair_cauldron.ps1'
 if(-not(Test-Path $copy)){throw 'helper_not_copied'}
 if((Get-FileHash $helper -Algorithm SHA256).Hash -ne
    (Get-FileHash $copy -Algorithm SHA256).Hash){throw 'helper_copy_mismatch'}
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helper -Mode Install -ProfilePath $profile
 if($LASTEXITCODE -ne 0){throw 'idempotent_install_failed'}
 if([IO.File]::ReadAllText($profile) -cne $one){throw 'rerun_changed_profile'}
 Write-Output 'RITSUPAIR_INSTALL_IDEMPOTENT=PASS'
 # Existing other-owner function must not be overwritten.
 $conflict=Join-Path $root 'profile\conflict.ps1'
 $prior='function ritsupair { Write-Output "owner-defined" }'
 [IO.File]::WriteAllText($conflict,$prior)
 $ErrorActionPreference='Continue'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helper -Mode Install -ProfilePath $conflict *> $null
 $rc=$LASTEXITCODE
 $ErrorActionPreference='Stop'
 if($rc -eq 0){throw 'alias_conflict_not_rejected'}
 if([IO.File]::ReadAllText($conflict) -cne $prior){throw 'unowned_profile_changed'}
 Write-Output 'RITSUPAIR_UNOWNED_ALIAS_PRESERVED=PASS'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helper -Mode Remove -ProfilePath $profile
 if($LASTEXITCODE -ne 0){throw 'remove_failed'}
 $after=[IO.File]::ReadAllText($profile)
 if(-not $after.Contains($owner) -or $after.Contains('RITSUPAIR_DIRECT_V1')){
    throw 'remove_modified_unrelated_lines'
 }
 Write-Output 'RITSUPAIR_ROLLBACK_PRESERVES_PROFILE=PASS'
 $doctor=(& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helper -Mode Doctor | Out-String)
 if($LASTEXITCODE -ne 0 -or -not $doctor.Contains('RITSUPAIR_DOCTOR=PASS') -or
    $doctor.Contains('Bearer ')){throw 'doctor_failed_or_emitted_secret'}
 Write-Output 'RITSUPAIR_DOCTOR_NO_SECRET=PASS'
}finally{
 $env:LOCALAPPDATA=$original
 Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
