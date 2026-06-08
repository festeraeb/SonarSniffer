SonarSniffer desktop (Tauri 2)

UI:     desktop/ui/          (index.html, app.js, styles.css)
Rust:   desktop/src-tauri/   (mirrors root src/; shares deps.rs, mp4_av1_body.rs)

Video:  built-in pure-Rust AV1/MP4 (rav1e). No GStreamer required.
        Legacy H.264: cargo tauri build --features video-gstreamer

Prerequisites (Windows): WebView2, Rust, cargo tauri CLI
Prerequisites (macOS):   Xcode CLT, Rust, cargo tauri CLI
Prerequisites (Linux):   webkit2gtk, gtk3, dbus dev packages (see root README)

Build:
  bash scripts/stage_tauri_sidecars.sh     # Linux/macOS — stage CLI + soundtiles sidecars
  cd desktop/src-tauri && cargo tauri build --bundles dmg   # or msi,nsis on Windows

Windows MSI + Setup.exe:
  .\scripts\build_sonarsniffer_desktop_msi_windows.ps1
  .\scripts\pack_sonarsniffer_windows_setup.ps1
