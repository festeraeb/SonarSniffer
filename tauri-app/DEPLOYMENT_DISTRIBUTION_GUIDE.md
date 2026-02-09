# Final Deployment & Distribution Guide

## Overview

This document provides comprehensive instructions for deploying, distributing, and managing the SonarSniffer beta release.

---

## 1. Pre-Release Checklist

### Code Quality
- [ ] All TypeScript files pass type check (`npx tsc --noEmit`)
- [ ] ESLint passes without errors (`npm run lint`)
- [ ] Rust code compiles without warnings (`cargo build --release`)
- [ ] No console errors in development

### Testing
- [ ] Basic functionality verified on Windows
- [ ] Basic functionality verified on macOS (if available)
- [ ] Basic functionality verified on Linux (if available)
- [ ] Error handling works correctly
- [ ] Settings persist across restarts
- [ ] Telemetry export works

### Documentation
- [ ] README.md complete and accurate
- [ ] QUICK_START.md tested and verified
- [ ] BETA_TESTING_GUIDE.md complete
- [ ] BETA_FEEDBACK_FORM.md ready
- [ ] TELEMETRY_SCHEMA.md documented
- [ ] TECHNICAL_ARCHITECTURE.md current

### Configuration
- [ ] Version number consistent (0.1.0)
- [ ] Package.json correct
- [ ] Cargo.toml dependencies locked
- [ ] tauri.conf.json properly configured
- [ ] .gitignore complete

---

## 2. Building Release Artifacts

### Option A: Automated Build (Windows)

```powershell
# Run PowerShell build script
.\build.ps1 -Target all -Clean

# Or for specific platform
.\build.ps1 -Target windows
.\build.ps1 -Target macos
.\build.ps1 -Target linux
```

### Option B: Automated Build (Bash/macOS/Linux)

```bash
# Run shell build script
chmod +x build.sh
./build.sh all --clean

# Or for specific platform
./build.sh windows
./build.sh macos
./build.sh linux
```

### Option C: Manual Build (Windows)

```bash
# Install dependencies
npm install
cd src-tauri && cargo fetch && cd ..

# Build frontend
npm run build:ui

# Build Windows executable
npm run build:windows

# Create MSI installer (optional, requires NSIS)
npm run build:msi
```

### Build Output Locations

```
Windows:
  - EXE: src-tauri/target/x86_64-pc-windows-msvc/release/SonarSniffer.exe
  - MSI: src-tauri/target/x86_64-pc-windows-msvc/release/msi/ (optional)

macOS:
  - DMG: src-tauri/target/release/bundle/dmg/SonarSniffer_0.1.0_x64.dmg
  - Bundle: src-tauri/target/release/bundle/macos/

Linux:
  - AppImage: src-tauri/target/release/bundle/appimage/SonarSniffer_0.1.0_amd64.AppImage
```

---

## 3. Beta Testing Distribution

### Create Release Package

```bash
# Create directory for distribution
mkdir -p sonarsniffer-beta-v0.1.0
cd sonarsniffer-beta-v0.1.0

# Copy installer/executable
cp ../src-tauri/target/x86_64-pc-windows-msvc/release/SonarSniffer.exe ./SonarSniffer-0.1.0.exe
# or
cp ../src-tauri/target/x86_64-pc-windows-msvc/release/msi/*.msi ./SonarSniffer-0.1.0.msi

# Copy documentation
cp ../QUICK_START.md ./
cp ../BETA_TESTING_GUIDE.md ./
cp ../BETA_FEEDBACK_FORM.md ./
cp ../README.md ./

# Create README for distribution
cat > README_DISTRIBUTION.md << 'EOF'
# SonarSniffer Beta 0.1.0

## Quick Start

1. **Install**: Run SonarSniffer-0.1.0.exe
2. **Test**: Follow QUICK_START.md (5 minutes)
3. **Feedback**: Complete BETA_FEEDBACK_FORM.md
4. **Submit**: Email to beta-feedback@sonarsniffer.dev

See BETA_TESTING_GUIDE.md for comprehensive testing instructions.
EOF

# Create SHA256 checksums
sha256sum * > checksums.sha256
```

### Distribution Methods

