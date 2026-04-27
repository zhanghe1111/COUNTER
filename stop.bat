@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   Stop Counter App Services
echo ========================================
echo.

taskkill /F /FI "WINDOWTITLE eq Counter-Backend*" >nul 2>&1 && echo   Backend closed
taskkill /F /FI "WINDOWTITLE eq Counter-Frontend*" >nul 2>&1 && echo   Frontend closed

echo.
echo ========================================
echo   Done
echo ========================================
pause
