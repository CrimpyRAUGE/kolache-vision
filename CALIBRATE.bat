@echo off
setlocal

REM Go to repo root (where this .bat file lives)
cd /d "%~dp0"

REM Create venv if missing
if not exist "venv\" (
  echo Creating virtual environment...
  py -m venv venv
)

REM Activate venv
call "venv\Scripts\activate"

REM Upgrade pip + install deps
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Capture a frame, then calibrate slots
python vision\capture_frame.py
python vision\calibrate_slots.py

echo.
echo Calibration complete! Saved config\vision_rois.json
pause
endlocal
