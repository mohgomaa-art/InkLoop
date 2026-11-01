@echo off
setlocal enabledelayedexpansion

:: Ensure script runs from the repository root directory
cd /d "%~dp0"

:: -----------------------------------------------------------------------------
:: Argument Parsing
:: -----------------------------------------------------------------------------
set "NO_PAUSE=0"
set "ZIP_OUT="

:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="--no-pause" (
    set "NO_PAUSE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="-n" (
    set "NO_PAUSE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="/?" goto :help
if /i "%~1"=="-h" goto :help
if /i "%~1"=="--help" goto :help

if "!ZIP_OUT!"=="" (
    set "ZIP_OUT=%~1"
    shift
    goto :parse_args
)
shift
goto :parse_args
:args_done

title InkLoop Studio - Source Code Packager

echo ======================================================================
echo                  INKLOOP STUDIO - SOURCE PACKAGER
echo        Package pure source code into a clean, lightweight zip
echo ======================================================================
echo.

:: 1. Locate tar.exe (native on Windows 10/11)
set "TAR_EXE="
where tar.exe >nul 2>&1
if not errorlevel 1 set "TAR_EXE=tar.exe"
if "!TAR_EXE!"=="" (
    if exist "%SystemRoot%\System32\tar.exe" set "TAR_EXE=%SystemRoot%\System32\tar.exe"
)

if "!TAR_EXE!"=="" (
    echo [ERROR] Native 'tar.exe' was not found on your system.
    echo Windows 10 [Build 17063+] or Windows 11 includes tar.exe by default.
    echo Please ensure tar.exe is in System32 or on your PATH.
    echo.
    goto :pause_and_exit
)

:: 2. Determine Output File Name
if "!ZIP_OUT!"=="" (
    :: Generate clean timestamp YYYYMMDD_HHMMSS
    for /f "tokens=*" %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss" 2^>nul') do set "TIMESTAMP=%%t"
    if "!TIMESTAMP!"=="" (
        :: Fallback timestamp if PowerShell is unavailable
        set "TIMESTAMP=%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
        set "TIMESTAMP=!TIMESTAMP: =0!"
    )
    set "ZIP_OUT=InkLoop_pure_source_!TIMESTAMP!.zip"
)

:: If output doesn't end with .zip, append it
if /i not "!ZIP_OUT:~-4!"==".zip" (
    set "ZIP_OUT=!ZIP_OUT!.zip"
)

:: 3. Warn / Confirm if destination exists
if exist "!ZIP_OUT!" (
    echo [INFO] Destination archive exists: !ZIP_OUT!
    echo [INFO] Overwriting previous archive with fresh build...
    del /f /q "!ZIP_OUT!" 2>nul
)

echo [INFO] Target archive: !ZIP_OUT!
echo [INFO] Scanning and archiving pure source code...
echo.

:: 4. Execute Native Compression with Strict Exclusions
"!TAR_EXE!" -a -c -f "!ZIP_OUT!" ^
    --exclude *.zip ^
    --exclude *.tar ^
    --exclude *.gz ^
    --exclude *.7z ^
    --exclude *.rar ^
    --exclude .git ^
    --exclude */.git ^
    --exclude */.git/* ^
    --exclude .git/* ^
    --exclude .agents ^
    --exclude */.agents ^
    --exclude */.agents/* ^
    --exclude .agents/* ^
    --exclude .deepread ^
    --exclude */.deepread ^
    --exclude */.deepread/* ^
    --exclude .deepread/* ^
    --exclude node_modules ^
    --exclude */node_modules ^
    --exclude */node_modules/* ^
    --exclude node_modules/* ^
    --exclude .npm ^
    --exclude */.npm ^
    --exclude */.npm/* ^
    --exclude venv ^
    --exclude */venv ^
    --exclude */venv/* ^
    --exclude venv/* ^
    --exclude .venv ^
    --exclude */.venv ^
    --exclude */.venv/* ^
    --exclude .venv/* ^
    --exclude env ^
    --exclude */env ^
    --exclude */env/* ^
    --exclude env/* ^
    --exclude dist ^
    --exclude */dist ^
    --exclude */dist/* ^
    --exclude dist/* ^
    --exclude build ^
    --exclude */build ^
    --exclude */build/* ^
    --exclude build/* ^
    --exclude runs ^
    --exclude */runs ^
    --exclude */runs/* ^
    --exclude runs/* ^
    --exclude scratch ^
    --exclude */scratch ^
    --exclude */scratch/* ^
    --exclude scratch/* ^
    --exclude docs/visual_forensics ^
    --exclude */docs/visual_forensics ^
    --exclude */docs/visual_forensics/* ^
    --exclude docs/visual_forensics/* ^
    --exclude __pycache__ ^
    --exclude */__pycache__ ^
    --exclude */__pycache__/* ^
    --exclude __pycache__/* ^
    --exclude *.pyc ^
    --exclude *.pyo ^
    --exclude *.pyd ^
    --exclude .pytest_cache ^
    --exclude */.pytest_cache ^
    --exclude */.pytest_cache/* ^
    --exclude .pytest_cache/* ^
    --exclude .coverage ^
    --exclude */.coverage ^
    --exclude htmlcov ^
    --exclude */htmlcov ^
    --exclude */htmlcov/* ^
    --exclude .env ^
    --exclude */.env ^
    --exclude .env.*.local ^
    --exclude */.env.*.local ^
    --exclude *.key ^
    --exclude *.pem ^
    --exclude *.secret ^
    --exclude *.token ^
    --exclude *.log ^
    --exclude */*.log ^
    --exclude .vscode ^
    --exclude */.vscode ^
    --exclude */.vscode/* ^
    --exclude .vscode/* ^
    --exclude .idea ^
    --exclude */.idea ^
    --exclude */.idea/* ^
    --exclude .idea/* ^
    --exclude .DS_Store ^
    --exclude */.DS_Store ^
    --exclude Thumbs.db ^
    --exclude */Thumbs.db ^
    --exclude desktop.ini ^
    --exclude */desktop.ini ^
    -C . .

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to create zip archive!
    echo Check disk space and permissions.
    goto :pause_and_exit
)

