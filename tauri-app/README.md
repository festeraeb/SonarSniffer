# SonarSniffer Desktop - Tauri Application

Full-featured cross-platform desktop application for sonar data processing with built-in telemetry tracking and error reporting.

## Features

✅ **Cross-Platform** - Windows, macOS, Linux  
✅ **Native Desktop UI** - Built with Tauri + React  
✅ **Video Processing** - RSD parsing and encoding  
✅ **Error Tracking** - Comprehensive error reporting with SQLite database  
✅ **Telemetry** - Usage analytics for beta testing and improvements  
✅ **Settings Management** - Persist user preferences  
✅ **Real-time Dashboard** - Live metrics and statistics  
✅ **Export Capabilities** - Export telemetry data for analysis  

## System Requirements

### Windows

- Windows 10 or later (x86_64)
- Microsoft Visual C++ Runtime

### macOS

- macOS 10.13 or later
- Intel or Apple Silicon

### Linux

- GTK 3.6 or later
- WebKit 2.33 or later

## Prerequisites

### Required

- **Node.js** 16+ ([download](https://nodejs.org/))
- **Rust** 1.70+ ([install](https://rustup.rs/))

### Optional

- **GStreamer** 1.20+ (for video encoding with hardware acceleration)
- **FFmpeg** (alternative video encoder)

## Project Structure

```
sonarsniffer_desktop/
├── src/                           # React TypeScript frontend
│   ├── main.tsx                  # Entry point
│   ├── App.tsx                   # Main app component
│   ├── App.css                   # Main styles
│   ├── index.css                 # Global styles
│   └── pages/
│       ├── Dashboard.tsx         # Real-time metrics
│       ├── ProcessVideo.tsx      # Video processing UI
│       ├── Errors.tsx            # Error reporting
│       └── Settings.tsx          # User settings
├── src-tauri/                     # Rust backend
│   ├── src/
│   │   ├── main.rs              # Tauri window setup
│   │   ├── lib.rs               # Commands & state
│   │   ├── db.rs                # SQLite database
│   │   ├── telemetry.rs         # Telemetry manager
│   │   ├── video_processor.rs   # Video processing logic
│   │   └── settings.rs          # Settings management
│   ├── Cargo.toml               # Rust dependencies
│   ├── tauri.conf.json          # Tauri configuration
│   └── build.rs                 # Build script
├── package.json                  # NPM dependencies
├── vite.config.ts               # Vite configuration
├── tsconfig.json                # TypeScript config
└── README.md                     # This file
```

## Setup & Installation

### 1. Install Dependencies

```bash
# Install Node dependencies
npm install

# Rust dependencies are automatically managed by Cargo
```

### 2. Development Server

```bash
# Start Tauri dev server (opens app automatically)
npm run dev
```

This starts:

- Vite dev server on `http://localhost:5173`
- Tauri window with hot reload

### 3. Build for Production

```bash
# Build for current platform
npm run build

# Build Windows installer (.msi)
npm run build:msi

# Build for specific target (Windows x86_64)
npm run build:windows
```

## Available Commands

```bash
# Development
npm run dev              # Start dev server
npm run lint            # Run ESLint

# Production
npm run build           # Build app
npm run build:windows   # Build Windows version
npm run build:msi       # Build Windows MSI installer
npm run preview         # Preview built app

# Tauri commands
npm run tauri dev       # Start Tauri dev mode
npm run tauri build     # Build executable
npm run tauri info      # Show system info
```

## Features

### Dashboard

- Real-time metrics (errors, jobs, records processed)
- Parser and encoder usage distribution
- Job success rates
- Auto-refresh every 5 seconds

### Video Processing

- Browse and select RSD input files
- Choose output video location
- Select parser (Rust or Python)
- Select encoder (GStreamer or FFmpeg)
- Real-time job status

### Error Tracking

- All errors logged with timestamp
- Severity levels (critical, warning, info)
- Filter by severity
- Component and platform information
- Context and details for each error

### Settings

- Parser and encoder defaults
- Quality presets
- Video resolution and FPS
- Hardware acceleration toggle
- Telemetry control

### Telemetry

- Error reporting (enabled by default)
- Job metrics tracking
- Performance benchmarking
- SQLite database storage
- Export functionality for analysis

## Database

**Location**: `sonarsniffer.db` in app data directory

**Tables**:

- `error_reports` - Error tracking
- `job_metrics` - Video processing jobs
- `benchmarks` - Performance data

## API Commands (Rust Backend)

All commands invoked from React frontend:

```rust
process_video(request: ProcessVideoRequest) -> Result<json>
get_dashboard_data() -> DashboardData
get_errors(limit: i32, severity: Option<String>) -> Vec<ErrorReport>
get_job_stats(hours: i32) -> json
export_telemetry(export_path: String) -> String
get_settings() -> json
update_settings(settings: json) -> Result<()>
```

## Configuration Files

### tauri.conf.json

- Window settings (size, resizable, fullscreen)
- Security permissions (allow list)
- Build configuration
- App metadata

### package.json

- Node.js dependencies (React, Vite, Tauri)
- Build scripts
- Project metadata

### Cargo.toml

- Rust dependencies (tauri, tokio, rusqlite)
- Build features

## Platform-Specific Notes

### Windows

- Installer created in `src-tauri/target/x86_64-pc-windows-msvc/release/`
- App data stored in `%APPDATA%/SonarSniffer/`
- Visual C++ Runtime required

### macOS

- App bundle: `.app` file
- Code signing can be configured
- M1/M2 support (Apple Silicon)

### Linux

- AppImage and .deb packages
- GTK 3.6 required
- Run with: `./sonarsniffer.AppImage`

## Development Workflow

### Adding a New Page

1. Create file: `src/pages/MyPage.tsx`
2. Add route in `App.tsx`
3. Add navigation link in navbar
4. Invoke backend commands with `invoke('command_name', args)`

### Adding a New Command

1. Create function in `src-tauri/src/lib.rs`
2. Annotate with `#[tauri::command]`
3. Add to `invoke_handler!` in `main.rs`
4. Call from React: `await invoke('command_name', args)`

### Database Operations

- Use `Database` struct in `src-tauri/src/db.rs`
- Queries executed via SQLite
- Results serialized to JSON for frontend

## Testing

### Manual Testing Checklist

- [ ] Process video with Rust parser
- [ ] Process video with Python parser
- [ ] Verify error tracking
- [ ] Export telemetry data
- [ ] Settings persist across restarts
- [ ] Cross-platform compatibility

## Beta Testing for Improvements

### Collected Metrics

- Installation errors (platform, step, severity)
- Job execution (duration, parser, encoder, success rate)
- Performance benchmarks (throughput, latency)
- User preferences and settings

### Exporting Data

```
Settings → Export Telemetry → Select location
```

Exports JSON file with:

- All errors (24 hours)
- All jobs (24 hours)
- Summary statistics

### Feedback

Share telemetry exports and feedback at: **[feedback email/URL]**

## Troubleshooting

### Build Issues

**Error: `cargo build failed`**

- Run: `rustup update`
- Run: `rustup target add x86_64-pc-windows-msvc`

**Error: `npm install failed`**

- Delete `node_modules` and `package-lock.json`
- Run: `npm install` again

### Runtime Issues

**App crashes on startup**

- Check `stdout.log` in app data directory
- Verify database file permissions

**Database locked error**

- Restart application
- Check for multiple instances running

**No telemetry being recorded**

- Verify telemetry is enabled in settings
- Check database file exists
- Verify permissions on app data directory

## Performance Tips

- Use Rust parser for ~3-5x faster processing
- Enable hardware acceleration if available
- Run at lower resolution for faster encoding
- Close other applications during heavy processing

## Security & Privacy

- Telemetry data stored locally (not sent externally during beta)
- No personal information collected
- Error reports include: errors, timestamps, platform (no user data)
- Database encrypted on disk (optional, for future)

## License

[Add your license here]

## Support

For issues or questions:

1. Check troubleshooting section
2. Review error reports in app
3. Export and analyze telemetry data
4. Contact support at: [support email]

---

## Next Steps

1. **Setup**: Follow "Setup & Installation" above
2. **Test**: Run `npm run dev` and test features
3. **Build**: Create installer with `npm run build:msi`
4. **Deploy**: Distribute installer to beta testers
5. **Analyze**: Collect telemetry exports for improvements

Good luck with beta testing! 🚀
