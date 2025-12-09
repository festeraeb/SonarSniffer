# SonarSniffer Windows Installation Guide

## Quick Start (3 Steps)

### Step 1: Run Pre-Installation Test
```batch
test_windows_setup.bat
```
This checks if your system is ready. If this fails, fix the issues before proceeding.

### Step 2: Run the Installer
```batch
install_windows.bat
```
Press any key when prompted. The script will:
- Create a `sonarsniffer_env` folder
- Install SonarSniffer and all dependencies
- Display success message

### Step 3: Verify Installation
```batch
verify_installation.bat
```
This confirms everything works. You should see "✓ Success!"

## After Installation

To use SonarSniffer, you need to activate the environment first:

```batch
sonarsniffer_env\Scripts\activate.bat
```

You should see `(sonarsniffer_env)` at the start of your command prompt:
```
(sonarsniffer_env) C:\path\to\SonarSniffer>
```

Then you can use commands:

```batch
REM Get help
sonarsniffer --help

REM Analyze a sonar file
sonarsniffer analyze your_file.RSD

REM Start web interface
sonarsniffer web your_file.RSD --port 8080

REM Check licensing
sonarsniffer license --validate YOUR_KEY
```

## What Each Script Does

### `test_windows_setup.bat` (Run First)
✓ Checks if Python is installed  
✓ Verifies venv module is available  
✓ Confirms pip is working  
✓ Tests write permissions  

**Takes**: 2-3 seconds  
**Result**: Green checkmarks = you're good to go

### `install_windows.bat` (The Main Installer)
✓ Creates isolated Python environment in `sonarsniffer_env/`  
✓ Installs SonarSniffer package  
✓ Installs all dependencies:
  - numpy (scientific computing)
  - matplotlib (visualization)
  - Pillow (image processing)
  - requests (HTTP library)
  - docopt (command-line parsing)  

**Takes**: 3-5 minutes (first time slower, subsequent runs faster)  
**Result**: "Installation Complete!" message

### `verify_installation.bat` (Confirmation)
✓ Checks environment was created  
✓ Activates environment  
✓ Verifies SonarSniffer is installed  
✓ Tests CLI interface works  
✓ Checks all dependencies are present  

**Takes**: 5-10 seconds  
**Result**: "Verification Complete - Success!"

## Troubleshooting

### "Python is not installed"
**Solution**: 
1. Download Python from https://python.org (3.8 or newer)
2. Run the installer
3. **IMPORTANT**: Check "Add Python to PATH" during installation
4. Restart your Command Prompt
5. Run `test_windows_setup.bat` again

### "Permission denied" or "Access is denied"
**Solution**:
1. Right-click Command Prompt
2. Select "Run as Administrator"
3. Run the scripts again

### "pip install fails with module error"
**Solution**:
1. This usually means Python installation is incomplete
2. Uninstall Python completely
3. Reinstall from https://python.org
4. Make sure to check "tcl/tk and IDLE" during installation

### "Cannot find sonarsniffer command"
**Checklist**:
1. Did you run `verify_installation.bat` and see success?
2. Are you in the right directory?
3. Did you activate the environment with: `sonarsniffer_env\Scripts\activate.bat`
4. Does your prompt show `(sonarsniffer_env)` prefix?

If all yes, contact: festeraeb@yahoo.com

### "ModuleNotFoundError: No module named 'docopt'"
This was a bug in older versions. You have the fixed version - should not happen.
If it does, re-run: `install_windows.bat`

## System Requirements

- **Windows 10 or 11** (tested on Windows 10)
- **Python 3.8 or newer** (3.9, 3.10, 3.11 recommended)
- **2 GB free disk space** (minimum)
- **Administrator access** (for first installation)

## What Gets Installed

All installation files go into `sonarsniffer_env/` folder:
```
sonarsniffer_env/
├── Scripts/           (executables and activation scripts)
├── Lib/               (Python packages)
└── Include/           (Python headers)
```

This is an **isolated** Python environment - completely separate from your system Python. Safe to delete if needed.

## Updating SonarSniffer

To update to a newer version:
1. Activate environment: `sonarsniffer_env\Scripts\activate.bat`
2. Run: `pip install --upgrade sonarsniffer`

## Getting Help

If you hit any issues:

1. **Run diagnostics**: `test_windows_setup.bat`
2. **Check the error message** - it usually tells you what's wrong
3. **Try as Administrator** - right-click Command Prompt, "Run as administrator"
4. **Contact**: festeraeb@yahoo.com (include the error message)

## What's Fixed in This Version

✅ **docopt dependency** - Now included in installation  
✅ **Conda detection** - Removed (was unreliable on Windows)  
✅ **Environment activation** - More reliable  
✅ **Error messages** - Much clearer  
✅ **Verification** - Added post-install checker  

---

**Ready to install?** Start with: `test_windows_setup.bat`
