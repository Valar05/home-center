param(
  [string]$ConfigPath = "$env:LOCALAPPDATA\HomeCenterHands\config.json"
)

$ErrorActionPreference = 'Stop'
$WorkerVersion = 'home-center-hands-windows-v1'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName Microsoft.VisualBasic

Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class HomeCenterMouse {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
  public const uint LEFTDOWN = 0x0002;
  public const uint LEFTUP = 0x0004;
  public const uint RIGHTDOWN = 0x0008;
  public const uint RIGHTUP = 0x0010;
}
'@

function Read-Config {
  if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "Computer Hands config missing: $ConfigPath" }
  Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
}

function Headers($cfg) {
  @{ Authorization = "Bearer $($cfg.token)"; 'X-Home-Center-Worker' = [string]$cfg.workerId; 'Content-Type' = 'application/json' }
}

function Invoke-HandsApi([string]$Method, [string]$Path, $Body = $null) {
  $cfg = Read-Config
  $uri = "$($cfg.origin.TrimEnd('/'))/computer-hands/v1/$Path"
  $params = @{ Method = $Method; Uri = $uri; Headers = (Headers $cfg); UseBasicParsing = $true }
  if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Depth 12 -Compress) }
  Invoke-RestMethod @params
}

function Encode-Bytes([byte[]]$Bytes) { [Convert]::ToBase64String($Bytes) }
function Sha256-Hex([byte[]]$Bytes) { $sha = [Security.Cryptography.SHA256]::Create(); try { -join ($sha.ComputeHash($Bytes) | ForEach-Object { $_.ToString('x2') }) } finally { $sha.Dispose() } }

function Capture-Screen($args) {
  $maxWidth = if ($args.maxWidth) { [int]$args.maxWidth } else { 1280 }
  $quality = if ($args.quality) { [int]$args.quality } else { 55 }
  $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
  $source = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
  $graphics = [System.Drawing.Graphics]::FromImage($source)
  try { $graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $source.Size) } finally { $graphics.Dispose() }
  $scale = [Math]::Min(1.0, $maxWidth / [double]$source.Width)
  $width = [Math]::Max(1, [int]($source.Width * $scale)); $height = [Math]::Max(1, [int]($source.Height * $scale))
  $image = if ($scale -lt 1) { $tmp = New-Object System.Drawing.Bitmap $width, $height; $g = [System.Drawing.Graphics]::FromImage($tmp); try { $g.DrawImage($source, 0, 0, $width, $height) } finally { $g.Dispose(); $source.Dispose() }; $tmp } else { $source }
  $stream = New-Object IO.MemoryStream
  try {
    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object MimeType -eq 'image/jpeg' | Select-Object -First 1
    $encoder = [System.Drawing.Imaging.Encoder]::Quality
    $parameters = New-Object System.Drawing.Imaging.EncoderParameters 1
    $parameters.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter($encoder, [long]$quality)
    $image.Save($stream, $codec, $parameters)
    $bytes = $stream.ToArray()
    if ($bytes.Length -gt 620000) { throw "Screenshot evidence exceeded 620 KB. Retry with a smaller maxWidth or quality." }
    @{ ok = $true; mimeType = 'image/jpeg'; width = $width; height = $height; byteCount = $bytes.Length; sha256 = (Sha256-Hex $bytes); base64 = (Encode-Bytes $bytes) }
  } finally { $stream.Dispose(); $image.Dispose() }
}

function Window-List {
  @(Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle } | ForEach-Object {
    @{ pid = $_.Id; title = $_.MainWindowTitle; processName = $_.ProcessName; handle = [int64]$_.MainWindowHandle }
  } | Select-Object -First 100)
}

function Focus-Window($args) {
  $target = $null
  if ($args.pid) { $target = Get-Process -Id ([int]$args.pid) -ErrorAction Stop }
  elseif ($args.title) { $target = Get-Process | Where-Object { $_.MainWindowTitle -like "*$($args.title)*" } | Select-Object -First 1 }
  if (-not $target) { throw 'Window target not found.' }
  $ok = [Microsoft.VisualBasic.Interaction]::AppActivate([int]$target.Id)
  @{ ok = [bool]$ok; pid = $target.Id; title = $target.MainWindowTitle }
}

function Escape-SendKeys([string]$Text) {
  $sb = New-Object Text.StringBuilder
  foreach ($c in $Text.ToCharArray()) {
    if ('+^%~(){}[]'.Contains([string]$c)) { [void]$sb.Append('{').Append($c).Append('}') } else { [void]$sb.Append($c) }
  }
  $sb.ToString()
}

function Send-Key([string]$Key) {
  $map = @{ ENTER = '{ENTER}'; TAB = '{TAB}'; ESC = '{ESC}'; ESCAPE = '{ESC}'; BACKSPACE = '{BACKSPACE}'; DELETE = '{DELETE}'; UP = '{UP}'; DOWN = '{DOWN}'; LEFT = '{LEFT}'; RIGHT = '{RIGHT}'; HOME = '{HOME}'; END = '{END}'; PGUP = '{PGUP}'; PGDN = '{PGDN}'; F1 = '{F1}'; F2 = '{F2}'; F3 = '{F3}'; F4 = '{F4}'; F5 = '{F5}'; F6 = '{F6}'; F7 = '{F7}'; F8 = '{F8}'; F9 = '{F9}'; F10 = '{F10}'; F11 = '{F11}'; F12 = '{F12}' }
  $upper = $Key.ToUpperInvariant()
  if ($map.ContainsKey($upper)) { [System.Windows.Forms.SendKeys]::SendWait($map[$upper]); return }
  if ($upper -match '^CTRL\+(.+)$') { [System.Windows.Forms.SendKeys]::SendWait('^' + (Escape-SendKeys $Matches[1].ToLowerInvariant())); return }
  if ($upper -match '^ALT\+(.+)$') { [System.Windows.Forms.SendKeys]::SendWait('%' + (Escape-SendKeys $Matches[1].ToLowerInvariant())); return }
  if ($upper -match '^SHIFT\+(.+)$') { [System.Windows.Forms.SendKeys]::SendWait('+' + (Escape-SendKeys $Matches[1].ToLowerInvariant())); return }
  if ($Key.Length -eq 1) { [System.Windows.Forms.SendKeys]::SendWait((Escape-SendKeys $Key)); return }
  throw "Unsupported key: $Key"
}

