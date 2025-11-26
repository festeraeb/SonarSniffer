#!/usr/bin/env powershell
<#
.SYNOPSIS
    Smart Conda Environment Installer for NautiDog
    
.DESCRIPTION
    Creates or updates a conda environment with intelligent error handling.
    
    Features:
    - Auto-detects conda installation
    - Tries user's environment first (non-intrusive)
    - Option to create isolated clean environment
    - Tests all imports after installation
    - Auto-cleanup of old environments
    - Clear error messages with recovery options

.PARAMETER CreateClean
    Force creation of clean environment (delete old one first)

.PARAMETER DontDelete
    Don't delete old nautidog environment

.PARAMETER Verbose
    Show detailed output
#>

param(
    [switch]$CreateClean = $false,
    [switch]$DontDelete = $false,
    [switch]$Verbose = $false
)

# Color output
function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    $colors = @{
        "INFO"    = "Cyan"
        "SUCCESS" = "Green"
        "WARNING" = "Yellow"
        "ERROR"   = "Red"
        "PROMPT"  = "Magenta"
    }
    Write-Host "[$Status] $Message" -ForegroundColor $colors[$Status]
}

# Find conda
function Find-Conda {
    Write-Status "Searching for conda..." "INFO"
    
    # Try conda in PATH first
    try {
        $result = & conda --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Found conda in PATH" "SUCCESS"
            return "conda"
        }
    } catch {}
    
    # Common installation paths
    $paths = @(
        "$env:USERPROFILE\Miniconda3\Scripts\conda.exe",
        "$env:USERPROFILE\Anaconda3\Scripts\conda.exe",
        "$env:USERPROFILE\AppData\Local\Miniconda3\Scripts\conda.exe",
        "$env:ProgramFiles\Miniconda3\Scripts\conda.exe",
        "$env:ProgramFiles\Anaconda3\Scripts\conda.exe",
        "C:\Miniconda3\Scripts\conda.exe",
        "C:\Anaconda3\Scripts\conda.exe"
    )
    
    foreach ($path in $paths) {
        if (Test-Path $path) {
            Write-Status "Found conda at: $path" "SUCCESS"
            return $path
        }
    }
    
    Write-Status "Conda not found. Please install Miniconda/Anaconda first." "ERROR"
    return $null
}

