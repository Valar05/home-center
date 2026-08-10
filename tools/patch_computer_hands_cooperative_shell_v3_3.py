from pathlib import Path

p = Path('computer-hands/windows/home-center-hands.ps1')
s = p.read_text(encoding='utf-8')
old = r'''function Run-Shell([object]$ActionArgs) {
  $command=[string](Get-ActionArg $ActionArgs 'command' ''); if(-not $command){throw 'shell.exec command was missing from the leased ticket.'};$encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
  $psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName='powershell.exe';$psi.Arguments="-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded"
  $workingDirectory=[string](Get-ActionArg $ActionArgs 'workingDirectory' '');if($workingDirectory){$psi.WorkingDirectory=$workingDirectory};$psi.UseShellExecute=$false;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.CreateNoWindow=$true
  $p=New-Object Diagnostics.Process;$p.StartInfo=$psi;[void]$p.Start();$stdoutTask=$p.StandardOutput.ReadToEndAsync();$stderrTask=$p.StandardError.ReadToEndAsync()
  if(-not $p.WaitForExit(120000)){try{$p.Kill()}catch{};throw 'shell.exec exceeded 120 seconds.'};$stdout=$stdoutTask.Result;$stderr=$stderrTask.Result
  return @{ok=($p.ExitCode -eq 0);exitCode=$p.ExitCode;stdout=$stdout.Substring(0,[Math]::Min(120000,$stdout.Length));stderr=$stderr.Substring(0,[Math]::Min(60000,$stderr.Length))}
}

function Execute-Action([string]$Action, [object]$ActionArgs) {
'''
new = r'''function Run-Shell([object]$ActionArgs, [object]$Ticket = $null) {
  $command=[string](Get-ActionArg $ActionArgs 'command' ''); if(-not $command){throw 'shell.exec command was missing from the leased ticket.'};$encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
  $psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName='powershell.exe';$psi.Arguments="-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded"
  $workingDirectory=[string](Get-ActionArg $ActionArgs 'workingDirectory' '');if($workingDirectory){$psi.WorkingDirectory=$workingDirectory};$psi.UseShellExecute=$false;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.CreateNoWindow=$true
  $p=New-Object Diagnostics.Process;$p.StartInfo=$psi;[void]$p.Start();$stdoutTask=$p.StandardOutput.ReadToEndAsync();$stderrTask=$p.StandardError.ReadToEndAsync()
  $started=[DateTime]::UtcNow;$deadline=$started.AddSeconds(120);$nextHeartbeat=$started
  while(-not $p.HasExited){
    $now=[DateTime]::UtcNow
    if($now -ge $deadline){try{$p.Kill()}catch{};try{[void]$p.WaitForExit(5000)}catch{};throw 'shell.exec exceeded 120 seconds.'}
    if($null -ne $Ticket -and $now -ge $nextHeartbeat){
      $elapsed=[Math]::Max(0,[int](($now-$started).TotalSeconds))
      $progress=@{phase='shell_running';completedSteps=0;totalSteps=1;currentStepId='';currentAction='shell.exec';message=("Shell command running ({0}s)." -f $elapsed)}
      Write-ProgressState @{phase='shell_running';ticketId=$Ticket.ticketId;requestId=$Ticket.requestId;laneId=$Ticket.laneId;action='shell.exec';progress=$progress}
      $heartbeat=Invoke-HandsApi 'POST' "tickets/$($Ticket.ticketId)/heartbeat" @{phase='shell_running';progress=$progress}
      if($heartbeat.cancelRequested -eq $true){
        try{$p.Kill()}catch{};try{[void]$p.WaitForExit(5000)}catch{}
        return @{ok=$false;cancelled=$true;exitCode=$null;stdout='';stderr='';message='shell.exec cancelled by owner'}
      }
      $nextHeartbeat=$now.AddSeconds(5)
    }
    Start-Sleep -Milliseconds 250
  }
  [void]$p.WaitForExit()
  if(-not $stdoutTask.Wait(5000)){throw 'shell.exec stdout did not close after process exit.'}
  if(-not $stderrTask.Wait(5000)){throw 'shell.exec stderr did not close after process exit.'}
  $stdout=[string]$stdoutTask.Result;$stderr=[string]$stderrTask.Result
  return @{ok=($p.ExitCode -eq 0);exitCode=$p.ExitCode;stdout=$stdout.Substring(0,[Math]::Min(120000,$stdout.Length));stderr=$stderr.Substring(0,[Math]::Min(60000,$stderr.Length))}
}

function Execute-Action([string]$Action, [object]$ActionArgs, [object]$Ticket = $null) {
'''
if old not in s:
    raise SystemExit('expected Run-Shell/Execute-Action block not found')
s = s.replace(old, new, 1)
s = s.replace("    'shell.exec'{return Run-Shell $a}", "    'shell.exec'{return Run-Shell $a $Ticket}", 1)
s = s.replace("  if($action -ne 'packet.execute'){ return Execute-Action $action $a }", "  if($action -ne 'packet.execute'){ return Execute-Action $action $a $Ticket }", 1)
s = s.replace("      $stepResult=Execute-Action $stepAction $stepArgs", "      $stepResult=Execute-Action $stepAction $stepArgs $Ticket", 1)
p.write_text(s, encoding='utf-8')
print('cooperative shell v3.3 patch applied')
