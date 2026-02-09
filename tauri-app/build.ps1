# SonarSniffer Cross-Platform Build Script (PowerShell)
# Automates building for Windows, macOS, and Linux
# Usage: .\build.ps1 -Target all|windows|macos|linux|dev -Clean -Release

param(
    [ValidateSet('all', 'windows', 'macos', 'linux', 'dev', 'clean')]
    [string]$Target = 'all',
    
    [switch]$Clean,
    [switch]$Debug,
    [switch]$Help
)

# Configuration
$VERSION = "0.1.0"
$Script:ErrorCount = 0

# Functions
function Write-Header {
    param([string]$Text)
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param([string]$Text)
    Write-Host "✅ $Text" -ForegroundColor Green
}

function Write-Error {
    param([string]$Text)
    Write-Host "❌ $Text" -ForegroundColor Red
    $Script:ErrorCount++
}

function Write-Warning {
    param([string]$Text)
    Write-Host "⚠️  $Text" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Text)
    Write-Host "ℹ️  $Text" -ForegroundColor Blue
}

function Show-Help {
    Write-Host @"
SonarSniffer Build Script v$VERSION

Usage: .\build.ps1 [-Target <target>] [options]

Targets:
  all       Build all platforms (default)
  windows   Build Windows (.msi installer)
  macos     Build macOS (.dmg bundle)
  linux     Build Linux (AppImage)
  dev       Development build (Tauri dev mode)
  clean     Clean build artifacts

Options:
  -Clean    Clean build artifacts first
  -Debug    Build debug version (default: release)
  -Help     Show this help message

Examples:
  .\build.ps1 -Target all                 # Build all platforms
  .\build.ps1 -Target windows -Clean      # Clean and build Windows
  .\build.ps1 -Target dev                 # Start development environment

"@
}

function Test-Prerequisite {
    param(
        [string]$Name,
        [string]$Command,
        [string]$MinVersion = ""
    )
    
    try {
        $result = & $Command 2>$null
        if ($result) {
            $version = if ($MinVersion) { " ($result)" } else { "" }
            Write-Success "$Name installed$version"
            return $true
        }
    }
    catch {
        Write-Error "$Name not installed"
        return $false
    }
}

function Check-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    $allPresent = $true
    
    # Node.js
    if (Test-Prerequisite "Node.js" { node --version }) {
        Write-Success "Version: $(node --version)"
    } else {
        Write-Error "Node.js 18+ required: https://nodejs.org"
        $allPresent = $false
    }
    
    # npm
    if (Test-Prerequisite "npm" { npm --version }) {
        Write-Success "Version: $(npm --version)"
    } else {
        Write-Error "npm is required"
        $allPresent = $false
    }
    
    # Rust
    if (Test-Prerequisite "Rust" { rustc --version }) {
        Write-Success "Version: $(rustc --version)"
    } else {
        Write-Error "Rust required: https://rustup.rs"
        $allPresent = $false
    }
    
    # Cargo
    if (Test-Prerequisite "Cargo" { cargo --version }) {
        Write-Success "Version: $(cargo --version)"
    } else {
        Write-Error "Cargo is required"
        $allPresent = $false
    }
    
    # Git (optional)
    if (Test-Prerequisite "Git" { git --version }) {
        Write-Success "Version: $(git --version)"
    } else {
        Write-Warning "Git not found (optional but recommended)"
    }
    
    return $allPresent
}

function Install-Dependencies {
    Write-Header "Installing Dependencies"
    
    # npm dependencies
    if (Test-Path "node_modules") {
        Write-Info "node_modules exists, skipping npm install"
    } else {
        Write-Info "Installing Node.js dependencies..."
        npm install
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Node.js dependencies installed"
        } else {
            Write-Error "Failed to install Node.js dependencies"
            return $false
        }
    }
    
    # Rust dependencies
    Write-Info "Installing Rust dependencies..."
    try {
        Push-Location "src-tauri"
        cargo fetch
        Pop-Location
        Write-Success "Rust dependencies fetched"
    }
    catch {
        Write-Error "Failed to fetch Rust dependencies: $_"
        return $false
    }
    
    return $true
}

function Build-Frontend {
    Write-Header "Building Frontend (React + TypeScript)"
    
    Write-Info "Building with Vite..."
    npm run build:ui
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Frontend built: dist/"
        return $true
    } else {
        Write-Error "Frontend build failed"
        return $false
    }
}

