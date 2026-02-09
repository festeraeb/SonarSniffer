# Advanced Beta Testing Scenarios

## Overview

This document provides advanced testing scenarios for comprehensive beta validation. These go beyond basic functionality testing to explore edge cases, error conditions, and complex workflows.

---

## Scenario 1: Edge Case - Empty RSD File

**Description**: Test app behavior with zero-length or corrupted RSD file

**Setup**:
```
1. Create empty file: empty.rsd (0 bytes)
2. Create corrupted file: corrupt.rsd (random binary data)
```

**Test Steps**:

1. Open "Process Video" tab
2. Select empty.rsd as input
3. Choose output location
4. Click "Start Processing"

**Expected Outcome**:
- [ ] Error caught and displayed
- [ ] Error message is descriptive
- [ ] App doesn't crash
- [ ] Can process other files afterwards

**Actual Outcome**: ___________________________________________________

**Error Details**:
```
Error Message:


Stack Trace:

```

**Severity**: Critical / High / Medium / Low

---

## Scenario 2: Edge Case - Extremely Large File

**Description**: Test processing of very large RSD file (> 1 GB)

**Setup**:
```
Create or obtain 1+ GB RSD file
Ensure 5+ GB free disk space
```

**Test Steps**:

1. Start "Process Video" with large file
2. Monitor memory every 30 seconds
3. Check UI responsiveness during processing
4. Let process complete or run for 30 minutes

**Checkpoints**:

| Time | Memory | CPU | Status |
|------|--------|-----|--------|
| Start | ____ MB | ___% | |
| 5 min | ____ MB | ___% | |
| 10 min | ____ MB | ___% | |
| 15 min | ____ MB | ___% | |
| 20 min | ____ MB | ___% | |
| 30 min | ____ MB | ___% | |

**Issues Found**:
- [ ] Memory spike > 1 GB
- [ ] UI freeze during processing
- [ ] Disk space exhausted
- [ ] Other: _________________

---

## Scenario 3: Edge Case - Rapid File Switches

**Description**: Test rapid switching between different files

**Setup**:
```
Prepare 3-5 test RSD files
```

**Test Steps**:

1. Click "Process Video" tab
2. Select File 1 via Browse
3. Immediately select File 2 via Browse (before File 1 loads)
4. Repeat pattern 5 times
5. Check app stability

**Results**:
- [ ] No freezing or errors
- [ ] Correct file selected each time
- [ ] Memory properly managed
- [ ] App crashes: Yes / No

**Notes**: ________________________________________________________________

---

## Scenario 4: Stress Test - Multiple Parser/Encoder Combinations

**Description**: Test all parser/encoder combinations systematically

**Setup**:

```
Test File: medium 100-200 MB RSD
Run 4 combinations:
1. Rust + GStreamer
2. Rust + FFmpeg
3. Python + GStreamer
4. Python + FFmpeg
```

**Execution**:

| # | Parser | Encoder | Duration | Output Size | Status |
|---|--------|---------|----------|-------------|--------|
| 1 | Rust | GStreamer | ____ sec | ____ MB | Pass/Fail |
| 2 | Rust | FFmpeg | ____ sec | ____ MB | Pass/Fail |
| 3 | Python | GStreamer | ____ sec | ____ MB | Pass/Fail |
| 4 | Python | FFmpeg | ____ sec | ____ MB | Pass/Fail |

**Comparative Analysis**:

- Fastest combination: ________________ (____ sec)
- Smallest output: ________________ (____ MB)
- Most stable: ________________
- Recommended default: ________________

---

## Scenario 5: Settings Mutation Test

**Description**: Verify settings changes applied immediately and persisted

**Setup**:
```
Start with default settings
Process one file to baseline
```

**Test Steps**:

1. Open Settings tab
2. Change each setting one-by-one
3. After each change, verify it's applied correctly

**Settings Changes**:

| Setting | Old Value | New Value | Applied? | Persisted? |
|---------|-----------|-----------|----------|------------|
| Parser | Rust | Python | [ ] | [ ] |
| Encoder | GStreamer | FFmpeg | [ ] | [ ] |
| FPS | 30 | 60 | [ ] | [ ] |
| Resolution | 1080 | 720 | [ ] | [ ] |
| Quality | Medium | High | [ ] | [ ] |
| Telemetry | Enabled | Disabled | [ ] | [ ] |

**Verification**:
1. Process a file after each setting change
2. Close app and reopen
3. Check Settings tab shows correct values

**Issues**: _______________________________________________________________

---

## Scenario 6: Error Recovery Chain

**Description**: Test error handling and recovery across multiple attempts

**Part A: Recoverable Error**

```
Attempt 1: Process non-existent file
Attempt 2: Process valid file → should work
```

**Result**:
- First attempt error message: ___________________________________
- App still responsive: Yes / No
- Second attempt succeeds: Yes / No

**Part B: Permission Error**

```
(If possible on your OS)
Change file permissions to read-only
Try to process file
```

**Result**:
- Error captured: Yes / No
- Error message helpful: Yes / No
- Can retry after fixing: Yes / No

**Part C: Disk Full Scenario**

```
(Simulate if possible)
Process file to near-full disk
Monitor what happens
```

**Result**:
- Error detected: Yes / No
- Graceful cleanup: Yes / No
- Helpful message: Yes / No (_____________)

---

## Scenario 7: Telemetry Validation

**Description**: Verify telemetry data is accurate and complete

**Setup**:
```
Process 3 test files with different settings each
Track metrics manually
Compare with exported telemetry
```

