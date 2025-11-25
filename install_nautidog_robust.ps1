# NautiDog Sailing Robust Installer
# Handles Miniconda/Anaconda installation and PATH issues

param(
    [string]$InstallPath = "$env:USERPROFILE\NautiDog Sailing",
    [switch]$Uninstall,
    [switch]$SkipConda = $false
)

function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    $colors = @{
        "INFO" = "Cyan"
        "SUCCESS" = "Green"
        "WARNING" = "Yellow"
        "ERROR" = "Red"
    }
    Write-Host "[$Status] $Message" -ForegroundColor $colors[$Status]
}

function Find-Conda {
    <# Find conda executable in common locations #>
    Write-Status "Searching for conda..." "INFO"
    
    # Try direct conda command first
    try {
        $result = & cmd /c "conda --version 2>nul"
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Found conda in PATH: $result" "SUCCESS"
            return "conda"
        }
    } catch {}
    
    # Common Miniconda/Anaconda install paths
    $commonPaths = @(
        "$env:USERPROFILE\Miniconda3\Scripts\conda.exe",
        "$env:USERPROFILE\Anaconda3\Scripts\conda.exe",
        "$env:USERPROFILE\AppData\Local\Miniconda3\Scripts\conda.exe",
        "$env:ProgramFiles\Miniconda3\Scripts\conda.exe",
        "$env:ProgramFiles\Anaconda3\Scripts\conda.exe",
        "C:\Miniconda3\Scripts\conda.exe",
        "C:\Anaconda3\Scripts\conda.exe"
    )
    
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            Write-Status "Found conda at: $path" "SUCCESS"
            return $path
        }
    }
    
    return $null
}

function Get-CondaPaths {
    param([string]$CondaExe)
    
    # Get conda root by running conda info
    $condaInfo = & cmd /c "$CondaExe info --json 2>nul" | ConvertFrom-Json
    $condaRoot = $condaInfo.conda_prefix
    
    return @{
        Root = $condaRoot
        Scripts = Join-Path $condaRoot "Scripts"
        Library = Join-Path $condaRoot "Library\bin"
        Bin = Join-Path $condaRoot "bin"
    }
}

function Setup-Environment {
    param([hashtable]$Paths)
    
    # Add conda paths to current session PATH
    $env:PATH = "$($Paths.Scripts);$($Paths.Library);$($Paths.Bin);$env:PATH"
    
    Write-Status "Environment PATH updated for conda access" "SUCCESS"
}

function Create-CondaEnvironment {
    param([string]$CondaExe, [string]$InstallPath)
    
    Write-Status "Creating NautiDog conda environment..." "INFO"
    
    $envYml = Join-Path $InstallPath "environment.yml"
    if (-not (Test-Path $envYml)) {
        Write-Status "ERROR: environment.yml not found at $envYml" "ERROR"
        return $false
    }
    
    # Check if environment already exists
    $envExists = & cmd /c "$CondaExe env list 2>nul" | Select-String -Pattern "nautidog" -Quiet
    
    if ($envExists) {
        Write-Status "NautiDog environment already exists - updating..." "INFO"
        & cmd /c "$CondaExe env update -n nautidog -f `"$envYml`" --prune"
    } else {
        & cmd /c "$CondaExe env create -n nautidog -f `"$envYml`" --yes"
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Conda environment created/updated successfully" "SUCCESS"
        return $true
    } else {
        Write-Status "ERROR: Failed to create/update conda environment" "ERROR"
        return $false
    }
}

function Verify-Installation {
    param([string]$CondaExe, [string]$InstallPath)
    
    Write-Status "Verifying installation..." "INFO"
    
    # Test Python availability
    Write-Status "Testing Python..." "INFO"
    $pythonTest = & cmd /c "$CondaExe run -n nautidog python --version 2>&1"
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Python: $pythonTest" "SUCCESS"
    } else {
        Write-Status "ERROR: Python test failed" "ERROR"
        return $false
    }
    
    # Test key imports
    Write-Status "Testing key imports..." "INFO"
    $imports = @("PyQt5", "numpy", "scipy")
    foreach ($import in $imports) {
        $result = & cmd /c "$CondaExe run -n nautidog python -c `"import $import`" 2>&1"
        if ($LASTEXITCODE -eq 0) {
            Write-Status "$import: OK" "SUCCESS"
        } else {
            Write-Status "$import: MISSING (non-critical)" "WARNING"
        }
    }
    
    return $true
}

function Create-Shortcuts {
    param([string]$InstallPath)
    
    Write-Status "Creating shortcuts..." "INFO"
    
    $WshShell = New-Object -ComObject WScript.Shell
    
    # Desktop shortcut
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktopPath "NautiDog Sailing.lnk"
    
    $shortcut = $WshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $InstallPath "launch_nautidog_conda.bat"
    $shortcut.WorkingDirectory = $InstallPath
    $shortcut.Description = "NautiDog Sailing - Marine Survey Platform"
    $shortcut.IconLocation = Join-Path $InstallPath "nautidog_logo.ico"
    $shortcut.Save()
    Write-Status "Created desktop shortcut" "SUCCESS"
    
    return $true
}

# Main installation flow
function Main {
    Write-Host "`n" 
    Write-Status "NautiDog Sailing Installation" "INFO"
    Write-Host "Installation path: $InstallPath`n"
    
    # Find conda
    $condaExe = Find-Conda
    if (-not $condaExe -and -not $SkipConda) {
        Write-Status "ERROR: Conda not found and SkipConda not set" "ERROR"
        Write-Status "Please install Miniconda from: https://docs.conda.io/en/latest/miniconda.html" "INFO"
        Write-Status "After installation, run this script again or use: .\install_nautidog_robust.ps1 -SkipConda" "INFO"
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    # Get conda paths and setup environment
    if ($condaExe) {
        $paths = Get-CondaPaths $condaExe
        Setup-Environment $paths
    }
    
    # Create installation directory
    if (-not (Test-Path $InstallPath)) {
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
        Write-Status "Created installation directory" "SUCCESS"
    }
    
    # Copy files
    Write-Status "Copying application files..." "INFO"
    $sourcePath = Split-Path $MyInvocation.MyCommand.Path -Parent
    Get-ChildItem $sourcePath -Exclude @("install_nautidog*.ps1", "*.lnk") -ErrorAction SilentlyContinue |
        Copy-Item -Destination $InstallPath -Recurse -Force -ErrorAction SilentlyContinue
    Write-Status "Files copied successfully" "SUCCESS"
    
    # Create conda environment if conda is available
    if ($condaExe) {
        if (-not (Create-CondaEnvironment $condaExe $InstallPath)) {
            Read-Host "Press Enter to exit"
            exit 1
        }
        
        # Verify installation
        if (-not (Verify-Installation $condaExe $InstallPath)) {
            Write-Status "Installation verification had issues, but continuing..." "WARNING"
        }
    } else {
        Write-Status "Skipping conda environment creation - conda not available" "WARNING"
        Write-Status "You can manually create environment later with: conda env create -f environment.yml" "INFO"
    }
    
    # Create shortcuts
    if (-not (Create-Shortcuts $InstallPath)) {
        Write-Status "Warning: Could not create shortcuts" "WARNING"
    }
    
    Write-Host "`n"
    Write-Status "Installation completed successfully!" "SUCCESS"
    Write-Status "To launch: Run 'NautiDog Sailing' from Desktop or Start Menu" "INFO"
    Write-Host "`n"
    
    Read-Host "Press Enter to exit"
}

Main