# Check package availability
function Test-Packages {
    param([string]$EnvName)
    
    Write-Status "Testing package imports in environment: $EnvName" "INFO"
    
    $packages = @(
        "numpy",
        "scipy",
        "opencv",
        "PIL",
        "pandas",
        "psutil"
    )
    
    $missingPkgs = @()
    
    foreach ($pkg in $packages) {
        # Map short names to import names
        $importName = switch ($pkg) {
            "opencv" { "cv2" }
            "PIL" { "PIL" }
            default { $pkg }
        }
        
        $testCmd = "python -c `"import $importName; print('OK')`""
        
        if ($EnvName -eq "base") {
            & cmd /c "$testCmd" 2>$null | Out-Null
        } else {
            & conda run -n $EnvName cmd /c "$testCmd" 2>$null | Out-Null
        }
        
        if ($LASTEXITCODE -ne 0) {
            $missingPkgs += $pkg
            Write-Status "  Missing: $pkg" "WARNING"
        } else {
            Write-Status "  ✓ $pkg" "SUCCESS"
        }
    }
    
    return $missingPkgs
}

# Install packages
function Install-Packages {
    param(
        [string]$CondaExe,
        [string]$EnvName,
        [string[]]$Packages
    )
    
    Write-Status "Installing $($Packages.Count) packages..." "INFO"
    
    $pkgString = $Packages -join " "
    
    if ($EnvName -eq "base") {
        & cmd /c "$CondaExe install -y $pkgString"
    } else {
        & cmd /c "$CondaExe install -n $EnvName -y $pkgString"
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Installation successful" "SUCCESS"
        return $true
    } else {
        Write-Status "Installation failed" "ERROR"
        return $false
    }
}

# Prompt user for choice
function Get-UserChoice {
    param(
        [string]$Prompt,
        [string[]]$Options
    )
    
    Write-Status $Prompt "PROMPT"
    
    for ($i = 0; $i -lt $Options.Count; $i++) {
        Write-Host "  $($i+1). $($Options[$i])"
    }
    
    $choice = Read-Host "Enter choice (1-$($Options.Count))"
    
    if ($choice -ge 1 -and $choice -le $Options.Count) {
        return [int]$choice - 1
    } else {
        Write-Status "Invalid choice" "ERROR"
        return Get-UserChoice $Prompt $Options
    }
}

# Main script
function Main {
    Write-Host ""
    Write-Status "NautiDog Smart Environment Installer" "INFO"
    Write-Host ""
    
    # Find conda
    $condaExe = Find-Conda
    if (-not $condaExe) {
        Write-Status "FAILED: Conda not found. Please install Miniconda first." "ERROR"
        exit 1
    }
    
    # Check existing environment
    Write-Status "Checking for existing nautidog environment..." "INFO"
    $envExists = & cmd /c "$condaExe env list" 2>$null | Select-String -Pattern "nautidog" -Quiet
    
    if ($envExists -and -not $CreateClean) {
        Write-Status "Found existing nautidog environment" "WARNING"
        
        # Test current environment
        $missing = Test-Packages "nautidog"
        
        if ($missing.Count -eq 0) {
            Write-Status "All required packages already installed!" "SUCCESS"
            Write-Status "Environment is ready to use" "SUCCESS"
            
            # Offer to update anyway
            $choice = Get-UserChoice "Update environment with latest versions?" @(
                "Use current environment (no changes)",
                "Update to latest versions",
                "Create fresh environment (delete old one)"
            )
            
            if ($choice -eq 0) {
                Write-Status "No changes made. Environment ready." "SUCCESS"
                exit 0
            } elseif ($choice -eq 1) {
                # Update existing
                Write-Status "Updating environment..." "INFO"
                & cmd /c "$condaExe update -n nautidog -y -c conda-forge python numpy scipy opencv scikit-image"
                Write-Status "Environment updated" "SUCCESS"
                exit 0
            } else {
                $CreateClean = $true
            }
        } else {
            Write-Status "Missing $($missing.Count) packages" "WARNING"
            
            # Offer options
            $choice = Get-UserChoice "How to fix?" @(
                "Install missing packages only (quick)",
                "Create fresh environment (clean)",
                "Manual fix (I'll do it myself)"
            )
            
            if ($choice -eq 0) {
                # Install missing
                $pkgString = $missing -join " "
                Install-Packages $condaExe "nautidog" $missing
            } elseif ($choice -eq 1) {
                $CreateClean = $true
            } else {
                Write-Status "Please install packages manually or run this script again" "WARNING"
                exit 1
            }
        }
    }
    
    # Create clean environment if needed
    if ($CreateClean) {
        Write-Status "Creating fresh environment..." "INFO"
        
        # Delete old environment if exists
        if ($envExists -and -not $DontDelete) {
            Write-Status "Removing old nautidog environment..." "WARNING"
            & cmd /c "$condaExe env remove -n nautidog -y"
            Start-Sleep -Seconds 2
        }
        
        # Create new environment
        Write-Status "Creating new nautidog environment..." "INFO"
        & cmd /c "$condaExe create -n nautidog -y -c conda-forge python=3.10 numpy scipy opencv scikit-image pandas psutil numba gdal netCDF4 h5py"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Status "FAILED: Environment creation failed" "ERROR"
            Write-Status "Please check your conda installation and try again" "ERROR"
            exit 1
        }
        
        Write-Status "Environment created successfully" "SUCCESS"
    }
    
    # Test final environment
    Write-Status "Testing environment..." "INFO"
    $missing = Test-Packages "nautidog"
    
    if ($missing.Count -eq 0) {
        Write-Status "✓ All packages verified" "SUCCESS"
        Write-Status "Environment ready to use!" "SUCCESS"
        Write-Status ""
        Write-Status "To activate: conda activate nautidog" "INFO"
        Write-Status "To launch GUI: python sonar_gui.py" "INFO"
        Write-Host ""
        exit 0
    } else {
        Write-Status "WARNING: Missing packages: $($missing -join ', ')" "WARNING"
        Write-Status "Try installing manually: conda install -n nautidog $($missing -join ' ')" "INFO"
        exit 1
    }
}

# Run main
Main
