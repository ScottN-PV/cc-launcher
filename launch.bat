@echo off
REM Claude Code Launcher - Development Launch Script
REM This script launches main.py in the current directory

echo Starting Claude Code Launcher...
python main.py

REM If Python exits with an error, pause to see the error message
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python exited with error code %errorlevel%
    pause
)
