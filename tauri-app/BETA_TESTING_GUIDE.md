# Beta Testing Guide - SonarSniffer Desktop

Welcome to SonarSniffer beta! This guide will help you test the application and provide valuable feedback.

## Installation

### Windows

1. Download: `sonarsniffer-0.1.0.exe`
2. Double-click to run installer
3. Follow installation wizard
4. Launch from Start Menu or Desktop shortcut

### macOS

1. Download: `sonarsniffer-0.1.0.dmg`
2. Drag app to Applications folder
3. Launch from Applications

### Linux

1. Download: `sonarsniffer-0.1.0.AppImage`
2. Make executable: `chmod +x sonarsniffer-0.1.0.AppImage`
3. Run: `./sonarsniffer-0.1.0.AppImage`

## Quick Start

### 1. First Launch

- App opens automatically after installation
- Grant file access permissions if prompted
- Settings will be initialized to defaults

### 2. Test Video Processing

**Prerequisites**: Have at least one `.rsd` sonar data file

**Steps**:

1. Click "🎬 Process Video" tab
2. Click "Browse" next to "Input RSD File"
3. Select a `.rsd` file
4. Click "Browse" next to "Output Video File"
5. Choose output location and filename
6. Select parser (Rust recommended)
7. Select encoder (GStreamer recommended)
8. Click "▶️ Start Processing"
9. Wait for completion or error message

### 3. Monitor Telemetry

1. Click "📊 Dashboard" tab
2. Watch metrics update in real-time
3. Check "Errors" tab for any issues
4. Note parser/encoder distribution

### 4. Adjust Settings

1. Click "⚙️ Settings" tab
2. Try different settings combinations:
   - Change parser (test both Rust and Python)
   - Change encoder (test both options)
   - Adjust video FPS and resolution
   - Toggle hardware acceleration
3. Click "💾 Save Settings"
4. Test video processing with new settings

## Testing Scenarios

### Scenario 1: Basic Processing

**Goal**: Verify core functionality works

```
1. Process 1-2 small RSD files
2. Check both parsers work
3. Check both encoders work
4. Verify jobs appear in Dashboard
5. Verify no errors in Errors tab
```

### Scenario 2: Performance Testing

**Goal**: Evaluate processing speed and quality

```
1. Process same file with different settings:
   - Rust parser + GStreamer
   - Rust parser + FFmpeg
   - Python parser + GStreamer
   - Python parser + FFmpeg
2. Note completion times
3. Compare output video quality
4. Check Dashboard stats
5. Export metrics for comparison
```

### Scenario 3: Error Handling

**Goal**: Test error tracking and recovery

```
1. Try processing corrupt/invalid RSD file
2. Check Errors tab for error details
3. Check error timestamp and component
4. Try with different parser
5. Try processing again with valid file
6. Verify success is recorded
```

### Scenario 4: Settings Persistence

**Goal**: Verify settings are saved

```
1. Change all settings
2. Click "💾 Save Settings"
3. Close application completely
4. Reopen application
5. Verify all settings are preserved
6. Change settings again
7. Process video and verify settings applied
```

### Scenario 5: Cross-Platform (if testing multiple OS)

**Goal**: Verify app works on different platforms

```
1. Test on Windows/Mac/Linux
2. Test file browser paths (different formats per OS)
3. Check database file location
4. Test telemetry export (platform differences)
5. Note any OS-specific issues
```

## Data Collection

The app automatically collects and stores:

### Errors (🚨 Errors tab)

- Timestamp
- Error type (parsing, encoding, etc.)
- Error message (what went wrong)
- Component (which part failed)
- Platform (Windows/Mac/Linux)
- Severity level

### Jobs (📊 Dashboard)

- Job duration
- Records processed
- Parser used
- Encoder used
- Success/failure status
- Error message (if failed)

### Metrics (📊 Dashboard)

- Total jobs completed
- Success rate
- Total records processed
- Parser distribution
- Encoder distribution

## Exporting Telemetry

To collect your beta testing data:

1. Click "⚙️ Settings" tab
2. Scroll to bottom → "About This Beta"
3. Click "📤 Export Telemetry" button
4. Choose save location
5. File saved as `sonarsniffer_telemetry_TIMESTAMP.json`
6. Share with development team

