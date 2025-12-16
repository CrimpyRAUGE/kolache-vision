@echo off
title Kolache Vision - START ALL
cd /d "%~dp0"

echo ================================
echo  Starting Kolache Vision System
echo ================================

REM Activate virtual environment
call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Virtual environment not found.
    echo Run CALIBRATE.bat first.
    pause
    exit /b 1
)

REM Start vision in a new window
echo Starting vision...
start "Kolache Vision - Camera" cmd /k python vision\run_slots.py

REM Give vision a moment to start
timeout /t 3 >nul

REM Start web server in this window
echo Starting web server...
echo Access on phone at:
echo http://192.168.50.115:8000
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000

echo.
echo Server stopped.
pause
