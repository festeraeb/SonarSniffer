@echo off
REM ============================================
REM SonarSniffer Desktop Shortcut Creator
REM Automatically creates a desktop icon
REM ============================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo  SonarSniffer Desktop Shortcut Creator
echo ========================================
echo.

REM Check if SonarSniffer is installed
if not exist "C:\Program Files\SonarSniffer\SonarSniffer.exe" (
    echo ERROR: SonarSniffer is not installed!
    echo.
    echo Please install SonarSniffer first:
    echo 1. Download the installer file
    echo 2. Double-click it
    echo 3. Follow the installation steps
    echo.
    echo After installation, run this script again.
    echo.
    pause
    exit /b 1
)

echo Creating desktop shortcut...

REM Get the user's desktop path
for /f "tokens=3" %%a in ('reg query "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop ^| findstr /ri "REG_SZ"') do set "DESKTOP=%%a"

REM Create the shortcut using PowerShell (more reliable)
powershell -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; " ^
  "$Shortcut = $WshShell.CreateShortcut('%DESKTOP%\SonarSniffer.lnk'); " ^
  "$Shortcut.TargetPath = 'C:\Program Files\SonarSniffer\SonarSniffer.exe'; " ^
  "$Shortcut.WorkingDirectory = 'C:\Program Files\SonarSniffer'; " ^
  "$Shortcut.Description = 'SonarSniffer - Sonar Data Analysis Tool'; " ^
  "$Shortcut.IconLocation = 'C:\Program Files\SonarSniffer\SonarSniffer.exe,0'; " ^
  "$Shortcut.Save()"

if !errorlevel! equ 0 (
    echo.
    echo ========================================
    echo  SUCCESS!
    echo ========================================
    echo.
    echo Desktop shortcut created successfully!
    echo.
    echo You should now see "SonarSniffer" icon on your desktop.
    echo Double-click it to launch the application.
    echo.
) else (
    echo.
    echo ERROR: Failed to create shortcut
    echo.
    echo Try these steps manually:
    echo 1. Open File Explorer
    echo 2. Navigate to: C:\Program Files\SonarSniffer\
    echo 3. Right-click SonarSniffer.exe
    echo 4. Select "Send to" ^> "Desktop (create shortcut)"
    echo.
)

pause