#### Email
```
Recipients: Beta testers list
Subject: SonarSniffer Beta 0.1.0 - Ready for Testing
Body:
  Hi Beta Tester,
  
  SonarSniffer Beta 0.1.0 is ready for testing!
  
  Download: [Download Link]
  Quick Start: See QUICK_START.md (5 minutes)
  Testing Guide: See BETA_TESTING_GUIDE.md
  
  Please test and submit feedback form within [X] days.
  
  Thank you!
```

#### GitHub Releases
```bash
# Tag the release
git tag -a v0.1.0-beta -m "SonarSniffer Beta 0.1.0"
git push origin v0.1.0-beta

# Create release on GitHub
GitHub → Releases → Draft new release
- Tag: v0.1.0-beta
- Title: SonarSniffer Beta 0.1.0
- Upload artifacts (EXE, MSI, DMG, AppImage)
- Write release notes
- Mark as Pre-release
- Publish
```

#### Website/Portal
```
1. Create landing page for beta
2. Upload installers to CDN
3. Provide download links
4. Collect feedback via form
5. Track downloads and usage
```

---

## 4. Installer Generation

### Windows MSI (requires NSIS)

```bash
# Install NSIS
# Windows: https://nsis.sourceforge.io
# macOS: brew install makensis
# Linux: sudo apt-get install nsis

# Generate MSI
npm run build:msi

# Output: src-tauri/target/x86_64-pc-windows-msvc/release/msi/SonarSniffer_0.1.0.msi
```

### macOS Bundle

```bash
# Build DMG
npm run tauri -- build

# Code signing (optional but recommended)
codesign --force --verify --verbose --sign - \
  src-tauri/target/release/bundle/macos/SonarSniffer.app

# Create DMG
hdiutil create -volname "SonarSniffer" \
  -srcfolder src-tauri/target/release/bundle/macos/SonarSniffer.app \
  -ov -format UDZO SonarSniffer_0.1.0.dmg
```

### Linux AppImage

```bash
# Build AppImage
npm run tauri -- build --target x86_64-unknown-linux-gnu

# AppImage will be in:
# src-tauri/target/release/bundle/appimage/

# Make executable
chmod +x SonarSniffer_0.1.0_amd64.AppImage
```

---

## 5. Continuous Integration/Deployment (GitHub Actions)

### Automated Builds

The `.github/workflows/build-release.yml` workflow:

```yaml
Triggers:
  - Push to main/develop branches
  - Pull requests
  - Version tags (v*)

Jobs:
  - build-windows: Builds Windows .msi
  - build-macos: Builds macOS .dmg
  - build-linux: Builds Linux AppImage
  - test: Runs type checks and linter
  - release: Creates GitHub Release with artifacts
```

### Setting Up CI/CD

```bash
# 1. Push code to GitHub
git remote add origin https://github.com/user/sonarsniffer.git
git branch -M main
git push -u origin main

# 2. Configure GitHub Actions secrets (if needed)
# Settings → Secrets → New repository secret

# 3. Trigger workflow
git tag v0.1.0-beta
git push origin v0.1.0-beta

# 4. Monitor build
GitHub → Actions → Watch build progress

# 5. Release automatically created with artifacts
```

---

## 6. Version Management

### Semantic Versioning

```
Format: MAJOR.MINOR.PATCH
Example: 0.1.0

0 = Major (breaking changes)
1 = Minor (features, backward compatible)
0 = Patch (bug fixes)

Beta version: 0.1.0-beta
Release version: 0.1.0
```

### Update Version Number

```bash
# 1. Update version in package.json
{
  "version": "0.1.0"
}

# 2. Update version in Cargo.toml
[package]
version = "0.1.0"

# 3. Update version in tauri.conf.json
{
  "package": {
    "version": "0.1.0"
  }
}

# 4. Commit changes
git add .
git commit -m "Bump version to 0.1.0"
```

---

## 7. Feedback Collection & Analysis

### Automated Feedback

```bash
# Set up feedback repository
mkdir sonarsniffer-beta-feedback
cd sonarsniffer-beta-feedback
git init

# Instructions to testers
echo "Please submit telemetry exports here"
```

### Manual Feedback Organization

