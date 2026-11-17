param(
  [string]$ConfigPath = "$env:LOCALAPPDATA\HomeCenter\ComputerHands\config.json"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Home Center Computer Hands Windows worker requires Windows.' }

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$Native = @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class HomeCenterHandsNative {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int cmdShow);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);
  [DllImport("user32.dll", SetLastError=true)] public static extern uint SendInput(uint count, INPUT[] inputs, int size);
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public InputUnion U; }
  [StructLayout(LayoutKind.Explicit)] public struct InputUnion { [FieldOffset(0)] public KEYBDINPUT ki; }
  [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public UIntPtr dwExtraInfo; }
  public const uint INPUT_KEYBOARD = 1;
  public const uint KEYEVENTF_KEYUP = 0x0002;
  public const uint KEYEVENTF_UNICODE = 0x0004;
  public static void TypeUnicode(string value) {
    foreach (char ch in value) {
      INPUT down = new INPUT(); down.type = INPUT_KEYBOARD; down.U.ki.wScan = ch; down.U.ki.dwFlags = KEYEVENTF_UNICODE;
      INPUT up = down; up.U.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;
      INPUT[] pair = new INPUT[] { down, up };
      if (SendInput(2, pair, Marshal.SizeOf(typeof(INPUT))) != 2) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
    }
  }
}
'@
Add-Type -TypeDefinition $Native -Language CSharp

function Read-Config {
  if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "Computer Hands config not found: $ConfigPath" }
  $cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
  if (-not $cfg.origin -or -not $cfg.workerId -or -not $cfg.tokenPath) { throw 'Computer Hands config is incomplete.' }
  return $cfg
}

function Read-WorkerToken([object]$Cfg) {
  if (-not (Test-Path -LiteralPath $Cfg.tokenPath)) { throw 'Computer Hands token file is missing.' }
  $serialized = (Get-Content -LiteralPath $Cfg.tokenPath -Raw).Trim()
  $secure = $serialized | ConvertTo-SecureString
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

$Cfg = Read-Config
$Token = Read-WorkerToken $Cfg
$Origin = ([string]$Cfg.origin).TrimEnd('/')
$WorkerId = [string]$Cfg.workerId
$LogPath = if ($Cfg.logPath) { [string]$Cfg.logPath } else { Join-Path (Split-Path $ConfigPath) 'worker.log' }
$progressProperty = $Cfg.PSObject.Properties['progressPath']
$ProgressPath = if ($progressProperty -and $progressProperty.Value) { [string]$progressProperty.Value } else { Join-Path (Split-Path $ConfigPath) 'progress.json' }
$healthProperty = $Cfg.PSObject.Properties['healthPath']
$HealthPath = if ($healthProperty -and $healthProperty.Value) { [string]$healthProperty.Value } else { Join-Path (Split-Path $ConfigPath) 'cloud-health.json' }

function Log([string]$Message) {
  $line = "$(Get-Date -Format o) $Message"
  Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
  $info = Get-Item -LiteralPath $LogPath -ErrorAction SilentlyContinue
  if ($info -and $info.Length -gt 2MB) {
    Get-Content -LiteralPath $LogPath -Tail 1000 | Set-Content -LiteralPath "$LogPath.tmp" -Encoding UTF8
    Move-Item -Force "$LogPath.tmp" $LogPath
  }
}

function Write-ProgressState([object]$State) {
  try {
    $payload = [ordered]@{
      updatedAt = (Get-Date).ToUniversalTime().ToString('o')
      workerId = $WorkerId
      machine = $env:COMPUTERNAME
      pid = $PID
      state = $State
    } | ConvertTo-Json -Depth 12
    $directory = Split-Path -Parent $ProgressPath
    if ($directory) { [IO.Directory]::CreateDirectory($directory) | Out-Null }
    $temp = "$ProgressPath.tmp"
    [IO.File]::WriteAllText($temp, $payload, [Text.UTF8Encoding]::new($false))
    Move-Item -Force $temp $ProgressPath
  } catch { Log "progress_write_failed $($_.Exception.Message)" }
}

function Write-CloudHealth([string]$Phase) {
  try {
    $payload = [ordered]@{
      schema = 'home-center-computer-hands-cloud-health-v1'
      updatedAt = (Get-Date).ToUniversalTime().ToString('o')
      workerId = $WorkerId
      machine = $env:COMPUTERNAME
      pid = $PID
      phase = $Phase
    } | ConvertTo-Json -Depth 6
    $directory = Split-Path -Parent $HealthPath
    if ($directory) { [IO.Directory]::CreateDirectory($directory) | Out-Null }
    $temp = "$HealthPath.tmp"
    [IO.File]::WriteAllText($temp, $payload, [Text.UTF8Encoding]::new($false))
    Move-Item -Force $temp $HealthPath
  } catch { Log "cloud_health_write_failed $($_.Exception.Message)" }
}

function Invoke-HandsApi([string]$Method, [string]$Path, [object]$Body = $null) {
  $headers = @{ Authorization = "Bearer $Token"; 'X-Home-Center-Worker' = $WorkerId }
  $params = @{ Method = $Method; Uri = "$Origin/computer-hands/v1/$Path"; Headers = $headers; ContentType = 'application/json'; TimeoutSec = 130 }
  if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Depth 20 -Compress) }
  return Invoke-RestMethod @params
}

