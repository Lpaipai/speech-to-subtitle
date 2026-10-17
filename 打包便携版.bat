@echo off
setlocal
cd /d "%~dp0"
set TEMP=%~dp0.tmp
set TMP=%TEMP%
set PYINSTALLER_CONFIG_DIR=%~dp0.tmp\pyinstaller
if not exist "%TEMP%" mkdir "%TEMP%"
".venv\Scripts\pyinstaller.exe" speech-to-subtitle.spec --noconfirm --distpath dist\v0.1.1 --workpath build\v0.1.1
if errorlevel 1 exit /b %errorlevel%
copy /y README.md "dist\v0.1.1\speech-to-subtitle\README.md" >nul
if not exist "dist\v0.1.1\speech-to-subtitle\docs" mkdir "dist\v0.1.1\speech-to-subtitle\docs"
xcopy /e /i /y "docs" "dist\v0.1.1\speech-to-subtitle\docs" >nul
if not exist "dist\v0.1.1\speech-to-subtitle\models" mkdir "dist\v0.1.1\speech-to-subtitle\models"
xcopy /e /i /y "models\tiny" "dist\v0.1.1\speech-to-subtitle\models\tiny" >nul
if exist "dist\speech-to-subtitle-v0.1.1.7z" del /q "dist\speech-to-subtitle-v0.1.1.7z"
D:\Tools\7-Zip\7zr.exe a -t7z "dist\speech-to-subtitle-v0.1.1.7z" ".\dist\v0.1.1\speech-to-subtitle\*" -xr!.tmp -mx=3
