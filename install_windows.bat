@echo off
REM SonarSniffer Windows Installation Script
REM Creates Python virtual environment and installs SonarSniffer
REM Completely avoids conda which has PowerShell integration issues

setlocal enabledelayedexpansion

echo ========================================
echo   SonarSniffer Professional Installation
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found. Checking version...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%
echo.

REM Check if we're already in a virtual environment
if defined VIRTUAL_ENV (
    echo Already in virtual environment: %VIRTUAL_ENV%
    echo Upgrading pip...
    python -m pip install --upgrade pip
    if %errorlevel% neq 0 (
        echo WARNING: Failed to upgrade pip, continuing anyway...
    )
    echo Installing SonarSniffer and dependencies...
    pip install -e .
    if !errorlevel! equ 0 goto success
    goto error
) else (
    REM Use venv to create local environment (avoids conda entirely)
    set ENV_DIR=sonarsniffer_env
    echo Creating virtual environment in !ENV_DIR!...
    python -m venv !ENV_DIR!
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        goto error
    )
    
    echo.
    echo Activating virtual environment...
    call !ENV_DIR!\Scripts\activate.bat
    if %errorlevel% neq 0 (
        echo ERROR: Failed to activate virtual environment.
        goto error
    )
    
    echo Upgrading pip...
    python -m pip install --upgrade pip
    if %errorlevel% neq 0 (
        echo WARNING: Failed to upgrade pip, continuing anyway...
    )
    
    echo Installing SonarSniffer and dependencies...
    pip install -e .
    if !errorlevel! equ 0 goto success
    goto error
)

:success
echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo SonarSniffer has been successfully installed.
echo.
echo To use SonarSniffer:
echo   1. Navigate to this directory
echo   2. Activate environment: sonarsniffer_env\Scripts\activate.bat
echo   3. Run: sonarsniffer --help
echo.
echo Example commands:
echo   sonarsniffer analyze your_file.RSD
echo   sonarsniffer web your_file.RSD --port 8080
echo   sonarsniffer license --validate YOUR_KEY
echo.
echo For support: festeraeb@yahoo.com
echo.
pause
exit /b 0

:error
echo.
echo ========================================
echo   ERROR: Installation Failed
echo ========================================
echo.
echo Please check the error messages above.
echo.
echo Troubleshooting:
echo   - Make sure Python 3.8+ is installed and in PATH
echo   - Check that you have write permissions in this directory
echo   - Try running as Administrator if permission errors occur
echo.
pause
exit /b 1