# SonarSniffer Beta Feedback Form

**Submission Date**: [YYYY-MM-DD]  
**Tester Name**: [Your Name]  
**Test Platform**: [ ] Windows [ ] macOS [ ] Linux  
**Platform Version**: [e.g., Windows 11 Pro]

---

## 1. Testing Summary

**Testing Duration**: _____ minutes/hours  
**Number of RSD Files Processed**: _____  
**Issues Encountered**: [ ] None [ ] Minor [ ] Major  

---

## 2. Functionality Testing

### Video Processing

**Rust Parser**

- [ ] Works correctly
- [ ] Works with issues: ________________________
- [ ] Crashes: ________________________
- [ ] Performance (circle): ⭐️ 1 ⭐️ 2 ⭐️ 3 ⭐️ 4 ⭐️ 5

**Python Parser**

- [ ] Works correctly
- [ ] Works with issues: ________________________
- [ ] Crashes: ________________________
- [ ] Performance (circle): ⭐️ 1 ⭐️ 2 ⭐️ 3 ⭐️ 4 ⭐️ 5

**GStreamer Encoder**

- [ ] Works correctly
- [ ] Works with issues: ________________________
- [ ] Crashes: ________________________
- [ ] Output Quality (circle): ⭐️ 1 ⭐️ 2 ⭐️ 3 ⭐️ 4 ⭐️ 5

**FFmpeg Encoder**

- [ ] Works correctly
- [ ] Works with issues: ________________________
- [ ] Crashes: ________________________
- [ ] Output Quality (circle): ⭐️ 1 ⭐️ 2 ⭐️ 3 ⭐️ 4 ⭐️ 5

### Dashboard

- [ ] Metrics display correctly
- [ ] Metrics update in real-time
- [ ] Issues: ________________________

### Error Tab

- [ ] Errors display correctly
- [ ] Error details are helpful
- [ ] Filter works
- [ ] Issues: ________________________

### Settings Tab

- [ ] All settings save correctly
- [ ] Settings persist after restart
- [ ] Default values are sensible
- [ ] Issues: ________________________

---

## 3. Performance Evaluation

### Processing Speed

**Test File 1**:

- Size: _____ MB
- Parser: [ ] Rust [ ] Python
- Encoder: [ ] GStreamer [ ] FFmpeg
- Time: _____ seconds
- Input FPS: _____ Output FPS: _____

**Test File 2**:

- Size: _____ MB
- Parser: [ ] Rust [ ] Python
- Encoder: [ ] GStreamer [ ] FFmpeg
- Time: _____ seconds
- Input FPS: _____ Output FPS: _____

### Resource Usage

- Peak Memory: _____ MB
- CPU Usage: Average ____%, Peak _____%
- Disk Space Used: _____ MB
- Any throttling observed: [ ] Yes [ ] No

### Output Quality

**Subjective Rating** (circle one):
⭐️ 1 (Poor) ⭐️ 2 ⭐️ 3 ⭐️ 4 ⭐️ 5 (Excellent)

**Comments**: _______________________________________________

---

## 4. Stability & Reliability

### Crashes

Number of crashes: _____

**Crash Details** (if any):

```
What you were doing when it crashed:


Error message (if shown):


Steps to reproduce:

```

### Hangs/Freezes

Number of hangs: _____

**Details**:

```
What triggered the hang:


How long it lasted:


Recovery method:

```

### Data Integrity

- [ ] Database corrupted
- [ ] Settings lost
- [ ] Telemetry records were incomplete
- [ ] All data appeared correct

---

## 5. User Experience

### Navigation

**Ease of Use** (circle): ⭐️ 1 ⭐️ 2 ⭐️ 3 ⭐️ 4 ⭐️ 5

**Navigation Issues**:

```



```

### UI/UX

**Overall Design** (circle): ⭐️ 1 ⭐️ 2 ⭐️ 3 ⭐️ 4 ⭐️ 5

**Usability Issues**:

```
- 
- 
- 
```

**Things that work well**:

```
- 
- 
- 
```

### File Browser

- [ ] Intuitive
- [ ] Confusing
- [ ] Slow
- [ ] Issues: ________________________

### Error Messages

- [ ] Clear and helpful
- [ ] Confusing
- [ ] Missing (what error?): ________________________
- [ ] Too technical: ________________________

### Color Scheme & Theme

**Appearance Rating** (circle): ⭐️ 1 ⭐️ 2 ⭐️ 3 ⭐️ 4 ⭐️ 5

