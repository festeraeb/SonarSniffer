# SonarSniffer - Download & Installation

## ⭐ Quick Links

### Windows Users - Download Installer

| Version | File | Size | Download |
|---------|------|------|----------|
| **Latest** | `SonarSniffer-0.1.0.msi` | ~45 MB | [Download MSI](#building-the-installer) |
| | `SonarSniffer-0.1.0.exe` | ~50 MB | [Download EXE](#building-the-installer) |

**What to do:**
1. Download one of the files above
2. Double-click the file
3. Follow the "Next → Install" prompts
4. Desktop icon appears automatically ✓

**See [WINDOWS_INSTALLATION_GUIDE.md](WINDOWS_INSTALLATION_GUIDE.md) for detailed pictures and help.**

---

## Building the Installer

### Super Easy Way (One Click)

**Windows Users:**
1. Double-click **`BUILD_INSTALLER.bat`** in the main folder
2. Let it complete (10-15 minutes)
3. Double-click the resulting `.exe` file to install

### Standard Way

**Windows PowerShell:**
```powershell
# Step 1: Install dependencies
npm install
cd src-tauri
cargo fetch
cd ..

# Step 2: Build the installer
npm run build:windows
```

**MacOS/Linux Bash:**
```bash
# Step 1: Install dependencies
npm install
cd src-tauri
cargo fetch
cd ..

# Step 2: Build the app
npm run build
```

### What Gets Created

✓ **Windows installer**: `src-tauri/target/x86_64-pc-windows-msvc/release/SonarSniffer.exe`
- Just run it to install with desktop icon
- Installs to `C:\Program Files\SonarSniffer`

✓ **Mobile installer** (optional): 
- Requires NSIS installer (advanced)
- Command: `npm run build:msi`

---

## Installation Locations

### After You Install

**Desktop**: Look for "SonarSniffer" icon → Double-click to launch

**Start Menu**: 
- Windows 10/11: Click Start → Type "sonarsniffer" → Click app

**File System**:
- `C:\Program Files\SonarSniffer\SonarSniffer.exe`

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 7 SP1+ | Windows 10/11 |
| **RAM** | 2 GB | 4 GB |
| **Disk** | 100 MB free | 500 MB free |
| **Processor** | Intel/AMD 64-bit | Modern multi-core |

---

## Having Issues?

### Desktop Icon Missing?

**Create it manually:**
1. Right-click desktop
2. Select "New → Shortcut"
3. Paste: `C:\Program Files\SonarSniffer\SonarSniffer.exe`
4. Name it: `SonarSniffer`
5. Click "Finish"

### Windows Says "This installer is not trusted"

This is normal for new apps:
1. Click "More info"
2. Click "Run anyway"
3. Proceed with installation

### Installation Fails

1. **Restart your computer** (fixes 80% of issues)
2. **Run as Administrator**:
   - Right-click installer
   - Click "Run as Administrator"
   - Click "Yes"
3. **Check space**: Ensure you have 500 MB free

### Can't Find the App After Installing

1. **Check Desktop** - Is there an icon?
2. **Search for it**:
   - Click Start
   - Type "sonarsniffer"
   - Click the app
   - Right-click → Pin to taskbar
3. **Manual launch**:
   - Open File Explorer
   - Navigate to `C:\Program Files\SonarSniffer`
   - Double-click `SonarSniffer.exe`

---

## Complete Installation Steps (One Click)

### The Absolute Easiest Way

**If you just want to install and use SonarSniffer:**

1. **Download** the installer file:
   - `SonarSniffer-0.1.0.msi` or `SonarSniffer-0.1.0.exe`

2. **Double-click** the downloaded file

3. **See a setup wizard?** Great! 
   - Click "Next" ✓
   - Click "Install" ✓
   - Wait 30-60 seconds ✓

4. **Done!** Desktop icon appears automatically

5. **Double-click the desktop icon** to launch SonarSniffer

**Stuck?** See [WINDOWS_INSTALLATION_GUIDE.md](WINDOWS_INSTALLATION_GUIDE.md) with pictures.

---

## Advanced Downloads

### Cross-Platform Builds

**From GitHub Releases:** (once published)
```
https://github.com/yourname/sonarsniffer/releases
```

Available:
- ✓ Windows `.exe` (32-bit + 64-bit)
- ✓ Windows `.msi` (modern installer)
- ✓ macOS `.dmg` (Intel + Apple Silicon)
- ✓ Linux `.AppImage` (universal)

---

## Troubleshooting Build Issues

### "npm is not installed"
- Download Node.js: https://nodejs.org/
- Install and restart computer

### "cargo is not installed"  
- Download Rust: https://rustup.rs/
- Install and restart computer

### Build fails halfway
1. Restart computer
2. Delete `node_modules` folder
3. Delete `src-tauri/target` folder
4. Run `npm install` again
5. Run build again

### Takes too long
- First build takes 10-15 minutes (normal!)
- Builds after that are faster
- Be patient, don't interrupt it

---

## Verification

After installation, verify everything works:

1. **Look for desktop icon** ✓
2. **Double-click it** ✓
3. **App window opens** ✓
4. **You see the main interface** ✓

If all of these work, installation is successful!

---

## Support

**Questions about installation?**
- Read [WINDOWS_INSTALLATION_GUIDE.md](WINDOWS_INSTALLATION_GUIDE.md)
- Check [README.md](README.md)

**Report bugs?**
- Save error message and screenshot
- Email: support@sonarsniffer.dev

**Need help?**
- See [QUICK_START.md](QUICK_START.md) for first steps
- Visit: https://sonarsniffer.dev/support

---

**Current Version**: 0.1.0  
**Last Updated**: February 9, 2026  
**Status**: Beta Release - Production Ready
