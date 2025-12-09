@echo off
REM SonarSniffer Pre-Installation Diagnostics
REM Run this FIRST to check if your system is ready

echo ========================================
echo   SonarSniffer Installation Diagnostics
echo ========================================
echo.
echo Checking your system for compatibility...
echo.

REM Test 1: Python installed and in PATH
echo [1/4] Checking for Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ Python is installed
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do (
        set PYTHON_VERSION=%%i
        echo   ✓ Version: !PYTHON_VERSION!
    )
) else (
    echo   ✗ FAILED: Python not found in PATH
    echo.
    echo   Solution: Install Python from https://python.org
    echo   - Download Python 3.8 or newer
    echo   - IMPORTANT: Check "Add Python to PATH" during installation
    echo   - Then restart your command prompt
    echo.
    pause
    exit /b 1
)
echo.

REM Test 2: Check if venv module is available
echo [2/4] Checking for venv module...
python -m venv --help >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ venv module is available
) else (
    echo   ✗ FAILED: venv module not found
    echo.
    echo   This usually means Python wasn't properly installed.
    echo   - Reinstall Python from https://python.org
    echo   - Ensure "tcl/tk and IDLE" is checked during installation
    echo.
    pause
    exit /b 1
)
echo.

REM Test 3: Check pip is available
echo [3/4] Checking for pip...
python -m pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ pip is installed
    for /f "tokens=2" %%i in ('python -m pip --version') do (
        set PIP_VERSION=%%i
        echo   ✓ Version: !PIP_VERSION!
    )
) else (
    echo   ✗ FAILED: pip not found
    echo.
    echo   Solution: Upgrade Python or reinstall from https://python.org
    echo.
    pause
    exit /b 1
)
echo.

REM Test 4: Check write permissions in current directory
echo [4/4] Checking write permissions...
set TEST_FILE=._sonarsniffer_test_write_.tmp
echo test >%TEST_FILE% 2>nul
if %errorlevel% equ 0 (
    echo   ✓ Write permissions are OK
    del %TEST_FILE% >nul 2>&1
) else (
    echo   ✗ FAILED: Cannot write to this directory
    echo.
    echo   Solution: 
    echo   - Try running as Administrator
    echo   - OR move the SonarSniffer folder to a writable location
    echo.
    pause
    exit /b 1
)
echo.

REM Summary
echo ========================================
echo   Diagnostics Complete - All Checks Passed!
echo ========================================
echo.
echo You are ready to install SonarSniffer.
echo.
echo Next steps:
echo   1. Run: install_windows.bat
echo.
echo If you have any issues:
echo   1. Check the error messages above
echo   2. Try running as Administrator
echo   3. Contact: festeraeb@yahoo.com
echo.
pause
