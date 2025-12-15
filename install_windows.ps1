# SonarSniffer Windows Installation Script (PowerShell)
# Dynamically fetches latest Python release and installs SonarSniffer

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SonarSniffer Professional Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to find Python executable
function Get-PythonPath {
    # Check if python is in PATH
    $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($pythonPath) {
        return $pythonPath
    }
    
    # Check common installation paths
    $commonPaths = @(
        "C:\Python314\python.exe",
        "C:\Python313\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    )
    
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    return $null
}

# Check if Python is installed
$pythonPath = Get-PythonPath
$skipPythonInstall = $false

if ($pythonPath) {
    $pythonCheck = & $pythonPath --version 2>&1
    Write-Host "✓ Python found: $pythonPath" -ForegroundColor Green
    Write-Host "  Version: $pythonCheck" -ForegroundColor Green
    Write-Host ""
    $skipPythonInstall = $true
} else {
    Write-Host "⚠ Python is not installed or not in PATH" -ForegroundColor Yellow
    Write-Host ""
}

# Function to get latest Python release
function Get-LatestPythonVersion {
    Write-Host "[1/2] Fetching latest Python release information..." -ForegroundColor Cyan
    
    try {
        # Set up TLS
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
        
        # Fetch Python downloads page
        Write-Host "  Querying: https://www.python.org/downloads/" -ForegroundColor Gray
        $response = Invoke-WebRequest -Uri "https://www.python.org/downloads/" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        
        # Extract version numbers using regex - look for latest release pattern
        $versionMatches = [regex]::Matches($response.Content, 'Latest Python Release.*?Python\s+((\d+\.\d+\.\d+))')
        
        if ($versionMatches.Count -gt 0) {
            $latestVersion = $versionMatches[0].Groups[2].Value
            Write-Host "✓ Found latest Python: $latestVersion" -ForegroundColor Green
            return $latestVersion
        }
        
        # Fallback: Look for any version pattern and get the newest
        $allVersions = [regex]::Matches($response.Content, 'python-(\d+\.\d+\.\d+)-amd64\.exe') | 
                       ForEach-Object { $_.Groups[1].Value } | 
                       Sort-Object {[version]$_} -Descending |
                       Select-Object -First 1
        
        if ($allVersions) {
            Write-Host "✓ Found Python: $allVersions" -ForegroundColor Green
            return $allVersions
        }
    }
    catch {
        Write-Host "  (Query failed: $_)" -ForegroundColor Gray
    }
    
    # Default fallback
    Write-Host "  (Using default: 3.14.0)" -ForegroundColor Yellow
    return "3.14.0"
}

# Download and install Python if needed
if (-not $skipPythonInstall) {
    $pythonVersion = Get-LatestPythonVersion
    $pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
    $pythonInstaller = "$env:TEMP\python-installer.exe"
    
    Write-Host ""
    Write-Host "[2/2] Downloading Python $pythonVersion..." -ForegroundColor Cyan
    
    try {
        # Set up TLS
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
        
        Write-Host "  URL: $pythonUrl" -ForegroundColor Gray
        
        # Create WebClient with timeout
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($pythonUrl, $pythonInstaller)
        
        if (Test-Path $pythonInstaller) {
            Write-Host "✓ Download successful!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Installing Python $pythonVersion..." -ForegroundColor Cyan
            
            # Run installer with quiet options (elevated for system-wide install)
            $installProcess = Start-Process -FilePath $pythonInstaller `
                -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_doc=0 Include_pip=1" `
                -NoNewWindow -PassThru -Wait
            
            if ($installProcess.ExitCode -eq 0) {
                Write-Host "✓ Python installation successful!" -ForegroundColor Green
                
                # Refresh PATH
                $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
                
                # Verify installation
                Start-Sleep -Seconds 2
                $pythonPath = Get-PythonPath
                if ($pythonPath) {
                    $pythonCheck = & $pythonPath --version 2>&1
                    Write-Host "✓ Verified: $pythonCheck" -ForegroundColor Green
                } else {
                    Write-Host "⚠ Could not verify Python installation" -ForegroundColor Yellow
                }
            }
            else {
                Write-Host "✗ Python installation failed with code: $($installProcess.ExitCode)" -ForegroundColor Red
                exit 1
            }
        }
        else {
            Write-Host "✗ Download file not found" -ForegroundColor Red
            exit 1
        }
    }
    catch {
        Write-Host "✗ Download failed: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "MANUAL INSTALLATION:" -ForegroundColor Yellow
        Write-Host "1. Visit: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "2. Download latest Python 64-bit Windows installer" -ForegroundColor Yellow
        Write-Host "3. Run installer with 'Add Python to PATH' CHECKED" -ForegroundColor Yellow
        Write-Host "4. Run this script again" -ForegroundColor Yellow
        exit 1
    }
}

# Now install SonarSniffer
Write-Host ""
Write-Host "Setting up SonarSniffer..." -ForegroundColor Cyan
Write-Host ""

# Get Python path again (in case it was just installed)
$pythonPath = Get-PythonPath
if (-not $pythonPath) {
    Write-Host "✗ Python not found after installation attempt" -ForegroundColor Red
    exit 1
}

$venvName = "sonarsniffer_env"
$venvPath = "$PWD\$venvName"

# Create virtual environment
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment: $venvName" -ForegroundColor Cyan
    & $pythonPath -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Use venv Python and pip
$venvPython = "$venvPath\Scripts\python.exe"
$venvPip = "$venvPath\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "✗ Virtual environment setup failed" -ForegroundColor Red
    exit 1
}

Write-Host "Activating virtual environment..." -ForegroundColor Cyan

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $venvPip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to upgrade pip" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Pip upgraded" -ForegroundColor Green

# Install build dependencies for Rust
Write-Host "Installing build dependencies..." -ForegroundColor Cyan
& $venvPip install setuptools-rust
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install build dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Build dependencies installed" -ForegroundColor Green

# Install SonarSniffer
Write-Host "Building and installing SonarSniffer..." -ForegroundColor Cyan
& $venvPip install -e .
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install SonarSniffer" -ForegroundColor Red
    exit 1
}
Write-Host "✓ SonarSniffer installed successfully!" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To use SonarSniffer:" -ForegroundColor Cyan
Write-Host "  1. Activate environment: .\$venvName\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "  2. Run commands: sonarsniffer --help" -ForegroundColor Gray
Write-Host ""
