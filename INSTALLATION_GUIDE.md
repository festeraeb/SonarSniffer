# NautiDog Sailing - Installation Guide

## Quick Start (Recommended)

### Windows

**Option 1: PowerShell Installer (Recommended)**
```powershell
# Open PowerShell as Administrator
powershell -ExecutionPolicy Bypass -File install_nautidog_robust.ps1
```

**Option 2: Python Installer (Works with or without conda)**
```powershell
python install_nautidog_universal.py
```

**Option 3: Manual Batch Launch**
- Run `launch_nautidog_conda.bat` directly
- Script will auto-create environment and launch

### Linux/macOS

```bash
python3 install_nautidog_universal.py
# or
bash launch_nautidog.sh
```

---

## Troubleshooting Installation Errors

### Error: "Conda is not recognized"

**Problem**: Conda not found in system PATH after installation

**Solutions**:

1. **Verify Miniconda is installed**
   - Download from: https://docs.conda.io/en/latest/miniconda.html
   - Install to default location (typically `C:\Users\YourName\Miniconda3`)
   - **Important**: Check "Add Miniconda3 to my PATH" during installation

2. **Close and reopen PowerShell/CMD**
   - Conda requires shell restart to update PATH
   - Close all terminal windows
   - Open fresh PowerShell or CMD
   - Try installer again

3. **Use Python installer instead**
   ```powershell
   python install_nautidog_universal.py
   ```
   This method auto-detects conda even if not in PATH

4. **Manually set PATH (Advanced)**
   ```powershell
   $env:PATH = "C:\Users\YourName\Miniconda3\Scripts;" + $env:PATH
   conda --version  # Should show version now
   ```

### Error: "Pip is not recognized"

**Problem**: Pip not available in conda environment

**Solutions**:

1. **Use our robust installer** - handles pip setup automatically
   ```powershell
   python install_nautidog_universal.py
   ```

2. **Manual conda environment creation**
   ```powershell
   conda env create -n nautidog -f environment.yml --yes
   ```

3. **Reinstall conda**
   - Uninstall Miniconda from Control Panel
   - Restart computer
   - Download latest Miniconda: https://docs.conda.io/en/latest/miniconda.html
   - Install with defaults

### Error: "Permission denied" or "Access denied"

**Solutions**:
- Run PowerShell as Administrator (right-click → Run as Administrator)
- Or use Python directly: `python install_nautidog_universal.py`

### Error: "environment.yml not found"

**Problem**: Running installer from wrong directory

**Solution**:
- Make sure you're in the NautiDog project directory
- Verify `environment.yml` exists with: `dir environment.yml`
- Then run installer

---

## Verification

After installation, verify everything works:

```powershell
# Test conda environment
conda run -n nautidog python --version

# Test key imports
conda run -n nautidog python -c "import PyQt5, numpy, scipy; print('All imports OK')"

# Launch application
conda run -n nautidog python sonar_gui.py
```

---

## Advanced Options

### Custom Installation Path

```powershell
python install_nautidog_universal.py --install-path "C:\Program Files\NautiDog"
```

### Skip Verification

```powershell
python install_nautidog_universal.py --skip-verification
```

### Manual Environment Setup

```powershell
# Create environment manually
conda env create -n nautidog -f environment.yml --yes

# Launch GUI
conda run -n nautidog python sonar_gui.py
```

---

## Uninstall

### Windows

```powershell
# Option 1: Use installer with uninstall flag
powershell -ExecutionPolicy Bypass -File install_nautidog_robust.ps1 -Uninstall

# Option 2: Manual uninstall
conda env remove -n nautidog --yes
rmdir /s "%USERPROFILE%\NautiDog Sailing"
```

### Linux/macOS

```bash
conda env remove -n nautidog --yes
rm -rf ~/nautidog_sailing
```

---

## Checking Your Installation

### Verify Conda

```powershell
conda --version
conda env list
```

Should show something like:
```
conda 24.1.2
# conda environments:
nautidog              C:\Users\YourName\Miniconda3\envs\nautidog
```

### Verify Python

```powershell
conda run -n nautidog python --version
```

Should show Python 3.10+

### Verify Packages

```powershell
conda run -n nautidog pip list | findstr "PyQt5 numpy scipy gdal"
```

---

## Getting Help

If installation still fails:

1. **Check installer output** - Look for specific error messages
2. **Verify Miniconda installed correctly** - Run `conda --version` in new PowerShell
3. **Reinstall Miniconda** - Sometimes required for clean install
4. **Use Python installer** - `python install_nautidog_universal.py` is most robust

**Last resort**: Manual environment creation
```powershell
conda env create -n nautidog -f environment.yml --yes
conda run -n nautidog python sonar_gui.py
```

---

## System Requirements

- **Windows**: Windows 7 or later (10/11 recommended)
- **Python**: 3.10 or later (installed via Miniconda)
- **RAM**: 4GB minimum, 8GB+ recommended
- **Disk**: 2GB free space (conda + dependencies)

---

## Next Steps After Installation

1. **Launch NautiDog**: Double-click desktop shortcut or run launcher
2. **Configure survey**: Set up your sonar device and survey parameters
3. **Import data**: Load your RSD, XTF, or other sonar files
4. **Export results**: Generate KML, MBTiles, DEMs, or video

See `README.md` for detailed usage instructions.
