from pathlib import Path

path = Path('computer-hands/windows/home-center-hands.ps1')
text = path.read_text(encoding='utf-8-sig')
original = text

replacements = [
    (
        "  $secure = Get-Content -LiteralPath $Cfg.tokenPath -Raw | ConvertTo-SecureString",
        "  $serialized = (Get-Content -LiteralPath $Cfg.tokenPath -Raw).Trim()\n  $secure = $serialized | ConvertTo-SecureString",
    ),
    (
        "    [uint32]$pid = 0; [void][HomeCenterHandsNative]::GetWindowThreadProcessId($hwnd, [ref]$pid)\n    $name = ''; try { $name = (Get-Process -Id $pid -ErrorAction Stop).ProcessName } catch {}\n    $rows.Add([pscustomobject]@{handle=$hwnd.ToInt64(); pid=$pid; process=$name; title=$title}); return $true",
        "    [uint32]$windowProcessId = 0; [void][HomeCenterHandsNative]::GetWindowThreadProcessId($hwnd, [ref]$windowProcessId)\n    $name = ''; try { $name = (Get-Process -Id $windowProcessId -ErrorAction Stop).ProcessName } catch {}\n    $rows.Add([pscustomobject]@{handle=$hwnd.ToInt64(); pid=$windowProcessId; process=$name; title=$title}); return $true",
    ),
]

for before, after in replacements:
    if before not in text:
        raise SystemExit(f'expected source block missing: {before[:100]!r}')
    text = text.replace(before, after, 1)

marker = "function Focus-Window([object]$Args) {"
if marker not in text:
    raise SystemExit('Focus-Window marker missing')
helper = r'''function Get-ActionArg([object]$ActionArgs, [string]$Name, $Default = $null) {
  if ($null -eq $ActionArgs) { return $Default }
  $property = $ActionArgs.PSObject.Properties[$Name]
  if ($null -eq $property) { return $Default }
  if ($null -eq $property.Value) { return $Default }
  return $property.Value
}

'''
text = text.replace(marker, helper + "function Focus-Window([object]$ActionArgs) {", 1)

text = text.replace(
    "  if ($Args.pid) { $target = $windows | Where-Object { $_.pid -eq [int]$Args.pid } | Select-Object -First 1 }\n  elseif ($Args.title) { $needle=[string]$Args.title; $target=$windows | Where-Object { $_.title -like \"*$needle*\" } | Select-Object -First 1 }",
    "  $requestedPid = Get-ActionArg $ActionArgs 'pid' $null\n  $requestedTitle = [string](Get-ActionArg $ActionArgs 'title' '')\n  if ($null -ne $requestedPid) { $target = $windows | Where-Object { $_.pid -eq [int]$requestedPid } | Select-Object -First 1 }\n  elseif ($requestedTitle) { $needle=$requestedTitle; $target=$windows | Where-Object { $_.title -like \"*$needle*\" } | Select-Object -First 1 }",
    1,
)

text = text.replace("function Capture-Screen([object]$Args) {", "function Capture-Screen([object]$ActionArgs) {", 1)
text = text.replace(
    "    $maxWidth=if($Args.maxWidth){[int]$Args.maxWidth}else{1280}; $quality=if($Args.quality){[int64]$Args.quality}else{55}",
    "    $maxWidth=[int](Get-ActionArg $ActionArgs 'maxWidth' 1280); $quality=[int64](Get-ActionArg $ActionArgs 'quality' 55)",
    1,
)

text = text.replace("function Invoke-Mouse([object]$Args) {", "function Invoke-Mouse([object]$ActionArgs) {", 1)
text = text.replace(
    "  [void][HomeCenterHandsNative]::SetCursorPos([int]$Args.x,[int]$Args.y);$event=if($Args.event){([string]$Args.event).ToLowerInvariant()}else{'click'};$button=if($Args.button){([string]$Args.button).ToLowerInvariant()}else{'left'}",
    "  $x=[int](Get-ActionArg $ActionArgs 'x' 0);$y=[int](Get-ActionArg $ActionArgs 'y' 0);$event=([string](Get-ActionArg $ActionArgs 'event' 'click')).ToLowerInvariant();$button=([string](Get-ActionArg $ActionArgs 'button' 'left')).ToLowerInvariant();[void][HomeCenterHandsNative]::SetCursorPos($x,$y)",
    1,
)
text = text.replace(
    "  return @{ok=$true;x=[int]$Args.x;y=[int]$Args.y;button=$button;event=$event}",
    "  return @{ok=$true;x=$x;y=$y;button=$button;event=$event}",
    1,
)

text = text.replace("function Run-Shell([object]$Args) {", "function Run-Shell([object]$ActionArgs) {", 1)
text = text.replace(
    "  $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes([string]$Args.command))",
    "  $command=[string](Get-ActionArg $ActionArgs 'command' ''); if(-not $command){throw 'shell.exec command was missing from the leased ticket.'};$encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))",
    1,
)
text = text.replace(
    "  if($Args.workingDirectory){$psi.WorkingDirectory=[string]$Args.workingDirectory};$psi.UseShellExecute=$false;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.CreateNoWindow=$true",
    "  $workingDirectory=[string](Get-ActionArg $ActionArgs 'workingDirectory' '');if($workingDirectory){$psi.WorkingDirectory=$workingDirectory};$psi.UseShellExecute=$false;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.CreateNoWindow=$true",
    1,
)

old_start = "    'process.start'{$sp=@{FilePath=[string]$a.command;PassThru=$true};if($a.arguments){$sp.ArgumentList=[string]$a.arguments};if($a.workingDirectory){$sp.WorkingDirectory=[string]$a.workingDirectory};$p=Start-Process @sp;return @{ok=$true;pid=$p.Id;name=$p.ProcessName}}"
new_start = "    'process.start'{$command=[string](Get-ActionArg $a 'command' '');if(-not $command){throw 'process.start command was missing from the leased ticket.'};$sp=@{FilePath=$command;PassThru=$true};$processArguments=[string](Get-ActionArg $a 'arguments' '');$workingDirectory=[string](Get-ActionArg $a 'workingDirectory' '');if($processArguments){$sp.ArgumentList=$processArguments};if($workingDirectory){$sp.WorkingDirectory=$workingDirectory};$p=Start-Process @sp;return @{ok=$true;pid=$p.Id;name=$p.ProcessName}}"
if old_start not in text:
    raise SystemExit('process.start block missing')
text = text.replace(old_start, new_start, 1)

# Guard against reintroducing the known PowerShell automatic-variable collisions.
for forbidden in ("[uint32]$pid = 0", "function Capture-Screen([object]$Args)", "function Run-Shell([object]$Args)", "function Invoke-Mouse([object]$Args)"):
    if forbidden in text:
        raise SystemExit(f'forbidden legacy pattern remains: {forbidden}')

if text == original:
    raise SystemExit('patch made no changes')
path.write_text(text, encoding='utf-8', newline='\n')
print('patched', path)
