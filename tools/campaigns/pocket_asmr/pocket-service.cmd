@echo off
setlocal EnableExtensions
set "ROOT=%USERPROFILE%\PocketASMRGit\tools\campaigns\pocket_asmr"
set "PY=py -3"
set "PIDFILE=%USERPROFILE%\PocketASMR\gateway.pid"
set "TOKEN=%USERPROFILE%\PocketASMR\gateway-token.txt"
if /I "%~1"=="install" goto install
if /I "%~1"=="on" goto on
if /I "%~1"=="off" goto off
if /I "%~1"=="status" goto status
echo Usage: pocket-service.cmd install^|on^|off^|status
exit /b 2
:install
if not exist "%ROOT%\asmr_api.py" (echo BLOCKED: Git campaign unavailable & exit /b 2)
if not exist "%USERPROFILE%\PocketASMR" mkdir "%USERPROFILE%\PocketASMR"
if not exist "%TOKEN%" (
  echo BLOCKED: gateway token absent. Provision privately before starting.
  exit /b 2
)
echo INSTALLED=source_ready
exit /b 0
:on
if not exist "%TOKEN%" (echo BLOCKED: gateway token absent & exit /b 2)
if not exist "%ROOT%\asmr_api.py" (echo BLOCKED: gateway not installed & exit /b 2)
netstat -ano | findstr /C:":10215 " | findstr /C:"LISTENING" >nul && (echo GATEWAY=already_listening & exit /b 0)
start "Ritsu Pocket ASMR Gateway" /MIN cmd /c "cd /d \"%ROOT%\" && py -3 asmr_api.py"
echo START_REQUESTED=1
exit /b 0
:off
echo BLOCKED: safe ownership-based shutdown not implemented; refusing to terminate unidentified listeners
exit /b 2
:status
netstat -ano | findstr /C:":10215 " | findstr /C:"LISTENING" >nul
if errorlevel 1 (echo GATEWAY=not_listening & exit /b 1)
echo GATEWAY=listening
exit /b 0
