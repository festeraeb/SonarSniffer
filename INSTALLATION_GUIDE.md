# SonarSniffer Installation Guide - Windows & macOS

## Installation Scripts Overview

Two installation scripts are provided:
- **`install_windows.ps1`** - PowerShell script for Windows
- **`install_macos.sh`** - Bash script for macOS

Both scripts:
1. ✓ Dynamically detect latest Python version
2. ✓ Auto-install Python if not found
3. ✓ Install Rust toolchain (required for RSD parser)
4. ✓ Create isolated virtual environment
5. ✓ Build and install SonarSniffer with all dependencies

## Windows Installation

### System Requirements
- Windows 10/11 (64-bit)
- Internet connection
- Administrator access (optional, for system-wide Python install)

### How It Works
```
install_windows.ps1
├─ Detect Python installation
├─ Fetch latest Python version (3.14.0+)
├─ Download Python 64-bit installer using PowerShell WebClient
├─ Install Python with /passive /PrependPath=1 flags
├─ Create virtual environment (sonarsniffer_env)
├─ Install build tools (setuptools, wheel, setuptools-rust)
├─ Build Rust extension (rsd_parser_rust)
└─ Install SonarSniffer package
```

### Known Windows Issues & Solutions

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| Python download fails (batch methods) | Network stack/firewall | PowerShell uses different network stack that works better |
| `python` command not found | PATH not updated after install | Restart terminal or run: `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")` |
| Rust compilation fails | MSVC toolchain missing | Install Visual Studio Build Tools with C++ support |
| `pyo3` not found error | pyproject.toml listed it as Python package | Fixed in pyproject.toml - pyo3 is Rust dependency |
| Virtual env activation fails | Execution policy blocking | Run: `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force` |
| Long paths causing issues | Windows 260 character path limit | Use short working directory names |

### Running Windows Installation

```powershell
# Allow script execution for this session
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Navigate to project directory
cd C:\Temp\Garminjunk

# Run installer (detects Python 3.14+, installs if needed)
.\install_windows.ps1
```

### After Installation (Windows)

```powershell
# Activate environment
.\sonarsniffer_env\Scripts\activate.ps1

# Verify installation
sonarsniffer --help

# Test with RSD file
sonarsniffer analyze "path\to\file.rsd"

# Deactivate when done
deactivate
```

---

## macOS Installation

### System Requirements
- macOS 10.14+ (Intel or Apple Silicon)
- Internet connection
- Homebrew (will auto-install if missing)
- Xcode Command Line Tools (will auto-install if missing)

### How It Works
```
install_macos.sh
├─ Detect macOS version and architecture (Intel/Apple Silicon)
├─ Install Homebrew if missing
├─ Install Xcode Command Line Tools if missing
├─ Install Rust toolchain if missing
├─ Detect latest Python version dynamically
├─ Install Python via Homebrew if needed
├─ Create virtual environment (sonarsniffer_env)
├─ Install build tools (setuptools, wheel, setuptools-rust)
├─ Build Rust extension (rsd_parser_rust)
└─ Install SonarSniffer package
```

### Known macOS Issues & Solutions

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| Xcode tools installation hangs | Large download (5-12GB) | Run `xcode-select --install` manually, be patient |
| Homebrew not in PATH | Architecture-specific paths | Intel: `/usr/local`, Apple Silicon: `/opt/homebrew` (auto-detected) |
| Rust compilation fails | Missing LLVM tools | Already installed with Xcode Command Line Tools |
| Python version mismatch | Homebrew installs latest | Script uses version detection to match latest stable |
| Permission denied on script | Execution bit not set | Run: `chmod +x install_macos.sh` before executing |
| `M1/M2 chip compatibility` | ARM64 architecture | Script auto-detects and configures for Apple Silicon |

### Running macOS Installation

```bash
# Make script executable
chmod +x install_macos.sh

# Navigate to project directory
cd /path/to/sonarsniffer

# Run installer
./install_macos.sh
```

The script will:
1. Check for/install Homebrew (if missing)
2. Check for/install Xcode tools (if missing, may take 10-30 minutes)
3. Check for/install Rust (if missing)
4. Detect and optionally install latest Python
5. Create virtual environment
6. Build and install SonarSniffer

### After Installation (macOS)

```bash
# Activate environment
source sonarsniffer_env/bin/activate

# Verify installation
sonarsniffer --help

# Test with RSD file
sonarsniffer analyze path/to/file.rsd

# Deactivate when done
deactivate
```

---

## Comparison: Windows vs macOS

### Python Management
- **Windows**: Downloaded from python.org official FTP, installed via MSI
- **macOS**: Managed through Homebrew package manager

