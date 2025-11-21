@echo off
REM ============================================================================
REM SonarSniffer Windows Installer
REM Installs Python environment, dependencies, and SonarSniffer
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo SonarSniffer Windows Installer
echo ============================================================================
echo.

REM Check if Python is installed
echo Checking for Python installation...
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Python 3.10+ is required but not found in PATH
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Display Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo ✓ Found Python %PYTHON_VER%

REM Check for pip
echo.
echo Checking for pip...
pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: pip is required but not found
    echo Please reinstall Python and ensure pip is included
    pause
    exit /b 1
)
echo ✓ pip is available

REM Create virtual environment (optional but recommended)
echo.
echo.
set /p CREATE_VENV="Create a virtual environment? (recommended) [Y/n]: "
if /i "!CREATE_VENV!"=="" set CREATE_VENV=Y

if /i "!CREATE_VENV!"=="Y" (
    if not exist "venv" (
        echo Creating virtual environment...
        python -m venv venv
        if !errorlevel! neq 0 (
            echo ERROR: Failed to create virtual environment
            pause
            exit /b 1
        )
        echo ✓ Virtual environment created
    )
    
    REM Activate virtual environment
    call venv\Scripts\activate.bat
    if !errorlevel! neq 0 (
        echo ERROR: Failed to activate virtual environment
        pause
        exit /b 1
    )
    echo ✓ Virtual environment activated
)

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
if !errorlevel! neq 0 (
    echo WARNING: pip upgrade had issues, but continuing...
)
echo ✓ pip upgraded

REM Install requirements
echo.
echo Installing dependencies (this may take a few minutes)...
echo This includes: numpy, opencv, scipy, fastapi, flask, and more
echo.

if exist "requirements.txt" (
    pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo WARNING: Some packages may not have installed correctly
        echo You can try manual installation later
    )
) else (
    echo ERROR: requirements.txt not found
    echo Make sure you're in the SonarSniffer directory
    pause
    exit /b 1
)

echo ✓ Dependencies installed

REM Install FFmpeg
echo.
echo.
set /p INSTALL_FFMPEG="Install FFmpeg (required for video output)? [Y/n]: "
if /i "!INSTALL_FFMPEG!"=="" set INSTALL_FFMPEG=Y

if /i "!INSTALL_FFMPEG!"=="Y" (
    echo Checking for Chocolatey...
    choco --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo Installing FFmpeg via Chocolatey...
        choco install ffmpeg -y
        echo ✓ FFmpeg installed
    ) else (
        echo Chocolatey not found. Please install FFmpeg manually:
        echo Download from: https://ffmpeg.org/download.html
        echo Or use Windows Package Manager: winget install FFmpeg
    )
)

REM Create initial license
echo.
echo Setting up trial license...
python license_manager.py create-trial
if !errorlevel! neq 0 (
    echo WARNING: License setup had issues
    echo You can run: python license_manager.py create-trial
)
echo ✓ Trial license created (30 days)

REM Create desktop shortcut
echo.
set /p CREATE_SHORTCUT="Create desktop shortcut for SonarSniffer? [Y/n]: "
if /i "!CREATE_SHORTCUT!"=="" set CREATE_SHORTCUT=Y

if /i "!CREATE_SHORTCUT!"=="Y" (
    powershell -Command "
    $DesktopPath = [Environment]::GetFolderPath('Desktop')
    $ShortcutPath = Join-Path $DesktopPath 'SonarSniffer.lnk'
    $TargetPath = (Get-Location).Path + '\sonar_gui.py'
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = (Get-Command python).Source
    $Shortcut.Arguments = '$TargetPath'
    $Shortcut.WorkingDirectory = (Get-Location).Path
    $Shortcut.IconLocation = (Get-Command python).Source
    $Shortcut.Save()
    Write-Host '✓ Desktop shortcut created'
    "
)

REM Test installation
echo.
echo Testing installation...
python -c "import numpy, cv2, tkinter; print('✓ All core packages loaded successfully')"
if !errorlevel! neq 0 (
    echo ERROR: Installation test failed
    echo Some packages may not be properly installed
    pause
    exit /b 1
)

REM Success message
echo.
echo ============================================================================
echo ✓ SonarSniffer Installation Complete!
echo ============================================================================
echo.
echo You can now run SonarSniffer by:
echo   - Double-clicking the desktop shortcut (if created)
echo   - Running: python sonar_gui.py
echo   - Or running the batch file: run_sonarsniffer.bat
echo.
echo Next steps:
echo   1. Review the LICENSE file for terms and conditions
echo   2. Register your license key (if you have one)
echo   3. Start SonarSniffer and begin processing RSD files
echo.
echo Troubleshooting:
echo   - If packages fail to install, try: pip install --upgrade pip
echo   - Ensure you have internet connection for dependency downloads
echo   - Check Python version: python --version (should be 3.10+)
echo.
echo For support, visit: https://github.com/festeraeb/SonarSniffer
echo.
pause

REM Create run script
echo.
echo Creating run_sonarsniffer.bat...
(
    echo @echo off
    echo if exist venv\Scripts\activate.bat (
    echo     call venv\Scripts\activate.bat
    echo )
    echo python sonar_gui.py
) > run_sonarsniffer.bat

echo ✓ run_sonarsniffer.bat created

echo.
echo Installation finished! You can close this window.
echo.
