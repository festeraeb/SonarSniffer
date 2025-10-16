@echo off
REM SonarSniffer Windows Installation Script
REM Creates Python environment and installs SonarSniffer

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

REM Check if we're in a virtual environment
if defined VIRTUAL_ENV (
    echo Already in virtual environment: %VIRTUAL_ENV%
    echo Installing SonarSniffer...
    pip install -e .
) else (
    REM Check if conda is available
    conda --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Conda found. Creating conda environment...
        conda create -n sonarsniffer python=3.11 -y
        echo Activating conda environment...
        call conda activate sonarsniffer
        echo Installing SonarSniffer...
        pip install -e .
    ) else (
        REM Use venv
        echo Creating virtual environment with venv...
        python -m venv sonarsniffer_env
        echo Activating virtual environment...
        call sonarsniffer_env\Scripts\activate.bat
        echo Upgrading pip...
        python -m pip install --upgrade pip
        echo Installing SonarSniffer...
        pip install -e .
    )
)

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   Installation Complete!
    echo ========================================
    echo.
    echo SonarSniffer has been successfully installed.
    echo.
    echo To use SonarSniffer:
    echo   1. Activate the environment (if using conda/venv)
    echo   2. Run: sonarsniffer --help
    echo.
    echo For analysis: sonarsniffer analyze your_file.RSD
    echo For web interface: sonarsniffer web your_file.RSD
    echo.
    echo Contact: festeraeb@yahoo.com for licensing information.
    echo.
) else (
    echo.
    echo ERROR: Installation failed!
    echo Please check the error messages above.
    echo.
)

echo Press any key to continue...
pause >nul