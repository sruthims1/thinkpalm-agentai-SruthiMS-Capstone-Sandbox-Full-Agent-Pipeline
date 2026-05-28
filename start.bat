@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo  MaritimeTestAI - Starting Services
echo ============================================

REM Store project root (with trailing backslash)
set "ROOT=%~dp0"

REM Check for .env file
if not exist "%ROOT%.env" (
    echo [WARN] .env not found. Creating template...
    echo GROQ_API_KEY=gsk_your_key_here>"%ROOT%.env"
    echo OPENROUTER_API_KEY=>>"%ROOT%.env"
    echo [ACTION REQUIRED] Edit .env and set your GROQ_API_KEY, then re-run.
    pause
    exit /b 1
)

REM Parse GROQ_API_KEY from .env
for /f "tokens=1,* delims==" %%a in ('findstr /i "GROQ_API_KEY" "%ROOT%.env"') do (
    set GROQ_API_KEY=%%b
)

if "!GROQ_API_KEY!"=="" (
    echo [ERROR] GROQ_API_KEY not found in .env
    echo [INFO]  Get a free key at https://console.groq.com/
    pause
    exit /b 1
)

echo [OK] GROQ_API_KEY loaded.

REM Write a helper launcher so paths with spaces work reliably
echo @echo off > "%ROOT%_run_backend.bat"
echo cd /d "%ROOT%" >> "%ROOT%_run_backend.bat"
echo set PYTHONPATH=%ROOT%src >> "%ROOT%_run_backend.bat"
echo python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload >> "%ROOT%_run_backend.bat"

echo @echo off > "%ROOT%_run_mockapp.bat"
echo cd /d "%ROOT%mock_app" >> "%ROOT%_run_mockapp.bat"
echo python app.py >> "%ROOT%_run_mockapp.bat"

echo @echo off > "%ROOT%_run_frontend.bat"
echo cd /d "%ROOT%frontend" >> "%ROOT%_run_frontend.bat"
echo npm run dev >> "%ROOT%_run_frontend.bat"

REM Launch each service via the helper bat files
echo [1/3] Starting FastAPI backend on port 8000...
start "MaritimeTestAI - Backend" cmd /k "%ROOT%_run_backend.bat"

timeout /t 4 /nobreak >nul

echo [2/3] Starting Flask mock maritime app on port 5000...
start "MaritimeTestAI - Mock App" cmd /k "%ROOT%_run_mockapp.bat"

echo [3/3] Starting React frontend...
start "MaritimeTestAI - Frontend" cmd /k "%ROOT%_run_frontend.bat"

echo.
echo ============================================
echo  All services starting in separate windows:
echo   React UI:    http://localhost:5173
echo   FastAPI:     http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   Mock App:    http://localhost:5000
echo ============================================
echo.
echo If port 5173 is busy, Vite will use 5174 - check the React window.
echo Close the opened terminal windows to stop all services.
pause