### Compilation Toolchain
- **Windows**: Requires MSVC (Visual Studio Build Tools)
- **macOS**: Uses Clang (comes with Xcode Command Line Tools)

### Virtual Environments
- **Windows**: Built into Python, created with `python -m venv`
- **macOS**: Same method, identical behavior

### Rust Installation
- **Windows**: Must use rustup installer
- **macOS**: Can use rustup or Homebrew (script uses rustup for consistency)

### Shell/Path Management
- **Windows**: PowerShell, uses `$env:Path`, `.ps1` scripts
- **macOS**: Bash/Zsh, uses `$PATH`, `.sh` scripts

### Key Differences
| Aspect | Windows | macOS |
|--------|---------|-------|
| Package manager | None (manual download) | Homebrew |
| System tools | Visual Studio Build Tools | Xcode Command Line Tools |
| Path separator | `\` | `/` |
| Script format | PowerShell (.ps1) | Bash (.sh) |
| Activate venv | `Scripts\activate.ps1` | `bin/activate` |
| Compiler | MSVC | Clang |

---

## Troubleshooting

### Both Platforms

**Problem**: "No module named setuptools_rust"
```bash
pip install setuptools-rust
```

**Problem**: Rust compilation errors
```bash
# Ensure Rust is updated
rustup update

# Clean build
cargo clean
```

**Problem**: Virtual environment not activating
```bash
# Windows
.\sonarsniffer_env\Scripts\activate.ps1

# macOS
source sonarsniffer_env/bin/activate
```

### Windows Specific

**Problem**: PowerShell execution policy error
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
```

**Problem**: Python not in PATH after install
```powershell
# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### macOS Specific

**Problem**: "xcode-select: error: tool requires Xcode"
```bash
xcode-select --install
# Be patient - this can take 10-30 minutes
```

**Problem**: Homebrew command not found (Apple Silicon)
```bash
eval "$(/opt/homebrew/bin/brew shellenv)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
```

**Problem**: Permission denied when running script
```bash
chmod +x install_macos.sh
./install_macos.sh
```

---

## Verification Checklist

After installation, verify everything works:

### Windows
```powershell
# 1. Activate environment
.\sonarsniffer_env\Scripts\activate.ps1

# 2. Check Python
python --version

# 3. Check Rust (should work)
rustc --version

# 4. Check SonarSniffer
sonarsniffer --help

# 5. Check license
sonarsniffer license --validate

# 6. Test with RSD file
sonarsniffer analyze "HistoryofCESARSNIFFERBAGFILE\Garmin RSD\garminrsdfiles\Sonar000.RSD"
```

### macOS
```bash
# 1. Activate environment
source sonarsniffer_env/bin/activate

# 2. Check Python
python3 --version

# 3. Check Rust
rustc --version

# 4. Check SonarSniffer
sonarsniffer --help

# 5. Check license
sonarsniffer license --validate

# 6. Test with RSD file
sonarsniffer analyze path/to/file.rsd
```

---

## Network Issues

Both scripts download Python and dependencies from the internet. If downloads fail:

1. **Check internet connection**
   ```
   Windows: ipconfig
   macOS:   ifconfig
   ```

2. **Check firewall/proxy settings**
   - Ensure python.org, github.com, crates.io are not blocked
   - If behind proxy, configure system proxy settings

3. **Manual Download Option (Windows)**
   ```powershell
   # Download manually from https://python.org/downloads/
   # Install with "Add Python to PATH" checked
   # Then run: .\install_windows.ps1
   ```

4. **Manual Installation (macOS)**
   ```bash
   # Install dependencies manually
   brew install python3 rustup
   rustup-init
   
   # Then run: ./install_macos.sh
   ```

---

## Technical Details

### Rust Extension Building
- The RSD parser includes a Rust native extension for performance
- Built using PyO3 (Rust ↔ Python binding framework)
- Requires:
  - Rust toolchain (installed automatically)
  - C compiler (MSVC on Windows, Clang on macOS)
  - setuptools-rust (Python package for Rust/Python integration)

### Virtual Environment Isolation
- Each installation creates isolated `sonarsniffer_env` directory
- Contains Python interpreter, pip, and all packages
- Does not affect system Python
- Can be deleted if clean reinstall needed: `rm -r sonarsniffer_env`

### License Management
- First install auto-creates 30-day trial license
- Stored at: `~/.sonarsniffer/license.json`
- Can generate new licenses: `sonarsniffer license --generate`
- Can validate licenses: `sonarsniffer license --validate <key>`

---

## Support & Updates

For issues or questions:
1. Check the troubleshooting section above
2. Review error messages in installation output
3. Check GitHub repository for updates
4. Create issue with full error output and system info

---

Last Updated: December 2025
Python Version: 3.14.0+
Rust Version: 1.70+
