# Performance & Load Testing Guide

## Overview

This guide provides comprehensive performance and load testing procedures for the SonarSniffer beta application. Use these tests to measure app responsiveness, resource usage, and reliability under various conditions.

---

## Test Environment Setup

### Prerequisites

```
✅ SonarSniffer installed and running
✅ System Monitor or Task Manager open
✅ Test RSD file(s) available (various sizes)
✅ Output directory with 10+ GB free space
✅ Timing tool (stopwatch or built-in timer)
```

### Baseline Measurements

**Before Starting Tests**:

1. Close unnecessary applications
2. Check available system resources:
   - Free RAM: ________ MB
   - Free Disk: ________ GB
   - CPU utilization: ________ %
   - Background processes: ________

3. Record idle app metrics:
   - Memory (idle): ________ MB
   - CPU (idle): ________ %
   - Disk reads/sec (idle): ________

---

## Test 1: Startup Performance

**Objective**: Measure app launch time and initial UI render

**Procedure**:

1. Close application completely
2. Start stopwatch
3. Launch SonarSniffer from Start Menu/Applications
4. Stop timer when UI is fully responsive (Dashboard visible)

**Measurements**:

| Attempt | Time (sec) | Notes |
|---------|-----------|-------|
| 1 | _____ | |
| 2 | _____ | |
| 3 | _____ | (avg ___) |

**Pass Criteria**: < 5 seconds average

**Memory After Startup**:
- Idle memory: ________ MB
- Peak memory: ________ MB

---

## Test 2: UI Responsiveness

**Objective**: Verify UI remains responsive during operations

**Procedure**:

1. Click each tab rapidly (Dashboard → Process → Errors → Settings → Dashboard)
2. Note any lag or freezing
3. Repeat tab navigation 10 times
4. Time total duration

**Results**:

| Iteration | Tab Switch Time | Lag Detected? |
|-----------|-----------------|---------------|
| 1-3 | _____ sec | Yes / No |
| 4-6 | _____ sec | Yes / No |
| 7-10 | _____ sec | Yes / No |

**Notes**: ___________________________________________________________

**Pass Criteria**: No lag; tab switches < 500ms

---

## Test 3: File Processing Performance

### Test 3A: Small File (< 50 MB)

**File**: ________________  
**Size**: _____ MB  
**Parser**: [ ] Rust [ ] Python  
**Encoder**: [ ] GStreamer [ ] FFmpeg

**Timeline**:

```
Start Time: _______
Video Processing Complete: _______
Dashboard Updated: _______
Total Duration: _____ seconds
```

**Resource Monitoring**:

| Phase | Memory | CPU | Disk I/O |
|-------|--------|-----|----------|
| Processing | ____ MB | ___% | ____ MB/s |
| Peak | ____ MB | ___% | ____ MB/s |
| Post-Process | ____ MB | ___% | 0 MB/s |

**Output Metrics**:

- Records Processed: _______
- Output File Size: _______ MB
- Processing Rate: _______ records/sec
- Compression Ratio: _______

### Test 3B: Medium File (50-200 MB)

**File**: ________________  
**Size**: _____ MB  
**Parser**: [ ] Rust [ ] Python  
**Encoder**: [ ] GStreamer [ ] FFmpeg

**Timeline**:
```
Start Time: _______
Video Processing Complete: _______
Total Duration: _____ seconds
```

**Resource Monitoring**:

| Phase | Memory | CPU | Disk I/O |
|-------|--------|-----|----------|
| Processing | ____ MB | ___% | ____ MB/s |
| Peak | ____ MB | ___% | ____ MB/s |

### Test 3C: Large File (200+ MB)

**File**: ________________  
**Size**: _____ MB  
**Parser**: [ ] Rust [ ] Python  
**Encoder**: [ ] GStreamer [ ] FFmpeg

*Note: If processing > 30 minutes, may stop test after 15 min recording stats*

**Timeline**:
```
Start Time: _______
Processing at 5 min: ___________
Processing at 10 min: __________
Peak Memory Reached: _____ MB at ___ min
Estimated Total Time: _____ min
```