function Get-SystemStatus {
  $os = Get-CimInstance Win32_OperatingSystem
  return @{ ok=$true; machine=$env:COMPUTERNAME; user=[Environment]::UserName; interactive=[Environment]::UserInteractive; os=$os.Caption; osVersion=$os.Version; powershell=$PSVersionTable.PSVersion.ToString(); processId=$PID; sessionId=(Get-Process -Id $PID).SessionId; timestamp=(Get-Date).ToUniversalTime().ToString('o') }
}

function Get-WindowList {
  $rows = New-Object System.Collections.Generic.List[object]
  $callback = [HomeCenterHandsNative+EnumWindowsProc]{ param($hwnd, $lparam)
    if (-not [HomeCenterHandsNative]::IsWindowVisible($hwnd)) { return $true }
    $sb = New-Object Text.StringBuilder 1024
    [void][HomeCenterHandsNative]::GetWindowText($hwnd, $sb, $sb.Capacity)
    $title = $sb.ToString().Trim(); if (-not $title) { return $true }
    [uint32]$windowProcessId = 0; [void][HomeCenterHandsNative]::GetWindowThreadProcessId($hwnd, [ref]$windowProcessId)
    $name = ''; try { $name = (Get-Process -Id $windowProcessId -ErrorAction Stop).ProcessName } catch {}
    $rows.Add([pscustomobject]@{handle=$hwnd.ToInt64(); pid=$windowProcessId; process=$name; title=$title}); return $true
  }
  [void][HomeCenterHandsNative]::EnumWindows($callback, [IntPtr]::Zero)
  return @{ok=$true; windows=@($rows | Select-Object -First 200); count=$rows.Count}
}

function Get-ActionArg([object]$ActionArgs, [string]$Name, $Default = $null) {
  if ($null -eq $ActionArgs) { return $Default }
  $property = $ActionArgs.PSObject.Properties[$Name]
  if ($null -eq $property) { return $Default }
  if ($null -eq $property.Value) { return $Default }
  return $property.Value
}

function Focus-Window([object]$ActionArgs) {
  $windows = (Get-WindowList).windows; $target = $null
  $requestedPid = Get-ActionArg $ActionArgs 'pid' $null
  $requestedTitle = [string](Get-ActionArg $ActionArgs 'title' '')
  if ($null -ne $requestedPid) { $target = $windows | Where-Object { $_.pid -eq [int]$requestedPid } | Select-Object -First 1 }
  elseif ($requestedTitle) { $needle=$requestedTitle; $target=$windows | Where-Object { $_.title -like "*$needle*" } | Select-Object -First 1 }
  if (-not $target) { throw 'Requested window was not found.' }
  $hwnd=[IntPtr]::new([int64]$target.handle); [void][HomeCenterHandsNative]::ShowWindowAsync($hwnd,9); Start-Sleep -Milliseconds 120
  return @{ok=[bool][HomeCenterHandsNative]::SetForegroundWindow($hwnd); window=$target}
}

