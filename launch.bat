@echo off
setlocal EnableDelayedExpansion

:: ── Job Radar Launcher (Windows) ─────────────────────────────────────────────
:: Double-click this file to start Job Radar and open it in your browser.
:: Close this window (or press Ctrl+C) to stop the server.
:: ─────────────────────────────────────────────────────────────────────────────

set "DIR=%~dp0"
cd /d "%DIR%"

:: ── Python resolution ─────────────────────────────────────────────────────────
if exist "%DIR%venv\Scripts\python.exe" (
    set "PYTHON=%DIR%venv\Scripts\python.exe"
    set "PIP=%DIR%venv\Scripts\pip.exe"
    echo Using virtual environment
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON=python"
        set "PIP=pip"
    ) else (
        where python3 >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON=python3"
            set "PIP=pip3"
        ) else (
            echo.
            echo ERROR: Python 3 not found.
            echo Install Python 3.10+ from https://www.python.org/downloads/
            echo or run install.bat to set up a virtual environment.
            echo.
            pause
            exit /b 1
        )
    )
    echo No venv found -- using system Python
    echo Run install.bat once for a cleaner setup.
)

:: ── Dependency check ──────────────────────────────────────────────────────────
echo Checking dependencies...
"!PYTHON!" -c "import flask, feedparser, requests, bs4, lxml, docx" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    "!PIP!" install -r requirements.txt --quiet
    if errorlevel 1 (
        echo.
        echo ERROR: Dependency install failed.
        echo Try running install.bat or manually run:
        echo   pip install flask feedparser requests beautifulsoup4 lxml python-docx
        echo.
        pause
        exit /b 1
    )
)

:: ── Read port from config ─────────────────────────────────────────────────────
for /f "tokens=*" %%p in (
    '"!PYTHON!" -c "import json,sys; cfg=json.load(open(\"config.json\")); print(cfg.get(\"app\",{}).get(\"port\",5000))" 2^>nul'
) do set "PORT=%%p"

if "!PORT!"=="" set "PORT=5000"

:: ── Open browser after a short delay (non-blocking) ─────────────────────────
:: Launches a hidden PowerShell timer — browser opens once server is ready.
:: This runs in the background and exits on its own; it does not stay running.
powershell -NoProfile -WindowStyle Hidden -Command ^
  "Start-Sleep 3; Start-Process 'http://127.0.0.1:!PORT!'" >nul 2>&1

:: ── Start server in the FOREGROUND ───────────────────────────────────────────
:: Running Python directly (not via "start /b") means the server process is
:: owned by this window. Closing the window — by any method — stops the server.
:: No background processes are left behind.
echo Starting Job Radar on port !PORT!...
echo.
echo Job Radar will open in your browser in a moment.
echo Close this window to stop the server.
echo.
"!PYTHON!" app.py
