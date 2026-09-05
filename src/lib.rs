//! SonarSniffer — Professional Marine Survey Analysis
//!
//! Multi-format sonar file parser with self-healing capabilities,
//! curvelet denoising, geo-referenced mosaic generation, and target detection.
//!
//! Supported formats: Garmin RSD, Lowrance SL2/SL3, Humminbird, XTF, JSF, Cerulean
//!
//! WASM (`target_arch = "wasm32"`) exposes `wasm_api` and the parser modules needed
//! by the browser pipeline.  Heavy native-only modules (rusqlite-backed mbtiles,
//! gstreamer video, opencv SoundTiles) stay native-only — see docs/BUILD_FLAGS.md.

#![cfg_attr(target_arch = "wasm32", allow(dead_code))]

// Parser + discovery modules are exposed on both native and wasm so the
// browser build can run parse + channel discovery on raw bytes.  They use
// only std::fs / std::io (no mmap), so they're wasm-safe.
pub mod garmin_rsd_parser;
#[cfg(not(target_arch = "wasm32"))]
pub mod firmware_lookup;
#[cfg(not(target_arch = "wasm32"))]
pub mod healing_api;
#[cfg(not(target_arch = "wasm32"))]
pub mod channel_alignment;
pub mod channel_discovery;
#[cfg(not(target_arch = "wasm32"))]
pub mod probing;
#[cfg(not(target_arch = "wasm32"))]
pub mod egn;
#[cfg(not(target_arch = "wasm32"))]
pub mod adaptive_tvg;
#[cfg(not(target_arch = "wasm32"))]
pub mod export_presets;
#[cfg(not(target_arch = "wasm32"))]
pub mod multi_mosaic;
#[cfg(not(target_arch = "wasm32"))]
pub mod outputs;
#[cfg(not(target_arch = "wasm32"))]
pub mod overlay_align;
#[cfg(not(target_arch = "wasm32"))]
pub mod mosaic;
#[cfg(not(target_arch = "wasm32"))]
pub mod curvelet_diag;
#[cfg(not(target_arch = "wasm32"))]
#[doc(hidden)]
mod internal_fdct;
#[cfg(not(target_arch = "wasm32"))]
pub mod lowrance_parser;
#[cfg(not(target_arch = "wasm32"))]
pub mod humminbird_parser;
#[cfg(not(target_arch = "wasm32"))]
pub mod xtf_parser;
#[cfg(not(target_arch = "wasm32"))]
pub mod cerulean_parser;
#[cfg(not(target_arch = "wasm32"))]
pub mod jsf_parser;
pub mod format_detector;
#[cfg(not(target_arch = "wasm32"))]
pub mod target_detection;
#[cfg(not(target_arch = "wasm32"))]
pub mod license;

#[cfg(not(target_arch = "wasm32"))]
mod video;
#[cfg(not(target_arch = "wasm32"))]
mod video_enhanced;
#[cfg(not(target_arch = "wasm32"))]
mod mp4_av1;
#[cfg(not(target_arch = "wasm32"))]
mod corpus_scan;
#[cfg(not(target_arch = "wasm32"))]
pub mod deps;
#[cfg(not(target_arch = "wasm32"))]
pub mod host_profile;
#[cfg(not(target_arch = "wasm32"))]
mod static_server;

// WASM browser pipeline.  `parse_bytes` and `discover_bytes` accept &[u8]
// so the JS side hands in a `File.arrayBuffer()` directly.
#[cfg(target_arch = "wasm32")]
pub mod wasm_api;
#[cfg(target_arch = "wasm32")]
pub mod wasm_pipeline;

/// WASM stub of `channel_alignment`.  The real module pulls in
/// persistence + JSON that we don't need in the browser.  A flat
/// `ChannelAlignment` struct is enough for type compatibility with the
/// `channel_discovery` signatures.
#[cfg(target_arch = "wasm32")]
pub mod channel_alignment {
    #[derive(Debug, Clone, serde::Serialize)]
    pub struct ChannelAlignment {
        pub channel_id: u32,
        pub role: String,
        pub generation: String,
        pub flip: bool,
        pub invert: bool,
    }
}

#[cfg(all(not(debug_assertions), target_os = "linux", feature = "jemalloc"))]
#[global_allocator]
static GLOBAL: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;
