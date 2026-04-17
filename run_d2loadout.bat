@echo off
REM Use ASCII-only in this file: UTF-8/Cyrillic breaks cmd.exe parsing when run from PowerShell.
setlocal enabledelayedexpansion

echo ================================================================
echo   Dota 2 Loadout Generator
echo   Fetch D2PT data and build hero grid configs
echo ================================================================
echo.

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install 3.8+ from https://www.python.org/downloads/
    echo Enable "Add Python to PATH" during install.
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo OK Python !PYTHON_VERSION!
)

if exist "..\requirements.txt" (
    cd ..
)

echo.
echo Checking venv...
if not exist "venv" (
    echo Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: venv creation failed
        pause
        exit /b 1
    )
    echo OK venv created
) else (
    echo OK venv exists
)

echo.
echo Activating venv...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: activate.bat failed
    pause
    exit /b 1
)

echo.
echo Checking dependencies...
python -c "import selenium" >nul 2>&1
if errorlevel 1 (
    echo Installing requirements...
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: pip install failed
        pause
        exit /b 1
    )
    echo OK dependencies installed
) else (
    echo OK dependencies present
)

echo.
echo Note: Chrome is only needed for legacy: python main.py --scrape-all

echo.
echo ================================================================
echo   Running main.py - D2PT API + configs
echo ================================================================
echo.

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python main.py

if errorlevel 1 (
    echo.
    echo ERROR: main.py exited with errors
    echo Legacy scrape hint: python main.py --no-headless --debug --scrape-all
    echo.
) else (
    echo.
    echo OK: open Dota 2 and check hero loadout configs
    echo.
)

echo Press any key to exit...
pause >nul
