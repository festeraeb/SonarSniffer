# Telemetry Data Schema

This document describes the telemetry data collected by SonarSniffer during beta testing.

## Privacy & Data

✅ **All data is stored locally** on your computer  
✅ **No data sent to external servers** during testing  
✅ **Only sent when you export** for feedback  
✅ **You control all data** - can disable telemetry in Settings  

---

## Collected Data Structure

### 1. Error Reports

**Stored**: `sonarsniffer.db` → error_reports table

**Fields**:

```json
{
  "error_id": "uuid",           // Unique error identifier
  "timestamp": "ISO 8601",      // When error occurred
  "error_type": "string",       // Type: parsing_error, encoding_error, etc.
  "error_message": "string",    // Detailed error message
  "component": "string",        // Which part failed (parser, encoder, db, etc.)
  "platform": "string",         // OS: Windows, macOS, Linux
  "severity": "string",         // Level: critical, warning, info
  "stack_trace": "string",      // Code context (optional)
  "context": "json"             // Extra data: file size, duration, etc.
}
```

**Example**:

```json
{
  "error_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T14:30:45.123Z",
  "error_type": "parsing_error",
  "error_message": "Invalid RSD format: missing required header",
  "component": "rust_parser",
  "platform": "Windows",
  "severity": "critical",
  "context": {
    "input_file": "test.rsd",
    "file_size_mb": 125.5,
    "parser_version": "1.0.0"
  }
}
```

---

### 2. Job Metrics

**Stored**: `sonarsniffer.db` → job_metrics table

**Fields**:

```json
{
  "job_id": "uuid",              // Unique job identifier
  "timestamp": "ISO 8601",        // When job started
  "input_file": "string",         // Input RSD filename
  "input_size_mb": "number",      // Input file size
  "output_file": "string",        // Output video filename
  "output_size_mb": "number",     // Output file size
  "parser": "string",             // Parser used: rust, python
  "encoder": "string",            // Encoder used: gstreamer, ffmpeg
  "duration_seconds": "number",   // Processing time
  "records_processed": "number",  // Count of data records
  "success": "boolean",           // Completed successfully
  "error_id": "uuid or null",     // Reference to error if failed
  "platform": "string",           // OS: Windows, macOS, Linux
  "settings": "json"              // Settings used for job
}
```