**Include with feedback**:

- Telemetry export file
- Any crash logs (see troubleshooting)
- Screenshots of any issues
- Description of what you were testing

## Feedback Checklist

After testing, please provide feedback on:

### Functionality

- [ ] Video processing works correctly
- [ ] All parsers function
- [ ] All encoders function
- [ ] Settings are saved
- [ ] Telemetry is recorded
- [ ] Dashboard updates in real-time
- [ ] Error handling works properly

### Performance

- [ ] App launches quickly
- [ ] Video processing is reasonably fast
- [ ] No significant memory issues
- [ ] UI is responsive during processing
- [ ] Database operations are quick

### Usability

- [ ] UI is intuitive
- [ ] File browser works well
- [ ] Settings are clear
- [ ] Error messages are helpful
- [ ] Navigation is smooth

### Stability

- [ ] No crashes during normal use
- [ ] No crashes during error scenarios
- [ ] Settings persist correctly
- [ ] Database operations stable

### Cross-Platform (if applicable)

- [ ] Windows-specific issues
- [ ] macOS-specific issues
- [ ] Linux-specific issues
- [ ] File path handling per platform

## Troubleshooting

### App Won't Start

```
1. Try restarting your computer
2. Uninstall and reinstall
3. Check disk space
4. Check system requirements
5. Look for crash logs (see below)
```

### Processing Hangs

```
1. Wait 2-3 minutes (might be processing)
2. If no progress, close app
3. Try with smaller RSD file
4. Try different parser/encoder
5. Export logs and send to team
```

### File Browser Doesn't Work

```
1. Verify RSD file exists and readable
2. Try different file location
3. Check file permissions
4. Try with absolute path if relative fails
```

### Settings Not Saving

```
1. Verify app data directory exists
2. Check file permissions
3. Try different settings values
4. Restart and check if changes persisted
```

### Database Errors

```
1. Close all app instances
2. Delete sonarsniffer.db file
3. Restart app (new database created)
4. Try processing again
```

## Accessing Logs

### Windows

```
%APPDATA%\SonarSniffer\logs\
OR
C:\Users\YourUsername\AppData\Roaming\SonarSniffer\
```

### macOS

```
~/Library/Application Support/com.SonarSniffer/logs/
```

### Linux

```
~/.config/SonarSniffer/logs/
OR
~/.local/share/SonarSniffer/
```

**Note**: `stdout.log` contains application output and errors

## System Information

Please include when reporting issues:

### Windows

```
Settings → System → About
- Windows version
- System type (x86_64)
- Processor
- RAM
```

### macOS

```
Apple Menu → About This Mac
- macOS version
- Processor (Intel/Apple Silicon)
- RAM
```

### Linux

```bash
uname -a
cat /proc/meminfo
```

## Sending Feedback

**What to include**:

1. Description of issue/observation
2. Steps to reproduce
3. Expected vs. actual behavior
4. Screenshots (if applicable)
5. Telemetry export file
6. System information
7. Log files (if crash occurred)

**Send to**: `[beta-feedback@sonarsniffer.dev]` or upload to feedback portal

## Known Issues

*(Will be updated as issues are discovered)*

- [ ] Issue #1: ...
- [ ] Issue #2: ...

## Testing Timeline

**Phase 1** (Week 1): Basic functionality testing  
**Phase 2** (Week 2): Performance and stability  
**Phase 3** (Week 3): Cross-platform testing  
**Phase 4** (Week 4): Bug fixes and refinements  

## FAQ

**Q: Is my data safe?**  
A: All data is stored locally. Nothing is sent to external servers during beta.

**Q: Can I use this for production?**  
A: This is beta software. Use at your own risk. Backups recommended.

**Q: How do I uninstall?**  
A: Windows: Settings → Apps → Apps & features → SonarSniffer → Uninstall  
   macOS: Drag app to Trash from Applications  
   Linux: Delete AppImage file

**Q: What happens to my feedback?**  
A: All feedback is reviewed and used to improve the application.

**Q: Can I disable telemetry?**  
A: Yes, in Settings → uncheck "Enable Telemetry Reporting"

## Thank You

Your beta testing feedback is invaluable for making SonarSniffer better!

If you have any questions, don't hesitate to reach out.

Happy testing! 🚀
