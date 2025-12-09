@echo off
REM SonarSniffer Post-Installation Verification
REM Run this AFTER installation to verify everything works

echo ========================================
echo   SonarSniffer Installation Verification
echo ========================================
echo.

REM Check if the venv exists
if not exist "sonarsniffer_env\" (
    echo ERROR: sonarsniffer_env folder not found!
    echo The installer may have failed.
    echo.
    echo Try running install_windows.bat again.
    pause
    exit /b 1
)

echo [1/5] Checking virtual environment...
echo   ✓ Found sonarsniffer_env folder
echo.

REM Activate the environment
echo [2/5] Activating virtual environment...
call sonarsniffer_env\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo   ✗ FAILED: Could not activate environment
    echo.
    echo   Try running as Administrator or check folder permissions
    pause
    exit /b 1
)
echo   ✓ Environment activated
echo.

REM Check if sonarsniffer is installed
echo [3/5] Checking SonarSniffer installation...
sonarsniffer --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ FAILED: SonarSniffer not found in environment
    echo.
    echo   Try running install_windows.bat again
    pause
    exit /b 1
)
echo   ✓ SonarSniffer is installed
for /f "tokens=*" %%i in ('sonarsniffer --version 2^>^&1') do echo   ✓ %%i
echo.

REM Check CLI help works
echo [4/5] Checking CLI interface...
sonarsniffer --help >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ FAILED: CLI help failed (docopt not working?)
    echo.
    echo   Error details:
    sonarsniffer --help
    pause
    exit /b 1
)
echo   ✓ CLI interface is working
echo.

REM Check all required modules are importable
echo [5/5] Checking Python dependencies...
python -c "import numpy, matplotlib, PIL, requests, docopt; print('All dependencies found')" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ numpy - OK
    echo   ✓ matplotlib - OK
    echo   ✓ PIL (Pillow) - OK
    echo   ✓ requests - OK
    echo   ✓ docopt - OK (CLI parser)
) else (
    echo   ✗ FAILED: Some dependencies are missing
    echo.
    echo   Try running install_windows.bat again
    pause
    exit /b 1
)
echo.

REM Success!
echo ========================================
echo   Verification Complete - Success!
echo ========================================
echo.
echo SonarSniffer is ready to use!
echo.
echo Example commands:
echo   sonarsniffer analyze your_file.RSD
echo   sonarsniffer web your_file.RSD --port 8080
echo   sonarsniffer license --validate YOUR_KEY
echo.
echo To activate the environment in the future:
echo   sonarsniffer_env\Scripts\activate.bat
echo.
echo For help:
echo   sonarsniffer --help
echo.
echo For support: festeraeb@yahoo.com
echo.
pause
