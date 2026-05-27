@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   DataForge PyInstaller Build Script
echo ========================================
echo.

set PYTHON=E:\anaconda3\envs\qt6\python.exe
set PYINSTALLER=E:\anaconda3\envs\qt6\Scripts\pyinstaller.exe

%PYINSTALLER% --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    %PYTHON% -m pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo [1/3] Cleaning old build...
if exist dist\DataForge rmdir /s /q dist\DataForge
if exist build rmdir /s /q build

echo [2/3] Building...
%PYINSTALLER% build.spec --noconfirm --clean

echo [3/3] Checking result...
if exist dist\DataForge\DataForge.exe (
    echo.
    echo ========================================
    echo   BUILD SUCCESS
    echo   Output: dist\DataForge\DataForge.exe
    echo ========================================
    echo.
    dir dist\DataForge\DataForge.exe
    echo.
    echo Files in package:
    dir /b dist\DataForge\
) else (
    echo.
    echo [ERROR] Build failed. Check errors above.
)

pause
