@echo off
setlocal

echo ===================================================
echo Welcome to the AI Radio Station!
echo ===================================================
echo.

:: Prompt for API Key
set /p USER_API_KEY="Enter your GEMINI_API_KEY (leave blank to run in mock API mode): "

if "%USER_API_KEY%"=="" (
    echo.
    echo No API key provided. Starting in MOCK API MODE.
    echo Note: CrewAI and TTS generation will fail/fallback gracefully in mock mode.
    set GEMINI_API_KEY=dummy
) else (
    echo.
    echo API key accepted.
    set GEMINI_API_KEY=%USER_API_KEY%
)

echo.
echo Installing backend Python dependencies...
pip install -r requirements.txt

echo.
echo Starting FastAPI Backend Orchestrator (Port 8000)...
start "AI Radio Backend" cmd /c "python start_server.py"

echo.
echo Installing Frontend NPM dependencies...
cd frontend
call npm install

echo.
echo Starting React Vite Frontend (Port 5173)...
start "AI Radio Frontend" cmd /c "npm run dev"

echo.
echo ===================================================
echo All systems started!
echo Frontend Dashboard: http://localhost:5173
echo Backend API Docs:   http://localhost:8000/docs
echo.
echo Note: This system requires 'ffmpeg' to be installed on your Windows machine
echo and available in your system PATH for the audio mixer to function.
echo ===================================================
pause
