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
  $secure = Get-Content -LiteralPath $Cfg.tokenPath -Raw | ConvertTo-SecureString
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}
$Cfg=Read-Config;$Token=Read-WorkerToken $Cfg;$Origin=([string]$Cfg.origin).TrimEnd('/');$WorkerId=[string]$Cfg.workerId;$LogPath=if($Cfg.logPath){[string]$Cfg.logPath}else{Join-Path (Split-Path $ConfigPath) 'worker.log'}
function Log([string]$Message){$line="$(Get-Date -Format o) $Message";Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8;$info=Get-Item -LiteralPath $LogPath -ErrorAction SilentlyContinue;if($info -and $info.Length -gt 2MB){Get-Content -LiteralPath $LogPath -Tail 1000|Set-Content -LiteralPath "$LogPath.tmp" -Encoding UTF8;Move-Item -Force "$LogPath.tmp" $LogPath}}
function Invoke-HandsApi([string]$Method,[string]$Path,[object]$Body=$null){$headers=@{Authorization="Bearer $Token";'X-Home-Center-Worker'=$WorkerId};$params=@{Method=$Method;Uri="$Origin/computer-hands/v1/$Path";Headers=$headers;ContentType='application/json';TimeoutSec=130};if($null-ne$Body){$params.Body=($Body|ConvertTo-Json -Depth 20 -Compress)};Invoke-RestMethod @params}
function Get-SystemStatus{$os=Get-CimInstance Win32_OperatingSystem;@{ok=$true;machine=$env:COMPUTERNAME;user=[Environment]::UserName;interactive=[Environment]::UserInteractive;os=$os.Caption;osVersion=$os.Version;powershell=$PSVersionTable.PSVersion.ToString();processId=$PID;sessionId=(Get-Process -Id $PID).SessionId;timestamp=(Get-Date).ToUniversalTime().ToString('o')}}
function Get-WindowList{$rows=New-Object System.Collections.Generic.List[object];$callback=[HomeCenterHandsNative+EnumWindowsProc]{param($hwnd,$lparam)if(-not[HomeCenterHandsNative]::IsWindowVisible($hwnd)){return $true};$sb=New-Object Text.StringBuilder 1024;[void][HomeCenterHandsNative]::GetWindowText($hwnd,$sb,$sb.Capacity);$title=$sb.ToString().Trim();if(-not$title){return $true};[uint32]$pid=0;[void][HomeCenterHandsNative]::GetWindowThreadProcessId($hwnd,[ref]$pid);$name='';try{$name=(Get-Process -Id $pid -ErrorAction Stop).ProcessName}catch{};$rows.Add([pscustomobject]@{handle=$hwnd.ToInt64();pid=$pid;process=$name;title=$title});return $true};[void][HomeCenterHandsNative]::EnumWindows($callback,[IntPtr]::Zero);@{ok=$true;windows=@($rows|Select-Object -First 200);count=$rows.Count}}
function Focus-Window([object]$Args){$windows=(Get-WindowList).windows;$target=$null;if($Args.pid){$target=$windows|Where-Object{$_.pid-eq[int]$Args.pid}|Select-Object -First 1}elseif($Args.title){$needle=[string]$Args.title;$target=$windows|Where-Object{$_.title-like"*$needle*"}|Select-Object -First 1};if(-not$target){throw'Requested window was not found.'};$hwnd=[IntPtr]::new([int64]$target.handle);[void][HomeCenterHandsNative]::ShowWindowAsync($hwnd,9);Start-Sleep -Milliseconds 120;@{ok=[bool][HomeCenterHandsNative]::SetForegroundWindow($hwnd);window=$target}}
function Capture-Screen([object]$Args){$bounds=[System.Windows.Forms.SystemInformation]::VirtualScreen;$source=New-Object Drawing.Bitmap $bounds.Width,$bounds.Height;$g=[Drawing.Graphics]::FromImage($source);try{$g.CopyFromScreen($bounds.Left,$bounds.Top,0,0,$source.Size)}finally{$g.Dispose()};try{$maxWidth=if($Args.maxWidth){[int]$Args.maxWidth}else{1280};$quality=if($Args.quality){[int64]$Args.quality}else{55};$scale=[Math]::Min(1.0,$maxWidth/[double]$source.Width);$w=[Math]::Max(1,[int]($source.Width*$scale));$h=[Math]::Max(1,[int]($source.Height*$scale));$image=New-Object Drawing.Bitmap $w,$h;$rg=[Drawing.Graphics]::FromImage($image);try{$rg.DrawImage($source,0,0,$w,$h)}finally{$rg.Dispose()};try{$codec=[Drawing.Imaging.ImageCodecInfo]::GetImageEncoders()|Where-Object MimeType -eq'image/jpeg'|Select-Object -First 1;$ep=New-Object Drawing.Imaging.EncoderParameters 1;$ep.Param[0]=New-Object Drawing.Imaging.EncoderParameter ([Drawing.Imaging.Encoder]::Quality),$quality;$ms=New-Object IO.MemoryStream;try{$image.Save($ms,$codec,$ep);$bytes=$ms.ToArray()}finally{$ms.Dispose();$ep.Dispose()}}finally{$image.Dispose()};@{ok=$true;mimeType='image/jpeg';width=$w;height=$h;byteCount=$bytes.Length;base64=[Convert]::ToBase64String($bytes)}}finally{$source.Dispose()}}
function Get-ProcessList{$items=Get-Process|Sort-Object ProcessName,Id|Select-Object -First 300|ForEach-Object{[pscustomobject]@{pid=$_.Id;name=$_.ProcessName;sessionId=$_.SessionId;windowTitle=$_.MainWindowTitle}};@{ok=$true;processes=@($items);count=@($items).Count}}
function Invoke-Key([string]$Key){$normalized=$Key.Trim().ToUpperInvariant();$map=@{ENTER='{ENTER}';TAB='{TAB}';ESC='{ESC}';ESCAPE='{ESC}';BACKSPACE='{BACKSPACE}';DELETE='{DELETE}';UP='{UP}';DOWN='{DOWN}';LEFT='{LEFT}';RIGHT='{RIGHT}';HOME='{HOME}';END='{END}';PGUP='{PGUP}';PGDN='{PGDN}';F1='{F1}';F2='{F2}';F3='{F3}';F4='{F4}';F5='{F5}';F6='{F6}';F7='{F7}';F8='{F8}';F9='{F9}';F10='{F10}';F11='{F11}';F12='{F12}'};if($map.ContainsKey($normalized)){[Windows.Forms.SendKeys]::SendWait($map[$normalized]);return};if($normalized-match'^(CTRL|ALT|SHIFT)\+(.+)$'){$prefix=switch($Matches[1]){'CTRL'{'^'}'ALT'{'%'}'SHIFT'{'+'}};$tail=$Matches[2];if($tail.Length-eq1){[Windows.Forms.SendKeys]::SendWait("$prefix$tail");return};if($map.ContainsKey($tail)){[Windows.Forms.SendKeys]::SendWait("$prefix$($map[$tail])");return}};if($normalized.Length-eq1){[Windows.Forms.SendKeys]::SendWait($normalized);return};throw"Unsupported key chord: $Key"}
function Invoke-Mouse([object]$Args){[void][HomeCenterHandsNative]::SetCursorPos([int]$Args.x,[int]$Args.y);$event=if($Args.event){([string]$Args.event).ToLowerInvariant()}else{'click'};$button=if($Args.button){([string]$Args.button).ToLowerInvariant()}else{'left'};$down=if($button-eq'right'){0x0008}elseif($button-eq'middle'){0x0020}else{0x0002};$up=if($button-eq'right'){0x0010}elseif($button-eq'middle'){0x0040}else{0x0004};if($event-in@('down','click')){[HomeCenterHandsNative]::mouse_event($down,0,0,0,[UIntPtr]::Zero)};if($event-in@('up','click')){[HomeCenterHandsNative]::mouse_event($up,0,0,0,[UIntPtr]::Zero)};@{ok=$true;x=[int]$Args.x;y=[int]$Args.y;button=$button;event=$event}}
function Run-Shell([object]$Args){$encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes([string]$Args.command));$psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName='powershell.exe';$psi.Arguments="-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded";if($Args.workingDirectory){$psi.WorkingDirectory=[string]$Args.workingDirectory};$psi.UseShellExecute=$false;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.CreateNoWindow=$true;$p=New-Object Diagnostics.Process;$p.StartInfo=$psi;[void]$p.Start();$stdoutTask=$p.StandardOutput.ReadToEndAsync();$stderrTask=$p.StandardError.ReadToEndAsync();if(-not$p.WaitForExit(120000)){try{$p.Kill()}catch{};throw'shell.exec exceeded 120 seconds.'};$stdout=$stdoutTask.Result;$stderr=$stderrTask.Result;@{ok=($p.ExitCode-eq0);exitCode=$p.ExitCode;stdout=$stdout.Substring(0,[Math]::Min(120000,$stdout.Length));stderr=$stderr.Substring(0,[Math]::Min(60000,$stderr.Length))}}
function Execute-Ticket([object]$Ticket){$a=$Ticket.arguments;switch([string]$Ticket.action){'system.status'{return Get-SystemStatus}'screen.capture'{return Capture-Screen $a}'window.list'{return Get-WindowList}'window.focus'{return Focus-Window $a}'process.list'{return Get-ProcessList}'process.start'{$sp=@{FilePath=[string]$a.command;PassThru=$true};if($a.arguments){$sp.ArgumentList=[string]$a.arguments};if($a.workingDirectory){$sp.WorkingDirectory=[string]$a.workingDirectory};$p=Start-Process @sp;return @{ok=$true;pid=$p.Id;name=$p.ProcessName}}'process.stop'{Stop-Process -Id([int]$a.pid)-ErrorAction Stop;return @{ok=$true;pid=[int]$a.pid}}'input.type'{[HomeCenterHandsNative]::TypeUnicode([string]$a.text);return @{ok=$true;characters=([string]$a.text).Length}}'input.key'{Invoke-Key([string]$a.key);return @{ok=$true;key=[string]$a.key}}'input.mouse'{return Invoke-Mouse $a}'clipboard.get'{return @{ok=$true;text=[string](Get-Clipboard -Raw -ErrorAction Stop)}}'clipboard.set'{Set-Clipboard -Value([string]$a.text);return @{ok=$true;characters=([string]$a.text).Length}}'shell.exec'{return Run-Shell $a}default{throw"Unsupported action: $($Ticket.action)"}}}
Log "worker_start workerId=$WorkerId pid=$PID"
while($true){try{$lease=Invoke-HandsApi'POST''lease'@{};if(-not$lease.ticket){Start-Sleep -Seconds([Math]::Max(1,[int]$lease.pollAfterSeconds));continue};$ticket=$lease.ticket;Log "ticket_leased id=$($ticket.ticketId) action=$($ticket.action)";try{[void](Invoke-HandsApi'POST'"tickets/$($ticket.ticketId)/heartbeat"@{phase='executing'});$result=Execute-Ticket $ticket;[void](Invoke-HandsApi'POST'"tickets/$($ticket.ticketId)/complete"@{result=$result});Log "ticket_complete id=$($ticket.ticketId) ok=$($result.ok)"}catch{$failure=@{ok=$false;error='worker_action_failed';detail=$_.Exception.Message;action=[string]$ticket.action};try{[void](Invoke-HandsApi'POST'"tickets/$($ticket.ticketId)/complete"@{result=$failure})}catch{Log "ticket_failure_report_failed id=$($ticket.ticketId) detail=$($_.Exception.Message)"};Log "ticket_failed id=$($ticket.ticketId) detail=$($failure.detail)"}}catch{Log "poll_error $($_.Exception.Message)";Start-Sleep -Seconds 5}}