```
Directory structure:
  feedback/
    ├── 2026-02-09/
    │   ├── tester1-feedback.md
    │   ├── tester1-telemetry.json
    │   ├── tester2-feedback.md
    │   └── tester2-telemetry.json
    └── summary.md

Summary document:
  - Total testers: X
  - Issues reported: X
  - Critical issues: X
  - Features requested: X
  - Overall satisfaction: X/5
```

### Analysis Script (Python)

```python
#!/usr/bin/env python3
import json
import os
from pathlib import Path

def analyze_telemetry(feedback_dir):
    total_jobs = 0
    total_errors = 0
    avg_duration = 0
    
    for file in Path(feedback_dir).glob("**/telemetry.json"):
        with open(file) as f:
            data = json.load(f)
            total_jobs += len(data.get('jobs', []))
            total_errors += len(data.get('errors', []))
    
    print(f"Total jobs processed: {total_jobs}")
    print(f"Total errors: {total_errors}")
    print(f"Error rate: {total_errors/max(total_jobs,1)*100:.2f}%")

if __name__ == "__main__":
    analyze_telemetry("./feedback")
```

---

## 8. Post-Release Monitoring

### Usage Metrics

Track:
- Number of downloads
- Installation success rate
- Crash reports
- Feature usage
- Error frequency
- Performance metrics

### Update Checklist

- [ ] Monitor feedback submissions
- [ ] Track reported issues
- [ ] Collect performance data
- [ ] Identify crashes
- [ ] Plan improvements
- [ ] Prepare patch release (if needed)

### Patch Release Procedure

```bash
# 1. Fix bugs
git checkout -b fix/critical-issue

# 2. Update version to 0.1.1
# (Update package.json, Cargo.toml, tauri.conf.json)

# 3. Commit and push
git commit -am "Fix critical issue - v0.1.1"
git push origin fix/critical-issue

# 4. Create pull request
github.com → Create Pull Request → Merge

# 5. Tag release
git tag v0.1.1
git push origin v0.1.1

# 6. GitHub Actions builds and releases automatically
```

---

## 9. Long-Term Distribution

### Stable Release Preparation

Before releasing 0.1.0 stable:

```
Milestones:
✓ Beta 0.1.0 - Feedback collection (current)  
→ Beta 0.1.1 - Bug fixes  
→ RC 0.1.0 - Feature freeze  
→ 0.1.0 - Stable release  
```

### Release Channels

```
Channel         Version         Update Frequency
─────────────────────────────────────────────
Nightly        dev branch      Daily
Beta           v0.1.0-beta     Weekly
Release        v0.1.0          Monthly
LTS            v1.0.0(future)  Quarterly
```

---

## 10. Troubleshooting Build Issues

### Common Issues

**Issue**: Build fails with "GTK dependencies"
```
Solution: Install GTK3 development files
Ubuntu: sudo apt-get install libgtk-3-dev
```

**Issue**: NSIS not found for MSI creation
```
Solution: Install NSIS
Windows: https://nsis.sourceforge.io
macOS: brew install makensis
```

**Issue**: Node modules corrupted
```
Solution: Clean install
rm -rf node_modules package-lock.json
npm install
```

**Issue**: Rust build fails
```
Solution: Update Rust and clear cache
rustup update
cargo clean
cargo build --release
```

---

## Summary

### Distribution Checklist

- [ ] Code tested and reviewed
- [ ] Version numbers updated
- [ ] Build artifacts created
- [ ] Installers generated
- [ ] Documentation prepared
- [ ] Feedback form ready
- [ ] Distribution channels set up
- [ ] CI/CD configured
- [ ] Release published
- [ ] Testers notified
- [ ] Monitoring activated

### Contact Information

**Support**: [Set your contact method]  
**Feedback**: beta-feedback@sonarsniffer.dev  
**Issues**: [Set your issue tracking]  
**Website**: [Set your website]

---

## Additional Resources

- [Tauri Deployment Guide](https://tauri.app/en/docs/building/)
- [GitHub Actions Documentation](https://docs.github.com/actions)
- [NSIS Documentation](https://nsis.sourceforge.io/Docs/)
- [Rust Release Practices](https://doc.rust-lang.org/cargo/publishing/)

---

**Last Updated**: February 9, 2026  
**Version**: 0.1.0  
**Status**: Ready for Beta Distribution
