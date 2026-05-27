@echo off
chcp 65001 >nul 2>&1
echo Starting DataForge...
python "%~dp0run.py"
if errorlevel 1 (
    echo.
    echo [ERROR] DataForge exited with error.
    pause
)
