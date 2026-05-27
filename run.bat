@echo off
chcp 65001 >nul 2>&1
title DataForge v1.0

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Not installed. Run install_and_run.bat first.
    pause
    exit /b 1
)

.venv\Scripts\python.exe run.py