**Example**:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T14:35:00.000Z",
  "input_file": "sonar_data_001.rsd",
  "input_size_mb": 245.8,
  "output_file": "sonar_video_001.mp4",
  "output_size_mb": 1205.3,
  "parser": "rust",
  "encoder": "gstreamer",
  "duration_seconds": 125.4,
  "records_processed": 48000,
  "success": true,
  "platform": "Windows",
  "settings": {
    "fps": 30,
    "resolution_height": 1080,
    "quality": "high"
  }
}
```

---

### 3. Benchmark Records

**Stored**: `sonarsniffer.db` → benchmarks table

**Fields**:

```json
{
  "benchmark_id": "uuid",        // Unique benchmark identifier
  "timestamp": "ISO 8601",        // When benchmark ran
  "test_name": "string",          // Benchmark type
  "component": "string",          // Component tested
  "duration_ms": "number",        // Execution time (milliseconds)
  "memory_mb": "number",          // Peak memory used
  "cpu_percent": "number",        // Average CPU usage
  "result": "string",             // pass, fail, timeout
  "platform": "string",           // OS: Windows, macOS, Linux
  "metadata": "json"              // Additional context
}
```

**Example**:

```json
{
  "benchmark_id": "550e8400-e29b-41d4-a716-446655440002",
  "timestamp": "2024-01-15T14:40:00.000Z",
  "test_name": "parse_rsd",
  "component": "rust_parser",
  "duration_ms": 2450,
  "memory_mb": 185.3,
  "cpu_percent": 75.2,
  "result": "pass",
  "platform": "Windows",
  "metadata": {
    "file_size_mb": 245.8,
    "record_count": 48000,
    "parser_version": "1.0.0"
  }
}
```

---

### 4. Settings Snapshots

**Stored**: `sonarsniffer.db` (cached in settings table at export time)

**Fields**:

```json
{
  "setting_key": "string",       // Setting name
  "setting_value": "any",        // Current value
  "updated_at": "ISO 8601",      // Last modification time
  "value_type": "string"         // Type: string, number, boolean
}
```

**Current Settings Tracked**:

- `default_parser`: rust | python
- `default_encoder`: gstreamer | ffmpeg
- `default_fps`: 24-120
- `default_resolution_height`: 480-4320
- `default_quality`: low | medium | high | ultra
- `telemetry_enabled`: true | false
- `hardware_acceleration`: true | false

---

### 5. System Information

**Captured during export**:

```json
{
  "app_version": "0.1.0",
  "app_platform": "Windows|macOS|Linux",
  "app_arch": "x86_64|aarch64",
  "os_version": "e.g., Windows 11 Pro Build 22621",
  "hardware": {
    "cpu_cores": "number",
    "memory_gb": "number",
    "free_space_gb": "number"
  },
  "collection_timestamp": "ISO 8601"
}
```

---

## Telemetry Export Format

When exported, data is saved as:
**File**: `sonarsniffer_telemetry_2024-01-15_143045.json`

**Structure**:

```json
{
  "metadata": {
    "export_timestamp": "2024-01-15T14:30:45.123Z",
    "app_version": "0.1.0",
    "platform": "Windows",
    "tester_note": "Optional note from user"
  },
  "system_info": {
    "os_version": "Windows 11 Pro",
    "cpu_cores": 8,
    "memory_gb": 16,
    "free_space_gb": 256
  },
  "errors": [
    {error_record_1},
    {error_record_2}
  ],
  "jobs": [
    {job_record_1},
    {job_record_2}
  ],
  "benchmarks": [
    {benchmark_record_1}
  ],
  "settings": {
    "default_parser": "rust",
    "default_encoder": "gstreamer",
    ...
  },
  "summary": {
    "total_errors": 2,
    "total_jobs": 5,
    "successful_jobs": 4,
    "failed_jobs": 1,
    "total_records_processed": 240000,
    "average_job_duration_seconds": 98.5,
    "uptime_hours": 2.5
  }
}
```

---

## Data Storage Locations

### Windows

```
C:\Users\YourUsername\AppData\Roaming\SonarSniffer\sonarsniffer.db
C:\Users\YourUsername\AppData\Roaming\SonarSniffer\logs\
```

### macOS

```
~/Library/Application Support/com.SonarSniffer/sonarsniffer.db
~/Library/Application Support/com.SonarSniffer/logs/
```

### Linux

```
~/.local/share/SonarSniffer/sonarsniffer.db
~/.local/share/SonarSniffer/logs/
```

---

## Disabling Telemetry

To disable telemetry collection:

1. Open app
2. Click **"⚙️ Settings"**
3. Uncheck **"Enable Telemetry Reporting"**
4. Click **"💾 Save Settings"**

**What happens**:

- ✅ Errors still tracked (you may want to see them)
- ✅ Job metrics still recorded (for debugging)
- ✅ Settings still saved (for your preferences)
- ❌ Telemetry NOT included in exports

---

## Data Retention

**Local Storage**:

- Errors: Kept for 30 days then auto-deleted
- Jobs: Kept for 90 days then auto-deleted
- Benchmarks: Kept for 14 days then auto-deleted
- Settings: Kept indefinitely until changed

**Manual Deletion**:

- Delete `sonarsniffer.db` to start fresh
- New database auto-created on next launch

---

## Exporting & Sharing

**What's safe to share**:

- ✅ Telemetry export file (no personal data)
- ✅ Aggregated statistics
- ✅ Error messages & stack traces

**What's NOT in exports**:

- ❌ Filenames of your RSD files (sanitized)
- ❌ Full file paths (just relative paths)
- ❌ Any user document content
- ❌ Personal settings (unless you choose to share)

**Before sharing**:

1. Review exported JSON
2. Remove any sensitive data
3. Add testing context/notes

---

## Analysis & Privacy

**Data is used for**:

- 📊 Identifying bugs and crashes
- 📈 Performance tuning
- 🔍 Compatibility across platforms
- 🎯 Feature prioritization
- 📋 Beta testing metrics

**Data is NOT used for**:

- ❌ Commercial purposes
- ❌ Selling to third parties
- ❌ Identifying individuals
- ❌ Tracking behavior
- ❌ Account creation/linking

---

## Questions?

See BETA_TESTING_GUIDE.md for more details on telemetry usage in testing.

**Need help?** Email: `beta-support@sonarsniffer.dev`
