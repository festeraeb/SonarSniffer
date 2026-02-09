# SonarSniffer Beta - Quick Start (5 Minutes)

## Download & Install

### Windows

1. Download installer from beta portal
2. Run `.exe` file
3. Click "Next, Install, Finish"
4. App auto-launches

### macOS

1. Download `.dmg` file
2. Open and drag app to Applications
3. Open Applications folder
4. Double-click SonarSniffer

### Linux

```bash
chmod +x sonarsniffer-0.1.0.AppImage
./sonarsniffer-0.1.0.AppImage
```

---

## First Run Checklist (2 min)

- [ ] Click each tab: Dashboard, Process, Errors, Settings
- [ ] Open Settings, change one value, Save, Restart app
- [ ] Verify setting persisted

---

## Test Video Processing (3 min)

**Need**: One `.rsd` sonar data file

1. Click **"🎬 Process Video"**
2. Click "Browse" → select your `.rsd` file
3. Click "Browse" → choose output location
4. Click **"▶️ Start Processing"**
5. Wait for completion
6. Click **"📊 Dashboard"** → see results

---

## Export Telemetry

1. Click **"⚙️ Settings"**
2. Click **"📤 Export Telemetry"**
3. Save file
4. Send with feedback form

---

## Send Feedback

**Format**: BETA_FEEDBACK_FORM.md (included)

**Include**:

- Completed feedback form
- Telemetry export (.json)
- Any screenshots

**Send to**: `beta-feedback@sonarsniffer.dev`

---

## Troubleshoot (1 min)

**App won't start**

```
→ Restart computer
→ Uninstall & reinstall
→ Check disk space
```

**Processing hangs**

```
→ Wait 2-3 minutes
→ If no progress, close app
→ Try smaller RSD file
→ Try different parser
```

**Settings not saved**

```
→ Check app closed completely
→ Verify app data dir exists
→ Try different settings value
→ Restart and verify
```

---

## That's It

You now have everything needed for beta testing. Use the reference guide for detailed testing scenarios.

**Questions?** See BETA_TESTING_GUIDE.md