function Capture-Screen([object]$ActionArgs) {
  $bounds=[System.Windows.Forms.SystemInformation]::VirtualScreen
  $source=New-Object Drawing.Bitmap $bounds.Width,$bounds.Height
  $g=[Drawing.Graphics]::FromImage($source); try{$g.CopyFromScreen($bounds.Left,$bounds.Top,0,0,$source.Size)}finally{$g.Dispose()}
  try {
    $maxWidth=[int](Get-ActionArg $ActionArgs 'maxWidth' 1280); $quality=[int64](Get-ActionArg $ActionArgs 'quality' 55)
    $scale=[Math]::Min(1.0,$maxWidth/[double]$source.Width); $w=[Math]::Max(1,[int]($source.Width*$scale)); $h=[Math]::Max(1,[int]($source.Height*$scale))
    $image=New-Object Drawing.Bitmap $w,$h; $rg=[Drawing.Graphics]::FromImage($image); try{$rg.DrawImage($source,0,0,$w,$h)}finally{$rg.Dispose()}
    try {
      $codec=[Drawing.Imaging.ImageCodecInfo]::GetImageEncoders()|Where-Object MimeType -eq 'image/jpeg'|Select-Object -First 1
      $ep=New-Object Drawing.Imaging.EncoderParameters 1; $ep.Param[0]=New-Object Drawing.Imaging.EncoderParameter ([Drawing.Imaging.Encoder]::Quality),$quality
      $ms=New-Object IO.MemoryStream; try{$image.Save($ms,$codec,$ep);$bytes=$ms.ToArray()}finally{$ms.Dispose();$ep.Dispose()}
    } finally {$image.Dispose()}
    return @{ok=$true;mimeType='image/jpeg';width=$w;height=$h;byteCount=$bytes.Length;base64=[Convert]::ToBase64String($bytes)}
  } finally {$source.Dispose()}
}

function Get-ProcessList {
  $items=Get-Process|Sort-Object ProcessName,Id|Select-Object -First 300|ForEach-Object{[pscustomobject]@{pid=$_.Id;name=$_.ProcessName;sessionId=$_.SessionId;windowTitle=$_.MainWindowTitle}}
  return @{ok=$true;processes=@($items);count=@($items).Count}
}

function Invoke-Key([string]$Key) {
  $normalized=$Key.Trim().ToUpperInvariant()
  $map=@{ENTER='{ENTER}';TAB='{TAB}';ESC='{ESC}';ESCAPE='{ESC}';BACKSPACE='{BACKSPACE}';DELETE='{DELETE}';UP='{UP}';DOWN='{DOWN}';LEFT='{LEFT}';RIGHT='{RIGHT}';HOME='{HOME}';END='{END}';PGUP='{PGUP}';PGDN='{PGDN}';F1='{F1}';F2='{F2}';F3='{F3}';F4='{F4}';F5='{F5}';F6='{F6}';F7='{F7}';F8='{F8}';F9='{F9}';F10='{F10}';F11='{F11}';F12='{F12}'}
  if($map.ContainsKey($normalized)){[Windows.Forms.SendKeys]::SendWait($map[$normalized]);return}
  if($normalized -match '^(CTRL|ALT|SHIFT)\+(.+)$'){$prefix=switch($Matches[1]){'CTRL'{'^'}'ALT'{'%'}'SHIFT'{'+'}};$tail=$Matches[2];if($tail.Length -eq 1){[Windows.Forms.SendKeys]::SendWait("$prefix$tail");return};if($map.ContainsKey($tail)){[Windows.Forms.SendKeys]::SendWait("$prefix$($map[$tail])");return}}
  if($normalized.Length -eq 1){[Windows.Forms.SendKeys]::SendWait($normalized);return};throw "Unsupported key chord: $Key"
}

