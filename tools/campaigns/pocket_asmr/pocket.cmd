@echo off
setlocal
REM Windows alias when this folder is on PATH (or pocket.cmd is copied to a PATH directory).
REM Prefer the project Python if present; otherwise use py -3.
if exist "C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\.venv\Scripts\python.exe" (
  "C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\.venv\Scripts\python.exe" "%~dp0pocket.py" %*
) else (
  py -3 "%~dp0pocket.py" %*
)
exit /b %errorlevel%