**Comments**: _______________________________________________

---

## 6. Cross-Platform Specific Issues

### Windows

- [ ] File paths work correctly
- [ ] Installer works smoothly
- [ ] App integrates with Windows well
- [ ] Issues: ________________________________________________

### macOS

- [ ] File paths work correctly
- [ ] App launches from Applications
- [ ] Permissions handled correctly
- [ ] Issues: ________________________________________________

### Linux

- [ ] AppImage launches correctly
- [ ] File permissions work
- [ ] Package manager compatible
- [ ] Issues: ________________________________________________

---

## 7. Feature Requests

**High Priority Features** (what's missing most):

```
1. 


2. 


3. 

```

**Nice-to-Have Features**:

```
1. 


2. 


3. 

```

**Feature Requests Explanation**:

```



```

---

## 8. Bug Reports

### Bug #1

**Title**: ____________________________________________________

**Severity** (circle): 🔴 Critical 🟡 High 🟡 Medium 🟢 Low

**Steps to Reproduce**:

```
1. 
2. 
3. 
```

**Expected Behavior**: ________________________________________

**Actual Behavior**: __________________________________________

**Workaround** (if found): ____________________________________

**Screenshots**: [✓ Attached / ✗ Not attached]

---

### Bug #2

**Title**: ____________________________________________________

**Severity** (circle): 🔴 Critical 🟡 High 🟡 Medium 🟢 Low

**Steps to Reproduce**:

```
1. 
2. 
3. 
```

**Expected Behavior**: ________________________________________

**Actual Behavior**: __________________________________________

**Workaround** (if found): ____________________________________

**Screenshots**: [✓ Attached / ✗ Not attached]

---

### Bug #3

**Title**: ____________________________________________________

**Severity** (circle): 🔴 Critical 🟡 High 🟡 Medium 🟢 Low

**Steps to Reproduce**:

```
1. 
2. 
3. 
```

**Expected Behavior**: ________________________________________

**Actual Behavior**: __________________________________________

**Workaround** (if found): ____________________________________

**Screenshots**: [✓ Attached / ✗ Not attached]

---

## 9. Overall Assessment

### Overall Rating

**How satisfied are you with this beta?** (circle):

⭐️ 1 (Poor)  
⭐️ 2 (Needs work)  
⭐️ 3 (Average)  
⭐️ 4 (Good)  
⭐️ 5 (Excellent)

### Would You Use This in Production?

[ ] Yes, ready now  
[ ] Yes, after fixes  
[ ] Needs more work  
[ ] No, not suitable for my use case  

**Why**: _______________________________________________________

### Recommendation

- [ ] Highly recommend for next release
- [ ] Recommend after minor fixes
- [ ] Needs significant improvement
- [ ] Not ready for release

---

## 10. System Information

### Hardware

- **Processor**: _________________________________________________
- **RAM**: ________ GB
- **Disk**: ________ GB free

### Software

- **OS**: ________________________________________________________
- **OS Version**: ________________________________________________
- **Node.js Version** (if available): ____________________________
- **Browser** (if applicable): __________________________________

### App Details

- **App Version**: 0.1.0 (Beta)
- **Installation Date**: ________________________________________
- **Uptime Since Last Restart**: ________________________________

---

## 11. Telemetry & Log Files

**Telemetry Export Attached**: [ ] Yes [ ] No

**Export File Location** (for reference):

```
[If you exported telemetry, copy the filename here]


```

**Crash Logs Attached**: [ ] Yes [ ] No

**Log File Locations** (for reference):

```
Windows: %APPDATA%\SonarSniffer\logs\
macOS: ~/Library/Application Support/com.SonarSniffer/logs/
Linux: ~/.config/SonarSniffer/logs/
```

---

## 12. Additional Comments

**General Comments** (anything else we should know):

```




```

**What Impressed You**:

```




```

**What Disappointed You**:

```




```

**Suggestions for Improvement**:

```




```

---

## 13. Submission

**Form Completion Date**: [YYYY-MM-DD]

**Action Items** (development team only):

- [ ] Bug #____: Severity ___, Priority___
- [ ] Feature Request #____
- [ ] Issue #____: Follow up needed

**Next Steps**:

- [ ] Confirm receipt
- [ ] Schedule followup with tester
- [ ] Investigate critical issues
- [ ] Plan fixes for next beta

---

**Thank you for your detailed feedback! Your input is invaluable.**

*Please submit this form along with any attached telemetry data or screenshots to: <beta-feedback@sonarsniffer.dev>*
