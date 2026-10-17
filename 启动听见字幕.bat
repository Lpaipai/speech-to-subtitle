@echo off
setlocal
cd /d "%~dp0"
set TEMP=%~dp0.tmp
set TMP=%TEMP%
set HF_HOME=%~dp0models\.cache
set HF_HUB_CACHE=%~dp0models\.cache\hub
set HF_HUB_DISABLE_XET=1
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
if not exist "%TEMP%" mkdir "%TEMP%"
".venv\Scripts\python.exe" -m speech_to_subtitle
if errorlevel 1 pause
