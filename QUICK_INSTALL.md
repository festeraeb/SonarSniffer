# Quick Install Reference

## Windows - Recommended Method

### Option 1: PowerShell Installer (Auto Everything)
```powershell
powershell -ExecutionPolicy Bypass -File install_nautidog_robust.ps1
```
✅ Auto-detects conda  
✅ Creates environment  
✅ Makes desktop shortcut  
⏱️ ~2-3 minutes

### Option 2: Python Installer (Works Without Conda in PATH)
```powershell
python install_nautidog_universal.py
```
✅ Even if conda missing from PATH  
✅ Auto-detects MATLAB  
✅ Cross-platform  
⏱️ ~3-4 minutes

### Option 3: Just Run Launcher
```powershell
launch_nautidog_conda.bat
```
✅ Auto-creates environment  
✅ Auto-finds conda  
⏱️ ~1-2 minutes (first time)

---

## Verify Installation Works

```powershell
# Check conda
conda --version

# Check NautiDog environment
conda env list

# Run Python
conda run -n nautidog python --version

# Test GUI (will launch window)
conda run -n nautidog python sonar_gui.py
```

---

## Troubleshooting

### "Conda not found"
→ Run: `powershell -ExecutionPolicy Bypass -File install_nautidog_robust.ps1`

### Still "Conda not found"
→ Install Miniconda: https://docs.conda.io/en/latest/miniconda.html

### "Permission denied"
→ Run PowerShell as Administrator

### "Conda is installed but script doesn't find it"
→ Close all PowerShell windows, open NEW one, try again

---

## Uninstall

```powershell
# Remove environment
conda env remove -n nautidog --yes

# Remove folder
rmdir /s "%USERPROFILE%\NautiDog Sailing"

# Remove shortcuts (automatic, but can delete manually)
```

---

## Enhancement Features (Opt-in)

### Video Acceleration (GPU)
- H.264/H.265 encoding with NVIDIA CUDA
- 10-50x faster than CPU encoding
- Auto-detects GPU, falls back to CPU

### PMTiles Generation
- Modern web tileset format
- Single-file (smaller than MBTiles)
- Works with all mapping libraries

### MATLAB Integration (Optional)
- Advanced spatial analysis
- Kriging interpolation
- Water column analysis
- Auto-finds MATLAB if installed

---

## What's Installed

✅ Python 3.11  
✅ PyQt5 (GUI)  
✅ NumPy, SciPy (Analysis)  
✅ GDAL (Geospatial)  
✅ OpenCV (Video)  
✅ Matplotlib (Plotting)  
✅ All dependencies for sonar parsing & export

---

## Getting Help

See: `INSTALLATION_GUIDE.md` (detailed troubleshooting)  
See: `GDAL_DEPLOYMENT_GUIDE.md` (for GDAL features)

---

**Installation Status**: ✅ Production Ready  
**All Installers**: Backward compatible, reversible  
**Testing**: No risk - can uninstall cleanly
