@echo off
title Smjrifle Desktop Reminder
echo Starting Smjrifle Desktop Reminder...

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b 1
)

:: Install requirements if not already present
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Installing required components for first-time run...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

:: Run the app
echo Launching Smjrifle Desktop Reminder...
start "" pythonw main.py
exit
