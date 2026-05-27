@echo off
chcp 65001 >nul 2>&1
title DataForge Installer
echo.
echo ========================================
echo   DataForge v1.0 Setup
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.9+ first.
    echo https://www.python.org/downloads/
    echo Remember to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [INFO] Python %PYVER%

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
) else (
    echo [1/3] venv already exists, skipping.
)

echo [2/3] Installing dependencies (first time ~2-3 min)...
.venv\Scripts\python.exe -m pip install --upgrade pip -q -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv\Scripts\python.exe -m pip install -r requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. Check network.
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo ========================================
echo   Launching DataForge...
echo ========================================
echo.

.venv\Scripts\python.exe run.py
