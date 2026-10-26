@echo off
setlocal EnableExtensions
set "ROOT=%USERPROFILE%\PocketASMRGit\tools\campaigns\pocket_asmr"
set "HOME_DIR=%USERPROFILE%\PocketASMR"
set "TOKEN=%USERPROFILE%\PocketASMR\gateway-token.txt"
set "TASK=Ritsu Pocket ASMR Gateway"
if /I "%~1"=="install" goto install
if /I "%~1"=="on" goto on
if /I "%~1"=="off" goto off
if /I "%~1"=="status" goto status
echo Usage: pocket-service.cmd install^|on^|off^|status
exit /b 2
:install
if not exist "%ROOT%\asmr_api.py" (echo BLOCKED: Git campaign unavailable & exit /b 2)
if not exist "%HOME_DIR%" mkdir "%HOME_DIR%"
if not exist "%TOKEN%" (
  py -3 -c "import pathlib,secrets;pathlib.Path(r'%USERPROFILE%\PocketASMR\gateway-token.txt').write_text(secrets.token_urlsafe(32))"
  if errorlevel 1 exit /b 2
)
schtasks /query /tn "%TASK%" >nul 2>nul
if errorlevel 1 (
  schtasks /create /f /sc ONLOGON /tn "%TASK%" /tr "py -3 %ROOT%\asmr_api.py" /rl LIMITED
  if errorlevel 1 exit /b 2
  schtasks /change /tn "%TASK%" /disable >nul
)
echo INSTALLED=1
exit /b 0
:on
schtasks /change /tn "%TASK%" /enable >nul
if errorlevel 1 exit /b 2
schtasks /run /tn "%TASK%"
if errorlevel 1 exit /b 2
echo GATEWAY=start_requested
exit /b 0
:off
schtasks /end /tn "%TASK%" >nul 2>nul
schtasks /change /tn "%TASK%" /disable >nul
if errorlevel 1 exit /b 2
echo GATEWAY=stop_requested
exit /b 0
:status
schtasks /query /tn "%TASK%" /fo LIST
exit /b %ERRORLEVEL%
