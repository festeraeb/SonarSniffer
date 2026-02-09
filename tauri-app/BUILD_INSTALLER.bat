@echo off
REM ============================================
REM SonarSniffer Windows Installer Builder
REM Simple one-click build script
REM ============================================

setlocal enabledelayedexpansion
setlocal enableextensions

echo.
echo ========================================
echo  SonarSniffer Windows Installer Builder
echo ========================================
echo.

set "NODEJS_INSTALLED=1"
set "RUST_INSTALLED=1"

REM Check if npm is installed
where npm >nul 2>nul
if !errorlevel! neq 0 (
    set "NODEJS_INSTALLED=0"
)

REM Check if Rust is installed
where cargo >nul 2>nul
if !errorlevel! neq 0 (
    set "RUST_INSTALLED=0"
)

REM ============================================
REM Install Prerequisites if Missing
REM ============================================

if !NODEJS_INSTALLED! equ 0 (
    echo.
    echo ========================================
    echo  ⚠️  NODE.JS NOT INSTALLED
    echo ========================================
    echo.
    echo SonarSniffer requires Node.js to build.
    echo Without it, this program WILL NOT WORK.
    echo.
    echo Node.js includes npm, which is essential.
    echo.
    echo Would you like to install Node.js now?
    echo.
    set /p INSTALL_NODE="Type 'yes' to install, or 'no' to skip: "
    
    if /i "!INSTALL_NODE!"=="yes" (
        echo.
        echo Downloading Node.js installer...
        echo (This will open a browser window)
        echo.
        start https://nodejs.org/
        echo.
        echo Please follow these steps:
        echo   1. Click the "LTS" button
        echo   2. Run the downloaded file
        echo   3. Click "Next" until you see "Install"
        echo   4. Click "Install"
        echo   5. Wait for installation to complete
        echo   6. Close all windows
        echo   7. RESTART YOUR COMPUTER
        echo   8. Open this script again
        echo.
        pause
        exit /b 0
    ) else (
        echo.
        echo ❌ Cannot continue without Node.js
        echo Please install it and run this script again.
        echo.
        pause
        exit /b 1
    )
)

if !RUST_INSTALLED! equ 0 (
    echo.
    echo ========================================
    echo  ⚠️  RUST NOT INSTALLED
    echo ========================================
    echo.
    echo SonarSniffer requires Rust to compile.
    echo Without it, this program WILL NOT WORK.
    echo.
    echo Rust includes cargo, which is essential.
    echo.
    echo Would you like to install Rust now?
    echo.
    set /p INSTALL_RUST="Type 'yes' to install, or 'no' to skip: "
    
    if /i "!INSTALL_RUST!"=="yes" (
        echo.
        echo Downloading Rust installer...
        echo (This will open a browser window)
        echo.
        start https://rustup.rs/
        echo.
        echo Please follow these steps:
        echo   1. Save the file (rustup-init.exe)
        echo   2. Run the downloaded file
        echo   3. Press ENTER for default settings (or type 1)
        echo   4. Wait for installation to complete
        echo   5. Close all windows
        echo   6. RESTART YOUR COMPUTER
        echo   7. Open this script again
        echo.
        pause
        exit /b 0
    ) else (
        echo.
        echo ❌ Cannot continue without Rust
        echo Please install it and run this script again.
        echo.
        pause
        exit /b 1
    )
)

echo ✓ All prerequisites found!
echo.

echo Step 1: Installing npm dependencies...
echo (This downloads packages from the internet - takes 2-3 minutes)
echo.
call npm install
if !errorlevel! neq 0 (
    echo.
    echo ❌ ERROR: npm install failed
    echo.
    echo Try this:
    echo   1. Close this window
    echo   2. Restart your computer
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)
echo ✓ npm dependencies installed successfully
echo.

echo.
echo Step 2: Fetching Rust dependencies...
echo (This downloads Rust packages - takes 2-3 minutes)
echo.
cd src-tauri
call cargo fetch
if !errorlevel! neq 0 (
    echo.
    echo ❌ ERROR: cargo fetch failed
    echo.
    echo Try this:
    echo   1. Go back: cd ..
    echo   2. Delete folder: rmdir /s /q src-tauri\target
    echo   3. Run this script again
    echo.
    cd ..
    pause
    exit /b 1
)
cd ..
echo ✓ Rust dependencies fetched successfully
echo.

echo.
echo Step 3: Building frontend (React app)...
echo (This builds the user interface - takes 2-3 minutes)
echo.
call npm run build:ui
if !errorlevel! neq 0 (
    echo.
    echo ❌ ERROR: Frontend build failed
    echo.
    echo This is usually a temporary issue. Try:
    echo   1. Delete: node_modules folder
    echo   2. Run: npm install
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)
echo ✓ Frontend built successfully
echo.

echo.
echo Step 4: Building Windows executable...
echo (This compiles the Rust backend - takes 5-10 minutes on first build)
echo Please be patient, this is the longest step!
echo.
call npm run build:windows
if !errorlevel! neq 0 (
    echo.
    echo ❌ ERROR: Windows build failed
    echo.
    echo This sometimes happens on first build. Try:
    echo   1. Close this window
    echo   2. Restart your computer
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)
echo ✓ Windows executable built successfully
echo.

echo.
echo ========================================
echo  ✓ SUCCESS! INSTALLER READY!
echo ========================================
echo.
echo The Windows executable has been created:
echo.
echo   📁 src-tauri\target\x86_64-pc-windows-msvc\release\
echo   📄 SonarSniffer.exe
echo.
echo What to do next:
echo.
echo   Option 1 (Easiest):
echo   - Find SonarSniffer.exe in File Explorer
echo   - Double-click it to install
echo   - Desktop icon appears automatically ✓
echo.
echo Option 2 (Create MSI installer):
echo   - Run: npm run build:msi
echo     (requires NSIS installer on your computer)
echo   - This creates: SonarSniffer.msi (Windows installer format)
echo.
echo Option 3 (Run from build folder):
echo   - Just double-click: src-tauri\target\x86_64-pc-windows-msvc\release\SonarSniffer.exe
echo.
echo ========================================
echo.
pause
