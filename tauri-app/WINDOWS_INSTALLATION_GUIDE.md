# SonarSniffer Windows Installation Guide

**For Non-Technical Users** - This guide walks you through every step.

---

## Option 1: Using the Installer (Easiest) ⭐

### Step 1: Download and Run the Installer

1. **Download** the `SonarSniffer-0.1.0.exe` or `SonarSniffer.msi` file
2. **Double-click** the installer file
3. Wait while the installer runs (this may take 30-60 seconds)

### Step 2: Installation Window

When the installer opens, you'll see:

```
┌─────────────────────────────────────────┐
│  SonarSniffer Setup Wizard              │
├─────────────────────────────────────────┤
│                                          │
│  Choose Installation Options:            │
│                                          │
│  ☑ Create Desktop Shortcut               │
│  ☑ Add to Start Menu                     │
│  ☑ Associate with device files           │
│                                          │
│     [< Back]  [Next >]  [Cancel]        │
└─────────────────────────────────────────┘
```

**All the important boxes are already checked for you!**

### Step 3: Choose Installation Location

The installer suggests: `C:\Program Files\SonarSniffer`

**Just click "Next" unless you have a specific reason to change it.**

### Step 4: Click "Install"

The installer will:
- Copy files to your computer
- Create a Start Menu shortcut
- **Create a Desktop icon automatically**
- Register the application

This takes about 1-2 minutes.

### Step 5: Launch SonarSniffer

When installation is complete, you'll see:

```
✓ Installation Complete

☑ Launch SonarSniffer now

[Finish]
```

**Click the checkbox and then "Finish"** to start using SonarSniffer!

### Finding SonarSniffer After Installation

You can launch the app in three ways:

1. **Desktop Icon** - Double-click the "SonarSniffer" icon on your desktop
2. **Start Menu** - Click Start menu → Search for "SonarSniffer" → Click it
3. **Task Bar** - Pin it to your taskbar for quick access:
   - Right-click desktop icon
   - Select "Pin to taskbar"

---

## Option 2: Building from Source (For Developers)

### Prerequisites

You need to install two free tools:

1. **Node.js** (includes npm)
   - Go to: https://nodejs.org/
   - Click "LTS" (Long Term Support)
   - Install with default settings
   - Restart your computer after installing

2. **Rust**
   - Go to: https://rustup.rs/
   - Click "Download rustup-init.exe"
   - Run the installer
   - Keep all default options
   - Restart your computer after installing

### Building Steps

1. **Extract the source code** to a folder (e.g., `C:\SonarSniffer`)

2. **Right-click in the folder** and select "Open PowerShell window here"

3. **Copy and paste this command** (right-click to paste):
   ```powershell
   npm install
   ```
   Press Enter and wait (this takes 2-3 minutes)

4. **Copy and paste this command**:
   ```powershell
   cd src-tauri; cargo fetch; cd ..
   ```
   Press Enter and wait (this takes 2-3 minutes)

5. **Copy and paste this command** to build:
   ```powershell
   npm run build:windows
   ```
   Press Enter and wait (this takes 5-10 minutes depending on your computer)

6. **When it's done**, you'll see:
   ```
   ✓ SonarSniffer built successfully
   ```

7. **Find the installer** at:
   ```
   src-tauri\target\x86_64-pc-windows-msvc\release\SonarSniffer.exe
   ```

8. **Double-click** that file to install and run!

---

## Option 3: One-Click Build Script (Easiest for Developers)

1. **Extract the source code** to a folder

2. **Double-click** the file named `BUILD_INSTALLER.bat`

3. Wait while it builds (takes 10-15 minutes total)

4. **When done**, it shows you where the installer is located

5. **Double-click the installer** to install SonarSniffer

---

## Troubleshooting

### "Windows protected your PC"

If you see this warning:

```
⚠ Windows Defender SmartScreen
  Windows protected your PC

  Windows Defender SmartScreen prevented an unrecognized app from 
  starting. Running this app might put your PC at risk.
```

**This is normal for new apps!** Click:
- "More info"
- "Run anyway"

The app is safe - Windows just hasn't seen it before.

### "Installation failed"

**Try these steps:**

1. Restart your computer
2. Right-click the installer → Select "Run as Administrator"
3. Click "Yes" when asked for permission

### "Desktop icon didn't appear"

**Create it manually:**

1. Find `C:\Program Files\SonarSniffer\SonarSniffer.exe`
2. Right-click → "Create shortcut"
3. Choose "Yes" when asked to create on desktop

### "Can't find SonarSniffer"

After installation, check these places:

1. **Desktop** - Look for the SonarSniffer icon
2. **Start Menu** - Click Start → Type "sonarsniffer" → Click it
3. **Program Files** - Open `C:\Program Files\SonarSniffer\`

### Still having trouble?

1. **Restart your computer** (fixes 90% of issues!)
2. **Uninstall** using Windows Settings:
   - Settings → Apps → Apps & Features
   - Find "SonarSniffer" → Click "Uninstall"
3. **Reinstall** using the installer again

---

## Verifying Installation

**To verify SonarSniffer installed correctly:**

1. **Look for the desktop icon** - You should see "SonarSniffer" displayed
2. **Start Menu** - Open Start menu and type "sonarsniffer"
3. **Program Files** - Open `C:\Program Files\` and look for "SonarSniffer" folder
4. **Launch the app** - If it opens and shows the main window, you're all set!

---

## Uninstalling SonarSniffer

If you need to remove SonarSniffer:

1. Click **Windows Start Menu**
2. Type **"add or remove programs"** and press Enter
3. Find **"SonarSniffer"** in the list
4. Click it → Click **"Uninstall"**
5. Click **"Yes"** to confirm

**To also remove the desktop icon:**
- Right-click the icon on your desktop
- Click "Delete"
- Click "Yes"

---

## Getting Help

**Common Issues:**
- ✅ Click "Run anyway" if Windows warns you
- ✅ Restart your computer if it doesn't work
- ✅ Run as Administrator if you get permission errors
- ✅ Check that all boxes are checked in the installer

**Still stuck?**
- Save the error message
- Take a screenshot
- Contact: support@sonarsniffer.dev

---

## What Gets Installed

When you install SonarSniffer, you get:

```
C:\Program Files\SonarSniffer\
├── SonarSniffer.exe          (the main app)
├── resources\                 (app files)
└── uninstall.exe             (to remove it)

Desktop Icon:                  (for easy access)
└── SonarSniffer shortcut

Start Menu:
└── SonarSniffer → SonarSniffer (shortcut)
```

---

**That's it!** You're ready to use SonarSniffer! 🎉

For first steps using the app, see: [QUICK_START.md](QUICK_START.md)

**Version**: 0.1.0  
**Last Updated**: February 9, 2026