function Build-Windows {
    Write-Header "Building Windows (.msi Installer)"
    
    Write-Info "Building Windows executable..."
    npm run build:windows
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Windows build failed"
        return $false
    }
    
    # Try to create MSI
    Write-Info "Attempting to create MSI installer..."
    npm run build:msi
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Windows MSI installer created"
    } else {
        Write-Warning "MSI creation skipped (NSIS may not be installed)"
        Write-Info "Standalone EXE is available in src-tauri/target/x86_64-pc-windows-msvc/release/"
    }
    
    # Check for EXE
    $exePath = "src-tauri/target/x86_64-pc-windows-msvc/release/SonarSniffer.exe"
    if (Test-Path $exePath) {
        Write-Success "Windows executable: $exePath"
        return $true
    } else {
        Write-Error "Executable not found: $exePath"
        return $false
    }
}

function Build-MacOS {
    Write-Header "Building macOS (.dmg Bundle)"
    
    if ($env:OS -ne "Windows_NT" -and -not (Test-Path "/System")) {
        Write-Warning "Not on macOS - cannot build for macOS"
        Write-Info "macOS builds must be performed on macOS"
        return $true
    }
    
    Write-Info "Building macOS app..."
    npm run tauri -- build
    
    $dmgPath = "src-tauri/target/release/bundle/dmg/"
    if (Test-Path $dmgPath) {
        Write-Success "macOS DMG bundles created: $dmgPath"
        return $true
    } else {
        Write-Error "macOS DMG not created"
        return $false
    }
}

function Build-Linux {
    Write-Header "Building Linux (AppImage)"
    
    if ($env:OS -eq "Windows_NT") {
        Write-Warning "Not on Linux - cannot build AppImage natively"
        Write-Info "Linux builds must be performed on Linux"
        return $true
    }
    
    Write-Info "Building Linux AppImage..."
    npm run tauri -- build --target x86_64-unknown-linux-gnu
    
    $appImagePath = "src-tauri/target/release/bundle/appimage/"
    if (Test-Path $appImagePath) {
        Write-Success "Linux AppImage created: $appImagePath"
        return $true
    } else {
        Write-Error "AppImage not created"
        return $false
    }
}

function Build-Dev {
    Write-Header "Starting Development Environment"
    
    Write-Info "Starting Tauri dev server..."
    Write-Info "Frontend: http://localhost:5173"
    Write-Info "App window will open automatically"
    Write-Host ""
    
    npm run dev
}

function Build-All {
    Write-Header "Building All Platforms"
    
    # Frontend is common to all
    Build-Frontend
    
    # Build only for current platform
    if ($env:OS -eq "Windows_NT") {
        Write-Info "Windows detected - building for Windows"
        Build-Windows
    } elseif (Test-Path "/System") {
        Write-Info "macOS detected - building for macOS"
        Build-MacOS
    } else {
        Write-Info "Linux detected - building for Linux"
        Build-Linux
    }
    
    Write-Warning "Cross-platform builds are best done in CI/CD pipeline"
    Write-Info "See .github/workflows/build-release.yml for full multi-platform builds"
}

function Clean-Build {
    Write-Header "Cleaning Build Artifacts"
    
    Write-Info "Removing dist/"
    Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Info "Cleaning Cargo build..."
    try {
        Push-Location "src-tauri"
        cargo clean --release
        Pop-Location
    }
    catch {
        Write-Warning "Cargo clean failed: $_"
    }
    
    Write-Info "Removing build directory..."
    Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Success "Build artifacts cleaned"
    return $true
}

# Main
if ($Help) {
    Show-Help
    exit 0
}

Write-Host ""
Write-Header "SonarSniffer Build v$VERSION"

# Clean if requested
if ($Clean) {
    Clean-Build
}

# Check prerequisites
if (-not (Check-Prerequisites)) {
    Write-Error "Some prerequisites are missing"
    exit 1
}

# Install dependencies
if (-not (Install-Dependencies)) {
    Write-Error "Failed to install dependencies"
    exit 1
}

Write-Host ""

# Build based on target
switch ($Target) {
    'all' {
        Build-All
    }
    'windows' {
        Build-Frontend
        Build-Windows
    }
    'macos' {
        Build-Frontend
        Build-MacOS
    }
    'linux' {
        Build-Frontend
        Build-Linux
    }
    'dev' {
        Build-Dev
    }
    'clean' {
        Clean-Build
    }
    default {
        Write-Error "Unknown target: $Target"
        Show-Help
        exit 1
    }
}

Write-Host ""
if ($Script:ErrorCount -eq 0) {
    Write-Header "Build Complete - Success!"
    Write-Success "Build successful! Artifacts ready for distribution"
    exit 0
} else {
    Write-Header "Build Complete - With Errors"
    Write-Error "Build completed with $($Script:ErrorCount) error(s)"
    exit 1
}