function Mouse-Action($args) {
  [void][HomeCenterMouse]::SetCursorPos([int]$args.x, [int]$args.y)
  $event = if ($args.event) { [string]$args.event } else { 'click' }
  $button = if ($args.button) { [string]$args.button } else { 'left' }
  if ($event -eq 'move') { return @{ ok = $true; x = [int]$args.x; y = [int]$args.y; event = 'move' } }
  if ($button -eq 'right') { [HomeCenterMouse]::mouse_event([HomeCenterMouse]::RIGHTDOWN,0,0,0,[UIntPtr]::Zero); [HomeCenterMouse]::mouse_event([HomeCenterMouse]::RIGHTUP,0,0,0,[UIntPtr]::Zero) }
  else { [HomeCenterMouse]::mouse_event([HomeCenterMouse]::LEFTDOWN,0,0,0,[UIntPtr]::Zero); [HomeCenterMouse]::mouse_event([HomeCenterMouse]::LEFTUP,0,0,0,[UIntPtr]::Zero) }
  @{ ok = $true; x = [int]$args.x; y = [int]$args.y; event = 'click'; button = $button }
}

function Execute-Action($ticket) {
  $action = [string]$ticket.action; $args = $ticket.arguments
  switch ($action) {
    'system.status' { return @{ ok = $true; workerVersion = $WorkerVersion; machineName = $env:COMPUTERNAME; userName = $env:USERNAME; os = [Environment]::OSVersion.VersionString; powershell = $PSVersionTable.PSVersion.ToString(); fileLayer = 'drive_sync' } }
    'screen.capture' { return Capture-Screen $args }
    'window.list' { return @{ ok = $true; windows = @(Window-List) } }
    'window.focus' { return Focus-Window $args }
    'process.list' { return @{ ok = $true; processes = @(Get-Process | Sort-Object ProcessName | Select-Object -First 250 Id,ProcessName,MainWindowTitle | ForEach-Object { @{ pid = $_.Id; processName = $_.ProcessName; title = $_.MainWindowTitle } }) } }
    'process.start' { $p = Start-Process -FilePath ([string]$args.command) -ArgumentList ([string]$args.arguments) -WorkingDirectory $(if ($args.workingDirectory) { [string]$args.workingDirectory } else { $PWD.Path }) -PassThru; return @{ ok = $true; pid = $p.Id; command = [string]$args.command } }
    'process.stop' { Stop-Process -Id ([int]$args.pid) -ErrorAction Stop; return @{ ok = $true; pid = [int]$args.pid; stopped = $true } }
    'input.type' { [System.Windows.Forms.SendKeys]::SendWait((Escape-SendKeys ([string]$args.text))); return @{ ok = $true; chars = ([string]$args.text).Length } }
    'input.key' { Send-Key ([string]$args.key); return @{ ok = $true; key = [string]$args.key } }
    'input.mouse' { return Mouse-Action $args }
    'clipboard.get' { return @{ ok = $true; text = [string](Get-Clipboard -Raw -ErrorAction Stop) } }
    'clipboard.set' { Set-Clipboard -Value ([string]$args.text); return @{ ok = $true; chars = ([string]$args.text).Length } }
    'shell.exec' { $old = $PWD.Path; try { if ($args.workingDirectory) { Set-Location -LiteralPath ([string]$args.workingDirectory) }; $output = & powershell.exe -NoProfile -NonInteractive -Command ([string]$args.command) 2>&1 | Out-String; $code = $LASTEXITCODE; return @{ ok = ($code -eq 0); exitCode = $code; output = $output.Substring(0, [Math]::Min($output.Length, 60000)) } } finally { Set-Location -LiteralPath $old } }
    default { throw "Unsupported action: $action" }
  }
}

function Announce-Worker {
  $cfg = Read-Config
  try { Invoke-HandsApi 'POST' 'lease' | Out-Null } catch { }
}

$cfg = Read-Config
if (-not $cfg.origin -or -not $cfg.workerId -or -not $cfg.token) { throw 'Computer Hands config is incomplete.' }

while ($true) {
  try {
    $leased = Invoke-HandsApi 'POST' 'lease'
    if ($leased.ticket) {
      $ticket = $leased.ticket
      Invoke-HandsApi 'POST' "tickets/$($ticket.ticketId)/heartbeat" @{ phase = 'executing' } | Out-Null
      try { $result = Execute-Action $ticket } catch { $result = @{ ok = $false; error = 'action_failed'; detail = $_.Exception.Message; action = [string]$ticket.action } }
      Invoke-HandsApi 'POST' "tickets/$($ticket.ticketId)/complete" @{ result = $result } | Out-Null
      continue
    }
    Start-Sleep -Seconds $(if ($leased.pollAfterSeconds) { [int]$leased.pollAfterSeconds } else { 3 })
  } catch {
    Start-Sleep -Seconds 5
  }
}
