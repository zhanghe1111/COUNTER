@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   Reset Database (Keep Users)
echo ========================================
echo.

if not exist "backend\venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Run start.bat first.
    pause
    exit /b 1
)

call backend\venv\Scripts\python.exe reset_db.py

pause
