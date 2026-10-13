@echo off
setlocal EnableDelayedExpansion
title Pali TTS - Windows Installer
set "SELF=%~f0"

echo === Pali TTS - Windows Installer ===
echo.

:: ── 0. Install scope ─────────────────────────────────────────────────────────
set SCOPE=1

if /i "%~1"=="allusers" (
    set SCOPE=2
    goto :check_python
)

echo Install for:
echo   1) Just me    ^(default, no admin needed^)
echo   2) All users  ^(requires Administrator^)
echo.
set /p SCOPE_INPUT=Enter 1 or 2 [1]:
if not "!SCOPE_INPUT!"=="" set SCOPE=!SCOPE_INPUT!

if "!SCOPE!"=="2" (
    net session >nul 2>&1
    if !errorlevel! neq 0 (
        echo Requesting administrator privileges...
        powershell -Command "Start-Process '!SELF!' -ArgumentList 'allusers' -Verb RunAs -Wait"
        exit /b
    )
)

:check_python
if "!SCOPE!"=="2" (
    set "INSTALL_DIR=%ProgramFiles%\PaliTTS"
    set "STARTUP=%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup"
    set "DESKTOP=%PUBLIC%\Desktop"
    echo Installing for all users...
) else (
    set "INSTALL_DIR=%LOCALAPPDATA%\PaliTTS"
    set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
    set "DESKTOP=%USERPROFILE%\Desktop"
    echo Installing for current user...
)
echo.

:: ── 1. Check Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3 from python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo Python: %%v

:: ── 2. Install Python packages ───────────────────────────────────────────────
echo.
echo Installing Python packages...
python -m pip install --quiet edge-tts "playsound==1.2.2"
if errorlevel 1 (
    echo ERROR: Package installation failed. Check your internet connection.
    pause
    exit /b 1
)
echo Packages installed.

:: ── 3. Copy script to install location ───────────────────────────────────────
echo.
echo Installing to !INSTALL_DIR!...
if not exist "!INSTALL_DIR!" mkdir "!INSTALL_DIR!"
copy /Y "%~dp0pali_tts.py" "!INSTALL_DIR!\pali_tts.py" >nul

:: ── 4. Build the .exe ────────────────────────────────────────────────────────
echo.
echo Building pali_tts.exe (this takes a minute)...
python -m pip install --quiet pyinstaller
pyinstaller --onefile --noconsole ^
    --hidden-import playsound ^
    --hidden-import edge_tts ^
    --name pali_tts ^
    "!INSTALL_DIR!\pali_tts.py" ^
    --distpath "!INSTALL_DIR!" ^
    --workpath "%TEMP%\pali_tts_build" ^
    --specpath "%TEMP%\pali_tts_build" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to build exe.
    pause
    exit /b 1
)
echo pali_tts.exe built.

:: ── 5. Copy AHK script ───────────────────────────────────────────────────────
copy /Y "%~dp0pali_tts.ahk" "!INSTALL_DIR!\pali_tts.ahk" >nul

:: ── 6. Check for AutoHotkey ───────────────────────────────────────────────────
echo.
set AHK=
where AutoHotkey >nul 2>&1
if not errorlevel 1 (
    set AHK=AutoHotkey
) else if exist "%ProgramFiles%\AutoHotkey\AutoHotkey.exe" (
    set "AHK=%ProgramFiles%\AutoHotkey\AutoHotkey.exe"
) else if exist "%ProgramFiles(x86)%\AutoHotkey\AutoHotkey.exe" (
    set "AHK=%ProgramFiles(x86)%\AutoHotkey\AutoHotkey.exe"
)

if "!AHK!"=="" (
    echo AutoHotkey not found. Please install AutoHotkey v1 from https://www.autohotkey.com
    echo Then double-click: "!INSTALL_DIR!\pali_tts.ahk"
    goto :shortcut
)

:: ── 7. Add AHK to startup ─────────────────────────────────────────────────────
copy /Y "!INSTALL_DIR!\pali_tts.ahk" "!STARTUP!\pali_tts.ahk" >nul
echo Added to startup.

if "!SCOPE!"=="1" (
    "!AHK!" "!INSTALL_DIR!\pali_tts.ahk"
    echo AutoHotkey script started.
) else (
    echo Log out and back in to activate Win+P for all users,
    echo or double-click "!INSTALL_DIR!\pali_tts.ahk" to start now.
)

:shortcut
:: ── 8. Create desktop shortcut ───────────────────────────────────────────────
echo.
echo Creating desktop shortcut...
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $s = $ws.CreateShortcut('!DESKTOP!\Pali TTS.lnk'); ^
     $s.TargetPath = '!INSTALL_DIR!\pali_tts.ahk'; ^
     $s.Description = 'Pali TTS'; ^
     $s.Save()"

echo.
echo === Installation complete! ===
echo.
echo Usage:
echo   Select any Pali text in any application, press Win+P.
echo   Or right-click the tray icon in the bottom-right corner.
echo   A window appears - paste/edit text, choose voice and speed, press Play.
echo.
echo   Requires internet (aksharamukha + Microsoft TTS).
echo.
pause
