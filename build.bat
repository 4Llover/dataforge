@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   DataForge PyInstaller 打包脚本
echo ========================================
echo.

REM 使用 conda qt6 环境
set PYTHON=E:\anaconda3\envs\qt6\python.exe
set PYINSTALLER=E:\anaconda3\envs\qt6\Scripts\pyinstaller.exe

REM 检查 PyInstaller
%PYINSTALLER% --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller not found, installing...
    %PYTHON% -m pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo [1/3] 清理旧构建...
if exist dist\DataForge rmdir /s /q dist\DataForge
if exist build rmdir /s /q build

echo [2/3] 开始打包...
%PYINSTALLER% build.spec --noconfirm --clean

echo [3/3] 检查结果...
if exist dist\DataForge\DataForge.exe (
    echo.
    echo ========================================
    echo   打包成功！
    echo   输出: dist\DataForge\DataForge.exe
    echo ========================================
    echo.
    dir dist\DataForge\DataForge.exe
    echo.
    echo 包含文件:
    dir /b dist\DataForge\
) else (
    echo.
    echo [ERROR] 打包失败，请检查错误信息。
)

pause
