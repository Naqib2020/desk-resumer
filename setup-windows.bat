@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   DeskResumer - Windows Automated Setup
echo ============================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10 or newer from python.org
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
python --version

:: 2. Create virtual environment if not present
if not exist "venv\" (
    echo [2/4] Creating virtual environment (venv)...
    python -m venv venv
) else (
    echo [2/4] Virtual environment (venv) already exists.
)

:: 3. Install package and dependencies
echo [3/4] Installing dependencies and pywinauto for Windows...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .[windows]

:: 4. Copy configuration
if not exist "config.yaml" (
    echo [4/4] Creating config.yaml from config.example.yaml...
    copy config.example.yaml config.yaml >nul
    echo Config created. Remember to edit config.yaml to configure your alerts!
) else (
    echo [4/4] config.yaml already exists.
)

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo Quick commands:
echo   • Test window detection:   venv\Scripts\python -m desk_resumer.cli test-detect
echo   • Run watchdog:            venv\Scripts\python -m desk_resumer.cli watch --queue TASKS.md
echo   • Check checklist:         venv\Scripts\python -m desk_resumer.cli queue-status
echo   • Double click:            run-windows.bat
echo.
pause
