//! SonarSniffer — Professional Marine Survey Analysis
//! 
//! Multi-format sonar file parser with self-healing capabilities,
//! curvelet denoising, geo-referenced mosaic generation, and target detection.
//!
//! Supported formats: Garmin RSD, Lowrance SL2/SL3, Humminbird, XTF, JSF, Cerulean

pub mod garmin_rsd_parser;
pub mod firmware_lookup;
pub mod healing_api;
pub mod channel_alignment;
pub mod channel_discovery;
pub mod probing;
pub mod egn;
pub mod adaptive_tvg;
pub mod export_presets;
pub mod multi_mosaic;
pub mod outputs;
pub mod overlay_align;
pub mod mosaic;
pub mod curvelet_diag;
#[doc(hidden)]
mod internal_fdct;
pub mod lowrance_parser;
pub mod humminbird_parser;
pub mod xtf_parser;
pub mod cerulean_parser;
pub mod jsf_parser;
pub mod format_detector;
pub mod target_detection;
pub mod license;

mod video;
mod video_enhanced;
mod mp4_av1;
#[cfg(not(target_arch = "wasm32"))]
mod corpus_scan;
#[cfg(not(target_arch = "wasm32"))]
pub mod deps;
#[cfg(not(target_arch = "wasm32"))]
pub mod host_profile;
#[cfg(not(target_arch = "wasm32"))]
mod static_server;

#[cfg(target_arch = "wasm32")]
pub mod wasm_api;

#[cfg(all(not(debug_assertions), target_os = "linux", feature = "jemalloc"))]
#[global_allocator]
static GLOBAL: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;
