@echo off
setlocal EnableDelayedExpansion

:: ── Job Radar — Updater (Windows) ────────────────────────────────────────────
:: Pulls the latest code while preserving your personal data files.
::
:: Safe to run at any time. Your config.json and jobs.json are never overwritten.
::
:: Usage: Double-click update.bat
:: ─────────────────────────────────────────────────────────────────────────────

set "DIR=%~dp0"
cd /d "%DIR%"

echo.
echo ---------------------------------------------
echo   Job Radar -- Update
echo ---------------------------------------------
echo.

:: ── Show current version ──────────────────────────────────────────────────────
set "CURRENT_VERSION=unknown"
if exist "%DIR%VERSION" (
    set /p CURRENT_VERSION=<"%DIR%VERSION"
    set "CURRENT_VERSION=!CURRENT_VERSION: =!"
)
echo Current version: !CURRENT_VERSION!

:: ── Detect install method ─────────────────────────────────────────────────────
git -C "%DIR%" rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo.
    echo This installation was not set up with Git ^(you downloaded a ZIP^).
    echo.
    echo To update:
    echo   1. Download the latest ZIP from GitHub.
    echo   2. Extract it to a new folder.
    echo   3. Copy your personal files into the new folder:
    echo        config.json   ^<-- your Google Alert URLs, resume path, and settings
    echo        jobs.json     ^<-- your saved jobs and notes ^(if it exists^)
    echo   4. Run install.bat in the new folder.
    echo.
    echo Your data files will not be affected.
    echo.
    pause
    exit /b 0
)

:: ── Back up personal data files ───────────────────────────────────────────────
echo Backing up your personal data files...

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set "DATESTAMP=%%c%%a%%b"
for /f "tokens=1-3 delims=:. " %%a in ("%time%") do set "TIMESTAMP=%%a%%b%%c"
set "BACKUP_DIR=%DIR%.update_backup_%DATESTAMP%_%TIMESTAMP%"
mkdir "%BACKUP_DIR%" >nul 2>&1

if exist "%DIR%config.json" (
    copy /y "%DIR%config.json" "%BACKUP_DIR%\config.json" >nul
    echo   config.json backed up
)
if exist "%DIR%jobs.json" (
    copy /y "%DIR%jobs.json" "%BACKUP_DIR%\jobs.json" >nul
    echo   jobs.json backed up
)

:: ── Pull latest code ──────────────────────────────────────────────────────────
echo.
echo Pulling latest changes...

git stash --quiet >nul 2>&1

git pull --ff-only origin main
if errorlevel 1 (
    echo.
    echo ERROR: Could not pull updates.
    echo Check your internet connection or visit GitHub to download
    echo the latest release manually.
    git stash pop --quiet >nul 2>&1
    pause
    exit /b 1
)

:: ── Restore personal data files ───────────────────────────────────────────────
if exist "%BACKUP_DIR%\config.json" (
    copy /y "%BACKUP_DIR%\config.json" "%DIR%config.json" >nul
)
if exist "%BACKUP_DIR%\jobs.json" (
    copy /y "%BACKUP_DIR%\jobs.json" "%DIR%jobs.json" >nul
)
echo Your personal data files restored.

rmdir /s /q "%BACKUP_DIR%" >nul 2>&1

:: ── Update dependencies ───────────────────────────────────────────────────────
echo.
echo Updating dependencies...
if exist "%DIR%venv\Scripts\pip.exe" (
    "%DIR%venv\Scripts\pip.exe" install -r "%DIR%requirements.txt" --quiet
    echo Dependencies updated.
) else (
    echo   ^(No venv found -- run install.bat if you see import errors.^)
)

:: ── Show result ───────────────────────────────────────────────────────────────
set "NEW_VERSION=unknown"
if exist "%DIR%VERSION" (
    set /p NEW_VERSION=<"%DIR%VERSION"
    set "NEW_VERSION=!NEW_VERSION: =!"
)

echo.
echo ---------------------------------------------
if "!CURRENT_VERSION!" neq "!NEW_VERSION!" (
    echo   Updated: !CURRENT_VERSION! --^> !NEW_VERSION!
) else (
    echo   Already up to date ^(!CURRENT_VERSION!^).
)
echo.
echo   Launch Job Radar as normal -- no re-install needed.
echo ---------------------------------------------
echo.
pause