**File 1 Metrics**:

**Manual Measurement**:
- Input file: ________________________
- Duration (measured by stopwatch): ____ sec
- Parser used: [ ] Rust [ ] Python
- Encoder used: [ ] GStreamer [ ] FFmpeg
- Approximate records: ~______

**Exported Telemetry** (from JSON export):
```json
{
  "job_id": "...",
  "duration_seconds": _____,
  "records_processed": _____,
  "parser": "...",
  "encoder": "...",
  "success": true/false,
  "error_message": "..."
}
```

**Accuracy Check**:
- Duration matches: ±____% variance acceptable?
- Records count reasonable: Yes / No
- Parser/encoder correct: Yes / No
- Error logged if occurred: Yes / No

**Repeat for Files 2 & 3**: [Follow same steps]

---

## Scenario 8: Dashboard Real-Time Updates

**Description**: Verify dashboard auto-refresh accuracy

**Setup**:
```
Dashboard tab visible
Start processing a file
Watch dashboard in real-time
```

**Observation Points**:

| Time Point | Expected | Observed | Match? |
|-----------|----------|----------|--------|
| Before start | No new job | _________ | ✓/✗ |
| During process | Job counted | _________ | ✓/✗ |
| After complete | Success counted | _________ | ✓/✗ |
| Auto-refresh | 5 sec interval | _________ | ✓/✗ |

**Metric Accuracy**:

- Total jobs increases: Yes / No
- Records count increases: Yes / No
- Parsers distribution updated: Yes / No
- Health status reasonable: Yes / No

---

## Scenario 9: Error Filter Testing

**Description**: Verify error log filtering works correctly

**Setup**:
```
Process files to generate 3+ errors (if possible)
Include different error types/severities
```

**Test Steps**:

1. Open Errors tab
2. Click "All" filter
3. Verify all errors shown
4. Click each severity filter in turn

**Filter Results**:

| Filter | Expected Count | Shown | Match? |
|--------|----------------|-------|--------|
| All | _____ | _____ | ✓/✗ |
| Critical | _____ | _____ | ✓/✗ |
| Warning | _____ | _____ | ✓/✗ |
| Info | _____ | _____ | ✓/✗ |

**Sorting**:
- [ ] Errors sorted by most recent first
- [ ] Timestamps visible and accurate
- [ ] Error details partially visible

---

## Scenario 10: Settings Export/Import

**Description**: Test telemetry export completeness and format

**Setup**:
```
Process several files
Create some errors
Change settings
```

**Export Steps**:

1. Open Settings tab
2. Click "Export Telemetry"
3. Save file to known location
4. Open exported file with text editor

**Validation**:

**JSON Structure**:
```
✓ metadata section (timestamp, app version)
✓ system_info section (OS, CPU, memory)
✓ settings section (all config values)
✓ jobs array (all processed files)
✓ errors array (all errors)
✓ summary section (aggregate stats)
```

**Data Completeness**:

| Field | Present? | Accurate? |
|-------|----------|-----------|
| Export timestamp | [ ] | [ ] |
| App version | [ ] | [ ] |
| Platform info | [ ] | [ ] |
| All settings | [ ] | [ ] |
| All jobs | [ ] | [ ] |
| All errors | [ ] | [ ] |
| Statistics | [ ] | [ ] |

**File Size**: _____ KB (reasonable: [ ] Yes [ ] No)

**Notes**: ________________________________________________________________

---

## Scenario 11: Cross-Tab Navigation Stress

**Description**: Rapid navigation between tabs while processing

**Setup**:
```
Start processing file
Keep app visible
```

**Test Steps**:

1. Click tabs rapidly: Dashboard → Process → Errors → Settings → Dashboard
2. Repeat 20 times over ~1 minute
3. Observe for any lag, errors, or crashes

**Results**:

- Total cycles completed: _____
- Freezes encountered: [ ] Yes [ ] No
- How many: _______
- Duration of longest freeze: _____ sec
- App crashed: [ ] Yes [ ] No

**Responsiveness Rating** (circle):

⭐️ 1 Sluggish  
⭐️ 2 Slow  
⭐️ 3 Acceptable  
⭐️ 4 Good  
⭐️ 5 Excellent  

---

## Scenario 12: File Browser Edge Cases

**Description**: Test file dialog behavior

**Test Steps**:

1. Click "Browse" next to Input File
2. Try to navigate to network location (if available)
3. Try special folder (Desktop, Documents)
4. Try navigating to files with special characters
5. Try very long file paths (if possible)

**Results**:

| Action | Works? | Issue |
|--------|--------|-------|
| Network location | [ ] | _________ |
| Special folders | [ ] | _________ |
| Special characters | [ ] | _________ |
| Long paths | [ ] | _________ |
| Cancel operation | [ ] | _________ |

---

## Summary of Advanced Testing

**Scenarios Completed**: _____ / 12

**Critical Issues Found**: _______

**High Priority Issues**: _______

**Medium Priority Issues**: _______

**Overall Stability Rating**:

⭐️ 1 Unstable  
⭐️ 2 Unreliable  
⭐️ 3 Fair  
⭐️ 4 Good  
⭐️ 5 Production Ready  

**Tester Notes**:

```




```

**Recommendation**: [ ] Release [ ] Fix issues then release [ ] Major rework needed

**Submitted by**: ________________________  
**Date**: ____________________

Submit this form along with:
1. Telemetry export file
2. Screenshots of any issues
3. Any crash logs or error details
4. Video recording if applicable
