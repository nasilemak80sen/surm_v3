@echo off
title SURM Toolkit Launcher
color 0A

echo.
echo  =====================================================
echo   SURM Toolkit - PETRONAS Carigali
echo   Subsurface Uncertainty & Risk Management Plan
echo  =====================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Create venv if missing
if not exist ".venv" (
    echo [SETUP] Creating virtual environment...
    python -m venv .venv
    echo [SETUP] Installing dependencies ^(first run only^)...
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
    echo [SETUP] Setup complete.
) else (
    call .venv\Scripts\activate.bat
)

:: Open browser after short delay
echo.
echo [START] Launching SURM Toolkit at http://localhost:8501
echo         Close this window to stop the app.
echo.
start "" /B cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8501"

:: Run app
streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

pause
