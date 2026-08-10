from pathlib import Path

p = Path('computer-hands/windows/repair.ps1')
s = p.read_text(encoding='utf-8')

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'missing repair anchor: {label}')
    s = s.replace(old, new, 1)

def ensure_replace(old, new, label):
    global s
    if new in s:
        return
    once(old, new, label)

ensure_replace("$WorkerPath = Join-Path $Root 'home-center-hands.ps1'\n$LaunchPath = Join-Path $Root 'launch.ps1'", "$WorkerPath = Join-Path $Root 'home-center-hands.ps1'\n$WatchdogPath = Join-Path $Root 'watchdog.ps1'\n$LaunchPath = Join-Path $Root 'launch.ps1'", 'watchdog path')
ensure_replace("$TaskName = 'HomeCenterComputerHands'", "$TaskName = 'HomeCenterComputerHands'\n$WatchdogTaskName = 'HomeCenterComputerHandsWatchdog'", 'watchdog task')
watchdog_fetch = "$workerText | Set-Content -LiteralPath $WorkerPath -Encoding UTF8\n$watchdogText = & git -C $RepoPath show 'origin/main:computer-hands/windows/watchdog.ps1'\nif ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($watchdogText -join \"`n\"))) { throw 'Could not read watchdog from origin/main.' }\n$watchdogText | Set-Content -LiteralPath $WatchdogPath -Encoding UTF8"
ensure_replace("$workerText | Set-Content -LiteralPath $WorkerPath -Encoding UTF8", watchdog_fetch, 'watchdog fetch')
ensure_replace("$secure = Get-Content -LiteralPath $TokenPath -Raw | ConvertTo-SecureString", "$secure = (Get-Content -LiteralPath $TokenPath -Raw).Trim() | ConvertTo-SecureString", 'token trim')
anchor = "Start-ScheduledTask -TaskName $TaskName\nStart-Sleep -Seconds 6"
replacement = r'''Start-ScheduledTask -TaskName $TaskName

$watchdogArg = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$WatchdogPath`" -ConfigPath `"$ConfigPath`" -TaskName `"$TaskName`""
$watchdogAction = New-ScheduledTaskAction -Execute $ps -Argument $watchdogArg
Stop-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $WatchdogTaskName -Action $watchdogAction -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $WatchdogTaskName
Start-Sleep -Seconds 6'''
if '$watchdogAction = New-ScheduledTaskAction' not in s:
    once(anchor, replacement, 'watchdog register')
if 'watchdogState = [string](Get-ScheduledTask -TaskName $WatchdogTaskName).State' not in s:
    once("  taskState = [string]$task.State", "  taskState = [string]$task.State\n  watchdogState = [string](Get-ScheduledTask -TaskName $WatchdogTaskName).State\n  watchdogPath = $WatchdogPath", 'result evidence')
p.write_text(s, encoding='utf-8')
print('repair watchdog v3.3 patch applied')
