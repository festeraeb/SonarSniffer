# Prerequisites Installation Guide

## What You Need Before Building

SonarSniffer requires **two free programs** to be installed on your computer. This guide helps you install them.

---

## Quick Status Check

**Before running `BUILD_INSTALLER.bat`, check if you have these installed:**

### ✓ Node.js (includes npm)
**Check if installed:**
1. Open PowerShell (right-click desktop → "Open PowerShell window here")
2. Type: `node --version`
3. Press Enter
   - If you see a version number (like `v18.0.0`), skip to Rust check
   - If you see "command not recognized", install Node.js

### ✓ Rust (includes cargo)
**Check if installed:**
1. Open PowerShell
2. Type: `cargo --version`
3. Press Enter
   - If you see a version number (like `cargo 1.70.0`), you're ready!
   - If you see "command not recognized", install Rust

---

## Installation Steps

### Step 1: Install Node.js (5 minutes)

**Why you need it:**
- Node.js includes npm (the package manager for JavaScript)
- Builds the frontend (user interface)

**How to install:**
1. Go to: https://nodejs.org/
2. Click the big **"LTS"** button (green)
3. Run the downloaded file (usually appears at bottom of screen)
4. Click **"Next"** on each screen
5. When you see "Install", click **"Install"**
6. Wait for installation to complete (1-2 minutes)
7. Click **"Finish"**
8. **Restart your computer** after installation

**Verify it worked:**
- Open PowerShell
- Type: `node --version`
- You should see a version number

### Step 2: Install Rust (10 minutes)

**Why you need it:**
- Rust is the language SonarSniffer is written in
- Cargo compiles (builds) the Rust code into an executable

**How to install:**
1. Go to: https://rustup.rs/
2. Click **"Download rustup-init.exe"**
3. Find the downloaded file and run it
4. You'll see a command-line window with options:
   ```
   Current installation options:

   default host triple: x86_64-pc-windows-msvc
   default toolchain: stable
   default profile: default
   modify PATH: yes

   1) Proceed with installation
   2) Customize installation
   3) Cancel installation
   >
   ```
5. Type `1` and press Enter (use default settings)
6. Wait for Rust to install (takes 5 minutes, 500+ MB download)
7. Press Enter when installation completes
8. **Restart your computer** after installation

**Verify it worked:**
- Open PowerShell
- Type: `cargo --version`
- You should see a version number

---

## After Installing Prerequisites

### Option 1: Let the Script Handle It (Recommended)

1. **Open** the `BUILD_INSTALLER.bat` file
2. Script checks if prerequisites are installed
3. If missing, it asks:
   ```
   Would you like to install Node.js now?
   Type 'yes' to install, or 'no' to skip:
   ```
4. Select **"yes"** to auto-launch the installers
5. Follow the prompts
6. **Restart your computer** when finished
7. Run the script again

### Option 2: Manual Check

1. After installing both programs, **restart your computer**
2. Verify each is working:
   ```powershell
   node --version    # Should show a number like v18.0.0
   cargo --version   # Should show a number like cargo 1.70.0
   ```
3. If both show version numbers, **prerequisites are ready!**
4. Now you can run `BUILD_INSTALLER.bat`

---

## Troubleshooting Prerequisites

### "Command not recognized" after installing Node.js

**This usually means Path isn't updated. Try:**

1. **Restart your computer** (most important!)
2. Open a **new PowerShell window**
3. Try: `node --version` again
4. If still doesn't work:
   - Check Node.js installed correctly:
     - Open File Explorer
     - Go to: `C:\Program Files\nodejs\`
     - You should see `node.exe` file
   - If not there, reinstall Node.js

### "Command not recognized" after installing Rust

**Same fix as Node.js:**

1. **Restart your computer** (most important!)
2. Open a **new PowerShell window**
3. Try: `cargo --version` again
4. If still doesn't work:
   - Check Rust installed correctly:
     - Open File Explorer
     - Go to: `C:\Users\[YourUsername]\.cargo\bin\`
     - You should see `cargo.exe` file
   - If not there, reinstall Rust

### Both installed but script still says they're missing

**Solution:**
1. Restart your computer (fixes this 95% of the time!)
2. Open PowerShell
3. Verify: `node --version` and `cargo --version`
4. Run `BUILD_INSTALLER.bat` again from a new PowerShell window

---

## System Requirements Review

| Component | Need | Check |
|-----------|------|-------|
| **Operating System** | Windows 7 SP1 or newer | `systeminfo` command |
| **RAM** | 2 GB minimum | Windows Settings → System |
| **Disk Space** | 500 MB free | File Explorer → Properties |
| **Node.js** | Latest LTS | `node --version` |
| **Rust** | Latest stable | `cargo --version` |

---

## What Gets Installed

### Node.js installs:
- `node.exe` - JavaScript runtime
- `npm` - Package manager
- Dependencies for 300+ JavaScript packages

**Total Size:** ~200 MB

### Rust installs:
- `rustc` - Rust compiler
- `cargo` - Rust package manager
- Rust standard library and tools

**Total Size:** ~500 MB

**Total for both:** ~700 MB (compressed)

---

## Can I Uninstall Them Later?

**Yes!** Both are completely removable:

**To uninstall Node.js:**
1. Windows Settings → Apps → Apps & features
2. Find "Node.js"
3. Click "Uninstall"

**To uninstall Rust:**
1. Open PowerShell
2. Type: `rustup self uninstall`
3. Confirm when asked

Then delete the folders:
- `C:\Program Files\nodejs\`
- `C:\Users\[YourUsername]\.cargo\`
- `C:\Users\[YourUsername]\.rustup\`

---

## Still Having Issues?

**Before contacting support, try:**

1. ✓ Restart your computer
2. ✓ Run as Administrator:
   - Right-click PowerShell
   - Select "Run as Administrator"
   - Try commands again
3. ✓ Check versions:
   ```powershell
   node --version
   npm --version
   cargo --version
   rustc --version
   ```
4. ✓ Try installing again from scratch
   - Uninstall both
   - Restart
   - Reinstall

**Contact support** if still stuck:
- Email: support@sonarsniffer.dev
- Include: Your Windows version, error messages, command outputs

---

## Next Steps

Once prerequisites are installed and verified:

1. **Run** `BUILD_INSTALLER.bat`
2. **Follow the prompts** (takes 15 minutes)
3. **Double-click** the generated `SonarSniffer.exe`
4. **Start using** SonarSniffer!

---

**Current Version**: 0.1.0  
**Last Updated**: February 9, 2026  
**Status**: Prerequisites Guide Complete

**Questions?** See "Still Having Issues?" above or run `BUILD_INSTALLER.bat` - it handles everything!
