//! Pure-Rust MP4 (ISOBMFF) muxer for AV1 video — no system libs, no C, no NASM.
//!
//! Takes AV1 temporal-unit packets (as produced by `rav1e`) plus timing and
//! writes a standards-compliant `.mp4` with an `av01` sample entry and an
//! `av1C` (AV1CodecConfigurationRecord) box. Plays in VLC, mpv, modern
//! browsers, and the Tauri (WebKit/WebView2) desktop shell.
//!
//! References: ISO/IEC 14496-12 (ISOBMFF) and the AV1 Codec ISO Media File
//! Format Binding v1.2.0 (av1C / av01 boxes).

include!("mp4_av1_body.rs");
