@echo off
setlocal

cd /d "%~dp0"

echo ============================================================
echo   Building DeskResumer Native Windows System Tray App
echo ============================================================
echo.

where dotnet >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] .NET SDK is not installed or not in PATH!
    echo Please install .NET 8 SDK from https://dot.net
    pause
    exit /b 1
)

dotnet build DeskResumerTray.csproj -c Release -o bin\Release
if %errorlevel% equ 0 (
    echo.
    echo ✅ DeskResumerTray.exe built successfully!
    echo Location: apps\windows-tray\bin\Release\DeskResumerTray.exe
    echo Double-click to run native system tray app.
) else (
    echo ❌ Build failed.
)

pause