function Invoke-Mouse([object]$ActionArgs) {
  $x=[int](Get-ActionArg $ActionArgs 'x' 0);$y=[int](Get-ActionArg $ActionArgs 'y' 0);$event=([string](Get-ActionArg $ActionArgs 'event' 'click')).ToLowerInvariant();$button=([string](Get-ActionArg $ActionArgs 'button' 'left')).ToLowerInvariant();[void][HomeCenterHandsNative]::SetCursorPos($x,$y)
  $down=if($button -eq 'right'){0x0008}elseif($button -eq 'middle'){0x0020}else{0x0002};$up=if($button -eq 'right'){0x0010}elseif($button -eq 'middle'){0x0040}else{0x0004}
  if($event -in @('down','click')){[HomeCenterHandsNative]::mouse_event($down,0,0,0,[UIntPtr]::Zero)};if($event -in @('up','click')){[HomeCenterHandsNative]::mouse_event($up,0,0,0,[UIntPtr]::Zero)}
  return @{ok=$true;x=$x;y=$y;button=$button;event=$event}
}

function Run-Shell([object]$ActionArgs, [object]$Ticket = $null) {
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
  $a=$ActionArgs
  switch($Action){
    'system.status'{return Get-SystemStatus}
    'screen.capture'{return Capture-Screen $a}
    'window.list'{return Get-WindowList}
    'window.focus'{return Focus-Window $a}
    'process.list'{return Get-ProcessList}
    'process.start'{$command=[string](Get-ActionArg $a 'command' '');if(-not $command){throw 'process.start command was missing from the leased ticket.'};$sp=@{FilePath=$command;PassThru=$true};$processArguments=[string](Get-ActionArg $a 'arguments' '');$workingDirectory=[string](Get-ActionArg $a 'workingDirectory' '');if($processArguments){$sp.ArgumentList=$processArguments};if($workingDirectory){$sp.WorkingDirectory=$workingDirectory};$p=Start-Process @sp;return @{ok=$true;pid=$p.Id;name=$p.ProcessName}}
    'process.stop'{Stop-Process -Id ([int]$a.pid) -ErrorAction Stop;return @{ok=$true;pid=[int]$a.pid}}
    'input.type'{[HomeCenterHandsNative]::TypeUnicode([string]$a.text);return @{ok=$true;characters=([string]$a.text).Length}}
    'input.key'{Invoke-Key ([string]$a.key);return @{ok=$true;key=[string]$a.key}}
    'input.mouse'{return Invoke-Mouse $a}
    'clipboard.get'{return @{ok=$true;text=[string](Get-Clipboard -Raw -ErrorAction Stop)}}
    'clipboard.set'{Set-Clipboard -Value ([string]$a.text);return @{ok=$true;characters=([string]$a.text).Length}}
    'shell.exec'{return Run-Shell $a $Ticket}
    default{throw "Unsupported action: $Action"}
  }
}

function Execute-Ticket([object]$Ticket) {
  $action=[string]$Ticket.action
  $a=$Ticket.arguments
  if($action -ne 'packet.execute'){ return Execute-Action $action $a $Ticket }

  $steps=@(Get-ActionArg $a 'steps' @())
  $stopOnError=[bool](Get-ActionArg $a 'stopOnError' $true)
  $results=@()
  $completed=0
  $allOk=$true
  for($index=0;$index -lt $steps.Count;$index+=1){
    $step=$steps[$index]
    $stepId=[string](Get-ActionArg $step 'id' ("step-{0:d2}" -f ($index+1)))
    $stepAction=[string](Get-ActionArg $step 'action' '')
    $stepArgs=Get-ActionArg $step 'arguments' ([pscustomobject]@{})
    $progress=@{phase='packet_step';completedSteps=$completed;totalSteps=$steps.Count;currentStepId=$stepId;currentAction=$stepAction;message=("Running {0}/{1}: {2}" -f ($index+1),$steps.Count,$stepAction)}
    Write-ProgressState @{ticketId=$Ticket.ticketId;requestId=$Ticket.requestId;laneId=$Ticket.laneId;action=$action;progress=$progress}
    $heartbeat=Invoke-HandsApi 'POST' "tickets/$($Ticket.ticketId)/heartbeat" @{phase='packet_step';progress=$progress}
    if($heartbeat.cancelRequested -eq $true){
      return @{ok=$false;cancelled=$true;packet=$true;completedSteps=$completed;totalSteps=$steps.Count;steps=$results}
    }
    try{
      $stepResult=Execute-Action $stepAction $stepArgs $Ticket
      $completed+=1
      $results += [pscustomobject]@{id=$stepId;action=$stepAction;ok=($stepResult.ok -ne $false);result=$stepResult}
      if($stepResult.ok -eq $false){$allOk=$false;if($stopOnError){break}}
    }catch{
      $allOk=$false
      $results += [pscustomobject]@{id=$stepId;action=$stepAction;ok=$false;error=$_.Exception.Message}
      if($stopOnError){break}
    }
  }
  return @{ok=$allOk;packet=$true;completedSteps=$completed;totalSteps=$steps.Count;steps=$results}
}