if not exist "!ZIP_OUT!" (
    echo.
    echo [ERROR] Expected archive was not created: !ZIP_OUT!
    goto :pause_and_exit
)

:: 5. Calculate File Size
for %%A in ("!ZIP_OUT!") do set "ZIP_BYTES=%%~zA"
set /a "ZIP_KB=ZIP_BYTES / 1024"
set /a "ZIP_MB=ZIP_BYTES / 1048576"
set /a "ZIP_DEC=(ZIP_BYTES %% 1048576) * 100 / 1048576"

if %ZIP_DEC% lss 10 set "ZIP_DEC=0%ZIP_DEC%"

echo.
echo ======================================================================
echo                          PACKAGING COMPLETE!
echo ======================================================================
echo [SUCCESS] Source code package created successfully:
echo           File : !ZIP_OUT!
echo           Size : %ZIP_MB%.%ZIP_DEC% MB (%ZIP_BYTES% bytes)
echo.
echo [INCLUDED IN PACKAGE]:
echo   + backend/       : Python FastAPI application, models, tests, catalogues
echo   + frontend/      : React + Vite + TS UI components and styles
echo   + scripts/       : Production runners, benchmark utilities, and tools
echo   + templates/     : Style prompts, comic generation schemas
echo   + assets/        : Fonts, mascot/agent SVGs, and branding
echo   + docs/          : Architecture documentation, specs, and decisions
echo   + Root configs   : package.json, pytest.ini, README.md, run.bat, .env.example
echo.
echo [EXCLUDED (PURE SOURCE GUARANTEE)]:
echo   - Dependencies   : node_modules/, venv/, .venv/, env/, .npm/
echo   - Build outputs  : dist/, build/, *.egg-info/
echo   - Cache / Tests  : __pycache__/, *.pyc, .pytest_cache/, .coverage
echo   - Generated Runs : runs/, backend/runs/, scratch/
echo   - Forensics Media: docs/visual_forensics/ (heavy generated previews)
echo   - Secrets        : .env, *.key, *.pem, *.secret (only .env.example kept)
echo   - Repos / Agents : .git/, .agents/, .deepread/
echo   - System / IDE   : .vscode/, .idea/, .DS_Store, Thumbs.db, *.log, *.zip
echo.
echo [TO RUN EXTRACTED PROJECT]:
echo   1. Copy .env.example to .env and configure keys
echo   2. Double click 'run.bat' (installs deps and launches studio)
echo ======================================================================
echo.

goto :pause_and_exit

:help
echo InkLoop Studio - Pure Source Code Packager
echo.
echo Usage:
echo   zip_source.bat [output_filename.zip] [--no-pause]
echo.
echo Examples:
echo   zip_source.bat
echo     Creates a timestamped archive, e.g. InkLoop_pure_source_20261030_103000.zip
echo.
echo   zip_source.bat my_backup.zip
echo     Creates an archive named 'my_backup.zip' in the project root.
echo.
echo   zip_source.bat "InkLoop_clean.zip"
echo     Creates an archive at the specified custom path.
echo.
echo   zip_source.bat --no-pause
echo     Runs without prompting for keypress upon completion (ideal for CI/scripts).
echo.
exit /b 0

:pause_and_exit
if "%NO_PAUSE%"=="1" exit /b 0
:: Pause if launched by double-clicking in Windows Explorer
echo %cmdcmdline% | findstr /i /c:"/c" >nul
if not errorlevel 1 (
    echo Press any key to close this window...
    pause >nul
)
exit /b 0
