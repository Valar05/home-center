@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0ritsu.ps1" %*
exit /b %errorlevel%
