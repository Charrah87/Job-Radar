@echo off
setlocal EnableDelayedExpansion

:: ── Job Radar — One-time Setup (Windows) ─────────────────────────────────────
:: Run this once after downloading to:
::   1. Create a Python virtual environment
::   2. Install all dependencies
::   3. Create a Desktop shortcut
::
:: Usage: Double-click install.bat
:: ─────────────────────────────────────────────────────────────────────────────

set "DIR=%~dp0"
cd /d "%DIR%"

echo.
echo ---------------------------------------------
echo   Job Radar -- Setup
echo ---------------------------------------------
echo.

:: ── Step 1: Find Python ──────────────────────────────────────────────────────
set "PYTHON="
where python >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
    set "PYTHON=python"
    set "PIP=pip"
)

if "!PYTHON!"=="" (
    where python3 >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON=python3"
        set "PIP=pip3"
    )
)

if "!PYTHON!"=="" (
    echo ERROR: Python 3 not found.
    echo.
    echo Install Python 3.10 or higher from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, check the box that says
    echo "Add Python to PATH" before clicking Install.
    echo.
    echo After installing Python, re-run this script.
    echo.
    pause
    exit /b 1
)

echo Found: !PYVER!

:: ── Step 2: Virtual environment ──────────────────────────────────────────────
if exist "%DIR%venv\Scripts\python.exe" (
    echo Virtual environment already exists -- skipping creation.
) else (
    echo Creating virtual environment...
    "!PYTHON!" -m venv "%DIR%venv"
    if errorlevel 1 (
        echo ERROR: Could not create virtual environment.
        echo Make sure Python 3.10+ is installed correctly.
        pause
        exit /b 1
    )
    echo Done.
)

set "VENV_PYTHON=%DIR%venv\Scripts\python.exe"
set "VENV_PIP=%DIR%venv\Scripts\pip.exe"

:: ── Step 3: Install dependencies ─────────────────────────────────────────────
echo Installing dependencies...
"%VENV_PIP%" install --upgrade pip --quiet
"%VENV_PIP%" install -r "%DIR%requirements.txt" --quiet
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    echo Try running this script again, or manually run:
    echo   pip install flask feedparser requests beautifulsoup4 lxml python-docx
    pause
    exit /b 1
)
echo Done.

:: ── Step 4: Create Desktop shortcut ─────────────────────────────────────────
set "SHORTCUT=%USERPROFILE%\Desktop\Job Radar.lnk"
set "TARGET=%DIR%launch.bat"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%SHORTCUT%'); ^
   $s.TargetPath = 'cmd.exe'; ^
   $s.Arguments = '/c \"%TARGET%\"'; ^
   $s.WorkingDirectory = '%DIR%'; ^
   $s.WindowStyle = 1; ^
   $s.Description = 'Launch Job Radar'; ^
   $s.Save()" >nul 2>&1

if exist "%SHORTCUT%" (
    echo Desktop shortcut created: Job Radar
) else (
    echo Could not create Desktop shortcut.
    echo You can launch the app by double-clicking launch.bat directly.
)

echo.
echo ---------------------------------------------
echo   Setup complete!
echo.
echo   Next steps:
echo   1. Edit config.json with your Google Alert RSS URLs
echo      and the path to your resume .docx file.
echo   2. Double-click "Job Radar" on your Desktop
echo      ^(or double-click launch.bat in this folder^).
echo ---------------------------------------------
echo.
pause
