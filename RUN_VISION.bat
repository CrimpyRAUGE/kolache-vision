@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\" (
  echo venv not found. Run CALIBRATE.bat first.
  pause
  exit /b 1
)

call "venv\Scripts\activate"

python vision\run_slots.py

echo.
echo Vision stopped.
pause
endlocal
