# 👋 START HERE - SonarSniffer Installation

## What Do I Choose?

**Just want to use SonarSniffer?**  
→ Go to [INSTALLER_DOWNLOAD_LINKS.md](INSTALLER_DOWNLOAD_LINKS.md)

**Downloaded the installer?**  
→ Follow [WINDOWS_INSTALLATION_GUIDE.md](WINDOWS_INSTALLATION_GUIDE.md)

**Building from source code?**  
→ Double-click **`BUILD_INSTALLER.bat`** or follow below

**Desktop icon is missing?**  
→ Double-click **`CREATE_DESKTOP_SHORTCUT.bat`**

---

## Desktop Icon Not Showing? 

Don't worry, it's easy to fix!

### Option 1: Use the Shortcut Creator (Easiest)

1. Find **`CREATE_DESKTOP_SHORTCUT.bat`** in your SonarSniffer folder
2. Double-click it
3. **Done!** Icon appears on desktop

### Option 2: Quick Manual Fix

1. **Right-click your desktop**
2. Select **"New"** → **"Shortcut"**
3. Paste this location:
   ```
   C:\Program Files\SonarSniffer\SonarSniffer.exe
   ```
4. Name it: `SonarSniffer`
5. Click **"Finish"**
6. **Done!** Icon is on your desktop

### Option 3: From File Explorer

1. **Open File Explorer**
2. Go to: `C:\Program Files\SonarSniffer\`
3. **Right-click** `SonarSniffer.exe`
4. Select **"Send to"** → **"Desktop (create shortcut)"**
5. **Done!** Icon appears

---

## Quick Reference

### Files in This Folder

| File | What It Does | Click If... |
|------|-------------|-----------|
| **BUILD_INSTALLER.bat** | Builds the installer from source | You're building from source code |
| **CREATE_DESKTOP_SHORTCUT.bat** | Creates desktop icon | Icon is missing from desktop |
| **README_START_HERE.md** | ← You're reading this now | First time here |
| **PREREQUISITES_GUIDE.md** | How to install Node.js & Rust | You need to install dependencies |
| **INSTALLER_DOWNLOAD_LINKS.md** | Where to download the installer | You just want to install |
| **WINDOWS_INSTALLATION_GUIDE.md** | Detailed installation steps with pictures | You need help installing |
| **README.md** | Full project information | You want technical details |
| **QUICK_START.md** | How to use SonarSniffer | First time using the app |

---

## Prerequisites Needed to Build?

If you're building from source code, you need **two free programs**:

### ✓ Node.js (includes npm)
- Download: https://nodejs.org/ → Click **"LTS"**
- Install and restart your computer

### ✓ Rust (includes cargo)
- Download: https://rustup.rs/ → Click **"Download rustup-init.exe"**
- Install and restart your computer

**Don't worry!** If you don't have them, `BUILD_INSTALLER.bat` will ask if you want to install them and can help you!

**Full guide:** See [PREREQUISITES_GUIDE.md](PREREQUISITES_GUIDE.md)

---

### ⭐ Way 1: Download & Install (Easiest - 2 minutes)

```
1. Download installer file
   ↓
2. Double-click it
   ↓
3. Click "Next" → "Install" 
   ↓
4. Desktop icon appears automatically ✓
```

**See**: [INSTALLER_DOWNLOAD_LINKS.md](INSTALLER_DOWNLOAD_LINKS.md)

### 🚀 Way 2: One-Click Build (For developers - 15 minutes)

```
1. Click BUILD_INSTALLER.bat
   ↓
2. Wait for build to complete
   ↓
3. Click the installer it creates
   ↓
4. Desktop icon appears automatically ✓
```

**Click**: `BUILD_INSTALLER.bat`

### 🛠️ Way 3: Manual Build (Advanced)

```
1. npm install
2. cd src-tauri && cargo fetch && cd ..
3. npm run build:windows
4. Run the .exe file created
```

**See**: [WINDOWS_INSTALLATION_GUIDE.md](WINDOWS_INSTALLATION_GUIDE.md)

---

## Common Situations

### "I just downloaded the software"

1. Look for the downloaded file (probably in `Downloads`)
2. Double-click it
3. Follow the wizard
4. Desktop icon appears - done! ✓

### "I installed it but there's no desktop icon"

1. Double-click **`CREATE_DESKTOP_SHORTCUT.bat`**
2. Icon appears on desktop - done! ✓

### "I want to build it myself"

1. Double-click **`BUILD_INSTALLER.bat`**
2. Wait for build (takes 10-15 minutes)
3. When done, run the installer it creates
4. Desktop icon appears - done! ✓

### "Installation keeps failing"

1. **Restart your computer** (fixes 80% of issues!)
2. **Right-click installer** → **"Run as Administrator"**
3. Try installing again

---

## What Happens When You Install

✓ Creates **`C:\Program Files\SonarSniffer\`** folder  
✓ Installs all necessary application files  
✓ Creates **Start Menu** shortcut  
✓ Creates **Desktop** icon automatically  
✓ Registers app with Windows  

All automatic - you don't do anything except click "Install"!

---

## After Installation

1. **Look at your desktop** - You should see "SonarSniffer" icon
2. **Double-click the icon** - App launches
3. **Read [QUICK_START.md](QUICK_START.md)** - Learn how to use it

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Desktop icon is missing | Run `CREATE_DESKTOP_SHORTCUT.bat` |
| Installation fails | Restart computer, run as Administrator |
| Can't find installed app | Check `C:\Program Files\SonarSniffer\` |
| Windows warns about security | Click "More info" → "Run anyway" - it's safe! |
| Build fails (from source) | Delete `node_modules` folder, run `npm install` again |
| "npm not found" error | Install Node.js from nodejs.org |
| "cargo not found" error | Install Rust from rustup.rs |

---

## Need More Help?

📖 **Installation Help**  
→ [WINDOWS_INSTALLATION_GUIDE.md](WINDOWS_INSTALLATION_GUIDE.md)

📥 **Download & Links**  
→ [INSTALLER_DOWNLOAD_LINKS.md](INSTALLER_DOWNLOAD_LINKS.md)

🚀 **How to Use the App**  
→ [QUICK_START.md](QUICK_START.md)

📚 **Full Documentation**  
→ [README.md](README.md)

📧 **Contact Support**  
→ support@sonarsniffer.dev

---

## Quick Checklist

Before installing, make sure you have:

- [ ] **100 MB free disk space** (for installation)
- [ ] **Windows 7 or newer**
- [ ] **2 GB RAM** (minimum)
- [ ] **Internet connection** (for downloading only)

---

## TL;DR (Too Long; Didn't Read)

1. **Get the installer** - Download or build it
2. **Double-click it** - Windows handles rest
3. **See desktop icon** - Click to launch
4. **Done!** Start using SonarSniffer

That's it! No command lines, no complex steps. 👍

---

**Questions?** See the relevant guide above.  
**Still stuck?** Re-read this page carefully - answer is probably here! 

**Remember**: Most issues are fixed by restarting your computer! 💻
