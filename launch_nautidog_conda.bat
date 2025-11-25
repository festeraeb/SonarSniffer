@echo off
REM NautiDog Sailing Launcher with Robust Conda Handling
REM Automatically finds and configures conda from various install locations

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   NautiDog Sailing - Launching...
echo ========================================
echo.

REM Function to find conda
set "CONDA_EXE="
set "CONDA_ROOT="

REM Try method 1: Direct conda in PATH
where conda >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('where conda') do set "CONDA_EXE=%%i"
    for /f "tokens=*" %%i in ('cd') do set "CONDA_ROOT=%%i"
    goto conda_found
)

REM Try method 2: Common Miniconda locations
if exist "%USERPROFILE%\Miniconda3\Scripts\conda.exe" (
    set "CONDA_EXE=%USERPROFILE%\Miniconda3\Scripts\conda.exe"
    set "CONDA_ROOT=%USERPROFILE%\Miniconda3"
    goto conda_found
)

if exist "%USERPROFILE%\Anaconda3\Scripts\conda.exe" (
    set "CONDA_EXE=%USERPROFILE%\Anaconda3\Scripts\conda.exe"
    set "CONDA_ROOT=%USERPROFILE%\Anaconda3"
    goto conda_found
)

if exist "%USERPROFILE%\AppData\Local\Miniconda3\Scripts\conda.exe" (
    set "CONDA_EXE=%USERPROFILE%\AppData\Local\Miniconda3\Scripts\conda.exe"
    set "CONDA_ROOT=%USERPROFILE%\AppData\Local\Miniconda3"
    goto conda_found
)

if exist "C:\Miniconda3\Scripts\conda.exe" (
    set "CONDA_EXE=C:\Miniconda3\Scripts\conda.exe"
    set "CONDA_ROOT=C:\Miniconda3"
    goto conda_found
)

if exist "C:\Anaconda3\Scripts\conda.exe" (
    set "CONDA_EXE=C:\Anaconda3\Scripts\conda.exe"
    set "CONDA_ROOT=C:\Anaconda3"
    goto conda_found
)

REM Conda not found - show error with instructions
echo.
echo ERROR: Conda not found!
echo.
echo NautiDog Sailing requires Miniconda or Anaconda Python.
echo.
echo Please install Miniconda from:
echo   https://docs.conda.io/en/latest/miniconda.html
echo.
echo Recommended locations:
echo   - Windows: Install to %%USERPROFILE%%\Miniconda3 (default)
echo   - Or: C:\Miniconda3
echo.
echo After installation, close and reopen this launcher.
echo.
pause
exit /b 1

:conda_found
echo [INFO] Found conda at: !CONDA_ROOT!
echo.

REM Configure PATH for conda
set "PATH=!CONDA_ROOT!\Scripts;!CONDA_ROOT!\Library\bin;!CONDA_ROOT!\bin;!PATH!"

REM Initialize conda
call "!CONDA_ROOT!\Scripts\activate.bat" >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Could not initialize conda shell, continuing with direct path
)

REM Check if nautidog environment exists
echo [INFO] Checking NautiDog environment...
"!CONDA_EXE!" env list 2>nul | findstr /C:"nautidog" >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [INFO] NautiDog environment not found. Creating...
    "!CONDA_EXE!" env create -n nautidog -f environment.yml --yes
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Failed to create NautiDog environment
        echo Please try running the installer again: powershell -ExecutionPolicy Bypass -File install_nautidog_robust.ps1
        pause
        exit /b 1
    )
    echo [SUCCESS] Environment created
) else (
    echo [SUCCESS] NautiDog environment found
)

echo.
echo [INFO] Launching NautiDog Sailing...
echo.

REM Launch the GUI
"!CONDA_EXE!" run -n nautidog python sonar_gui.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to launch NautiDog Sailing
    echo Exit code: %errorlevel%
    echo.
    pause
    exit /b 1
)

endlocal