Log "worker_start workerId=$WorkerId pid=$PID"
Write-ProgressState @{phase='worker_start';message='Computer Hands worker started.'}
$ConsecutivePollErrors = 0
while($true){
  try{
    $lease=Invoke-HandsApi 'POST' 'lease' @{}
    $ConsecutivePollErrors = 0
    Write-CloudHealth 'lease_ok'
    if(-not $lease.ticket){Write-ProgressState @{phase='idle';message='Waiting for work.'};Start-Sleep -Seconds ([Math]::Max(1,[int]$lease.pollAfterSeconds));continue}
    $ticket=$lease.ticket
    Log "ticket_leased id=$($ticket.ticketId) lane=$($ticket.laneId) action=$($ticket.action)"
    Write-ProgressState @{phase='leased';ticketId=$ticket.ticketId;requestId=$ticket.requestId;laneId=$ticket.laneId;action=$ticket.action;progress=$ticket.progress}
    try{
      $heartbeat=Invoke-HandsApi 'POST' "tickets/$($ticket.ticketId)/heartbeat" @{phase='executing';progress=@{phase='executing';completedSteps=0;totalSteps=if($ticket.action -eq 'packet.execute'){@($ticket.arguments.steps).Count}else{1};currentStepId='';currentAction=[string]$ticket.action;message='Executing ticket.'}}
      if($heartbeat.cancelRequested -eq $true){Write-ProgressState @{phase='cancelled';ticketId=$ticket.ticketId;laneId=$ticket.laneId;message='Ticket cancelled before execution.'};continue}
      $result=Execute-Ticket $ticket
      [void](Invoke-HandsApi 'POST' "tickets/$($ticket.ticketId)/complete" @{result=$result})
      Write-ProgressState @{phase=if($result.cancelled){'cancelled'}elseif($result.ok -eq $false){'failed'}else{'completed'};ticketId=$ticket.ticketId;requestId=$ticket.requestId;laneId=$ticket.laneId;action=$ticket.action;result=$result}
      Log "ticket_complete id=$($ticket.ticketId) ok=$($result.ok)"
    }catch{
      $failure=@{ok=$false;error='worker_action_failed';detail=$_.Exception.Message;action=[string]$ticket.action}
      try{[void](Invoke-HandsApi 'POST' "tickets/$($ticket.ticketId)/complete" @{result=$failure})}catch{Log "ticket_failure_report_failed id=$($ticket.ticketId) detail=$($_.Exception.Message)"}
      Write-ProgressState @{phase='failed';ticketId=$ticket.ticketId;requestId=$ticket.requestId;laneId=$ticket.laneId;action=$ticket.action;error=$failure.detail}
      Log "ticket_failed id=$($ticket.ticketId) detail=$($failure.detail)"
    }
  }catch{
    $ConsecutivePollErrors += 1
    Log "poll_error count=$ConsecutivePollErrors $($_.Exception.Message)"
    Write-ProgressState @{phase='poll_error';message=$_.Exception.Message;consecutivePollErrors=$ConsecutivePollErrors}
    if($ConsecutivePollErrors -ge 20){
      Log 'poll_error_threshold_exit count=20; allowing scheduler recovery'
      throw
    }
    Start-Sleep -Seconds 3
  }
}
