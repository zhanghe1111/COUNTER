@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   Start Counter App Services
echo ========================================
echo.

REM ----- Backend -----
echo [1/2] Starting Backend (FastAPI) ...

if not exist "backend\venv\Scripts\python.exe" (
    echo       venv not found, creating...
    pushd backend
    python -m venv venv
    call venv\Scripts\pip install -r requirements.txt
    popd
)

if not exist "logs" mkdir logs

start "Counter-Backend" /MIN /D "%cd%\backend" "%cd%\backend\venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
echo       FastAPI starting on http://localhost:8000

timeout /t 4 /nobreak >nul

REM ----- Frontend -----
echo [2/2] Starting Frontend (Vite) ...

if not exist "frontend\node_modules" (
    echo       node_modules not found, installing...
    pushd frontend
    call npm install
    popd
)

start "Counter-Frontend" /MIN /D "%cd%\frontend" node "%cd%\frontend\node_modules\vite\bin\vite.js" --port 3001
echo       Vite starting on http://localhost:3001

echo.
echo ========================================
echo   Both services starting up!
echo   Backend : http://localhost:8000
echo   Frontend: http://localhost:3001
echo   Close   : run stop.bat
echo ========================================
echo.
