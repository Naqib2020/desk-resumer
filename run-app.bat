@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Running setup-windows.bat first...
    call setup-windows.bat
)

call venv\Scripts\activate
echo ============================================================
echo   Starting DeskResumer Studio Desktop UI
echo ============================================================
python -m desk_resumer.cli app
pause