---

## Test 4: Concurrent Operations

**Objective**: Test if app can handle fast operations in succession

**Procedure**:

1. Process file 1 (select, start, observe)
2. While processing, change settings (without stopping)
3. Open Errors tab and monitor
4. Repeat tabs
5. Verify no freezes or crashes

**Results**:

- [ ] Settings changes while processing: Success / Glitch / Frozen
- [ ] Tab navigation: Responsive / Sluggish / Frozen
- [ ] Errors visible and updating: Yes / No
- [ ] App crash: No / Yes (at _____ min)

**Pass Criteria**: All responsive, no crashes

---

## Test 5: Memory Stability

**Objective**: Ensure memory doesn't grow unboundedly

**Procedure**:

1. Record initial memory usage
2. Process 5 files in sequence (don't close app)
3. Record memory after each file
4. Check for memory leak pattern

**Memory Timeline**:

```
Initial: _______ MB
After File 1: _______ MB (Δ ____ MB)
After File 2: _______ MB (Δ ____ MB)
After File 3: _______ MB (Δ ____ MB)
After File 4: _______ MB (Δ ____ MB)
After File 5: _______ MB (Δ ____ MB)

Leak Suspected: [ ] Yes [ ] No
Growth Rate: _______ MB/file
```

**Pass Criteria**: < 20 MB growth per file; returns to baseline when idle

---

## Test 6: Database Performance

**Objective**: Verify database operations don't slow down app

**Procedure**:

1. Process files to generate 10-20 job records
2. Open Settings → "Export Telemetry"
3. Time the export process
4. Check file size

**Results**:

- Total Job Records: _______
- Total Error Records: _______
- Export Time: _______ seconds
- Export File Size: _______ KB
- Dashboard Load Time: _______ ms

**Pass Criteria**: Export < 5 seconds, Dashboard < 1 second load

---

## Test 7: Error Handling Under Load

**Objective**: Verify error handling doesn't crash app

**Procedure**:

1. Attempt to process non-existent file (catch error)
2. Process file to same location twice (overwrite scenario)
3. Process file with invalid permissions (if possible)
4. Verify all errors logged and displayed

**Error Recovery**:

| Scenario | Error Captured? | App Stable? | Recoverable? |
|----------|-----------------|-------------|--------------|
| Missing file | Yes / No | Yes / No | Yes / No |
| Overwrite | Yes / No | Yes / No | Yes / No |
| Permission denied | Yes / No | Yes / No | Yes / No |

**Pass Criteria**: All errors handled gracefully, app remains stable

---

## Test 8: Settings Persistence Check

**Objective**: Verify settings survive app restart under load

**Procedure**:

1. Process a file (settings active)
2. Change process settings (parser, encoder, quality)
3. Close and reopen app mid-operation
4. Verify settings persisted

**Results**:

- [ ] Settings saved before close
- [ ] Settings restored after reopen
- [ ] Settings applied to new jobs: Yes / No

---

## Test 9: Cross-Parser Comparison

**Objective**: Compare Rust vs Python parser performance

**Same File Processed With**:

### Rust Parser
- Duration: _____ sec
- Memory Peak: _____ MB
- CPU Peak: _____ %
- Output Size: _____ MB

### Python Parser
- Duration: _____ sec
- Memory Peak: _____ MB
- CPU Peak: _____ %
- Output Size: _____ MB

**Comparison**:

- Rust is ___% faster
- Rust uses ___% less memory
- Output quality similar: Yes / No

---

## Test 10: Long-Duration Stability

**Objective**: Verify app can run for extended period

**Procedure** (Optional, for dedicated testing):

1. Process multiple files continuously
2. Run for minimum 2 hours
3. Monitor for crashes, memory issues, or UI degradation
4. Check telemetry export at end

**Timeline**:

```
Start Time: _______
Status at 30 min: ________________________
Status at 60 min: ________________________
Status at 90 min: ________________________
End Time: _______
Total Duration: _____ hours

Crash Count: _______
Memory Growth: _____ MB over duration
Performance Degradation: None / Minor / Significant
```

---

## Performance Benchmarks

### Expected Performance (Target)

| Metric | Target | Actual |
|--------|--------|--------|
| Startup Time | < 5 sec | _____ |
| Idle Memory | < 150 MB | _____ |
| Tab Switch | < 500 ms | _____ |
| 100 MB File Process | < 5 min | _____ |
| Export Telemetry | < 5 sec | _____ |
| Memory Leak (per file) | < 20 MB | _____ |
| UI Responsiveness | Smooth | _____ |

### Collected Metrics

| Test | Value | Pass? |
|------|-------|-------|
| Startup | _____ sec | ✓/✗ |
| Idle Memory | _____ MB | ✓/✗ |
| File Processing | _____ sec/MB | ✓/✗ |
| Export Time | _____ sec | ✓/✗ |
| Memory Stability | _____ MB growth | ✓/✗ |
| Error Handling | _____ / _____ tests | ✓/✗ |
| UI Responsiveness | _____ | ✓/✗ |

---

## Issues Found

### Issue #1
- **Severity**: Critical / High / Medium / Low
- **Observed**: _______________________________________________________
- **Steps to Reproduce**: ______________________________________________
- **Impact**: ___________________________________________________________

### Issue #2
- **Severity**: Critical / High / Medium / Low
- **Observed**: _______________________________________________________
- **Steps to Reproduce**: ______________________________________________
- **Impact**: ___________________________________________________________

### Issue #3
- **Severity**: Critical / High / Medium / Low
- **Observed**: _______________________________________________________
- **Steps to Reproduce**: ______________________________________________
- **Impact**: ___________________________________________________________

---

## Performance Recommendations

**What Went Well**:
```




```

**Areas for Improvement**:
```




```

**Specific Optimizations Suggested**:
```
1.


2.


3.

```

---

## Platform-Specific Notes

**Windows**:
- CPU Usage Pattern: ____________________________________
- Memory Behavior: _____________________________________
- Disk I/O (SSD vs HDD if tested): _________________________

**macOS** (if tested):
- CPU Usage Pattern: ____________________________________
- Memory Behavior: _____________________________________
- Notes: _______________________________________________

**Linux** (if tested):
- CPU Usage Pattern: ____________________________________
- Memory Behavior: _____________________________________
- Notes: _______________________________________________

---

## Summary & Recommendations

**Overall Performance Rating** (circle one):

⭐️ 1 (Poor)  
⭐️ 2 (Below Average)  
⭐️ 3 (Average)  
⭐️ 4 (Good)  
⭐️ 5 (Excellent)

**Production Ready**: [ ] Yes [ ] With minor fixes [ ] Needs optimization

**Reviewer**: _____________________ **Date**: _________________

**Next Steps**: ___________________________________________________________

---

## Tools Used

**System Monitoring**:
- [ ] Windows Task Manager
- [ ] macOS Activity Monitor
- [ ] Linux top/htop
- [ ] Advanced tool: ______________________

**Test Files**:
- [ ] Created custom files
- [ ] Used provided test data
- [ ] Real world RSD data
- [ ] File sources: __________________________

**Testing Duration**: _____ hours  
**Tester Experience**: Beginner / Intermediate / Advanced  
**First Time Testing**: Yes / No

---

## Appendix: Resource Monitoring Tips

### Windows Task Manager

```
Ctrl+Shift+Esc → Performance Tab
- Memory (Private Working Set)
- CPU (%)
- Disk
- GPU (if available)

Details Tab → Find sonarsniffer.exe
- Memory, CPU columns
- Right-click → Priority
```

### macOS Activity Monitor

```
Cmd+Space → Activity Monitor
- Memory: Real Memory, Virtual Memory
- CPU: % CPU
- Disk: Reads/Writes
- Energy Impact
```

### Linux (htop)

```
top -p $(pgrep -f "sonarsniffer|tauri")
F3 → Sort by Memory
F4 → Sort by CPU
```

---

## Conclusion

Thank you for performing these performance tests. Your data will help us optimize SonarSniffer for production release.

Please export telemetry and submit this form along with any performance data collected.
