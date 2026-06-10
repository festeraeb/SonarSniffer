//! Enhanced sonar waterfall video generation with proper signal processing.
//!
//! This module implements industry-standard sonar corrections including:
//! - Time-Varied Gain (TVG) for geometric spreading and absorption
//! - Logarithmic dynamic range compression
//! - Noise reduction via median and bilateral filtering
//! - Contrast enhancement via histogram equalization and CLAHE
//! - Perceptual colormaps (viridis, magma, custom sonar palette)
//!
//! # Architecture
//!
//! ```text
//! Raw Samples → TVG Correction → Log Compression → Filtering
//!   → Histogram Eq → Colormap → Frame Rendering → Video Encoding
//! ```

mod colormaps;
mod filters;
mod hud;
mod processing;
mod renderer;
mod scroll;
mod statistics;
pub mod tvg;

pub use scroll::{build_scroll_timeline, scroll_window, VideoSpeedMode};

use serde::{Deserialize, Serialize};
use std::path::Path;

// Re-export key types
pub use colormaps::{ColorLUT, Colormap};
pub use processing::{apply_processing_pipeline, ProcessedFrame};
pub use renderer::encode_to_video;
#[allow(unused_imports)]
pub use statistics::{compute_dataset_statistics, DatasetStatistics};
#[allow(unused_imports)]
pub use tvg::apply_tvg_correction;

/// Comprehensive processing parameters for sonar enhancement.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SonarProcessingParams {
    // ═══════════════════════════════════════════════════════════════════════
    // TVG (Time-Varied Gain) Parameters
    // ═══════════════════════════════════════════════════════════════════════
    /// Enable Time-Varied Gain correction for geometric spreading and absorption.
    pub tvg_enabled: bool,

    /// Spreading factor in dB (typically 10-40).
    /// - 10-15: Shallow water, strong returns
    /// - 20: Standard spherical spreading
    /// - 25-30: Deep water
    /// - 35-40: Extreme range compensation
    pub tvg_spreading_factor: f32,

    /// Absorption coefficient in dB/m (frequency-dependent).
    /// - 455 kHz: ~0.10 dB/m
    /// - 800 kHz: ~0.30 dB/m
    pub tvg_absorption_db_per_m: f32,

    /// Skip TVG correction for first N samples (near-field artifact avoidance).
    pub tvg_start_sample: usize,

    /// Speed of sound in m/s (typically 1500 for freshwater, 1480-1540 range).
    pub sound_speed_m_per_s: f32,

    /// Sample rate in Hz (if known; used for accurate range calculation).
    /// Leave at 0.0 to use sample index directly as proxy for range.
    pub sample_rate_hz: f32,

    // ═══════════════════════════════════════════════════════════════════════
    // Dynamic Range Compression
    // ═══════════════════════════════════════════════════════════════════════
    /// Apply logarithmic compression (20*log10) to map wide dB range to 0-255.
    pub log_compression: bool,

    /// Noise floor in dB (typically -60 to -70).
    pub noise_floor_db: f32,

    /// Signal ceiling in dB (typically 0).
    pub signal_ceiling_db: f32,

    /// Automatically compute floor/ceiling from dataset percentiles instead of fixed values.
    pub use_adaptive_range: bool,

    /// Percentile for adaptive floor (e.g., 0.1 = 0.1%).
    pub floor_percentile: f32,

    /// Percentile for adaptive ceiling (e.g., 99.9).
    pub ceiling_percentile: f32,

    // ═══════════════════════════════════════════════════════════════════════
    // Filtering
    // ═══════════════════════════════════════════════════════════════════════
    /// Apply median filter to remove speckle noise.
    pub median_filter_enabled: bool,

    /// Median filter kernel size (3, 5, or 7).
    pub median_kernel_size: usize,

    /// Apply bilateral filter for edge-preserving smoothing.
    pub bilateral_filter_enabled: bool,

    /// Bilateral spatial sigma (controls spatial extent, typically 3-5).
    pub bilateral_spatial_sigma: f32,

    /// Bilateral range sigma (controls intensity similarity, typically 0.1-0.3).
    pub bilateral_range_sigma: f32,

    // ═══════════════════════════════════════════════════════════════════════
    // Contrast Enhancement
    // ═══════════════════════════════════════════════════════════════════════
    /// Apply global histogram equalization.
    pub histogram_equalization: bool,

    /// Apply CLAHE (Contrast-Limited Adaptive Histogram Equalization).
    pub clahe_enabled: bool,

    /// CLAHE tile size (8, 16, or 32 pixels per tile dimension).
    pub clahe_tile_size: usize,

    /// CLAHE clip limit (1.0 = minimal, 2.0 = moderate, 4.0 = strong).
    pub clahe_clip_limit: f32,

    // ═══════════════════════════════════════════════════════════════════════
    // Colormap
    // ═══════════════════════════════════════════════════════════════════════
    /// Colormap selection for final rendering.
    pub colormap: Colormap,

    // ═══════════════════════════════════════════════════════════════════════
    // Gap Handling
    // ═══════════════════════════════════════════════════════════════════════
    /// Interpolate missing data (black regions).
    pub interpolate_gaps: bool,

    /// Minimum consecutive zero/low samples to consider a gap.
    pub gap_threshold_samples: usize,

    // ═══════════════════════════════════════════════════════════════════════
    // Video Encoding
    // ═══════════════════════════════════════════════════════════════════════
    /// Frame rate for output video.
    pub fps: u32,

    /// Viewport height in pixels (visible ping rows on screen).
    pub video_height: u32,

    /// `readable` (default, ~2 pings/s) or `survey` (match file ping rate).
    #[serde(default = "default_video_speed_mode")]
    pub video_speed_mode: String,

    /// Display rate when `video_speed_mode` is `readable`.
    #[serde(default = "default_readable_pps")]
    pub video_readable_pings_per_sec: f32,

    /// Prefer hardware encoding (NVENC, QuickSync) if available.
    pub prefer_hardware_encoding: bool,

    // ═══════════════════════════════════════════════════════════════════════
    // Water Column
    // ═══════════════════════════════════════════════════════════════════════
    /// Strip the near-field blank water-column region from every ping row.
    /// Uses the same auto-detect nadir approach as the static mosaic images.
    pub remove_water_column: bool,

    /// Burn depth / speed / GPS into scrolling mosaic video frames.
    pub overlay_depth: bool,
    pub overlay_speed: bool,
    pub overlay_gps: bool,
}

fn default_video_speed_mode() -> String {
    "readable".to_string()
}
fn default_readable_pps() -> f32 {
    2.0
}

impl Default for SonarProcessingParams {
    fn default() -> Self {
        Self {
            // TVG defaults
            tvg_enabled: true,
            tvg_spreading_factor: 20.0,
            tvg_absorption_db_per_m: 0.15,
            tvg_start_sample: 5,
            sound_speed_m_per_s: 1500.0,
            sample_rate_hz: 0.0, // Unknown; use sample index

            // Dynamic range defaults
            log_compression: true,
            noise_floor_db: -60.0,
            signal_ceiling_db: 0.0,
            use_adaptive_range: true,
            floor_percentile: 0.1,
            ceiling_percentile: 99.9,

            // Filtering defaults (conservative)
            median_filter_enabled: true,
            median_kernel_size: 3,
            bilateral_filter_enabled: false, // Optional (slower)
            bilateral_spatial_sigma: 3.0,
            bilateral_range_sigma: 0.2,

            // Contrast defaults
            histogram_equalization: true,
            clahe_enabled: false, // Optional (best for non-uniform scenes)
            clahe_tile_size: 16,
            clahe_clip_limit: 2.0,

            // Colormap default
            colormap: Colormap::Amber,

            // Gap handling
            interpolate_gaps: true,
            gap_threshold_samples: 10,

            // Video encoding
            fps: 24,
            video_height: 1080,
            video_speed_mode: default_video_speed_mode(),
            video_readable_pings_per_sec: default_readable_pps(),
            prefer_hardware_encoding: false,

            // Water column
            remove_water_column: false,

            overlay_depth: false,
            overlay_speed: false,
            overlay_gps: false,
        }
    }
}

impl SonarProcessingParams {
    /// Preset for high-quality processing (slower, best visual results).
    pub fn high_quality() -> Self {
        Self {
            tvg_enabled: true,
            log_compression: true,
            use_adaptive_range: true,
            median_filter_enabled: true,
            median_kernel_size: 5,
            bilateral_filter_enabled: true,
            histogram_equalization: true,
            clahe_enabled: true,
            colormap: Colormap::Viridis,
            interpolate_gaps: true,
            ..Default::default()
        }
    }

    /// Preset for fast processing (minimal corrections).
    pub fn fast() -> Self {
        Self {
            tvg_enabled: true,
            log_compression: true,
            use_adaptive_range: false,
            median_filter_enabled: false,
            bilateral_filter_enabled: false,
            histogram_equalization: false,
            clahe_enabled: false,
            colormap: Colormap::Grayscale,
            interpolate_gaps: false,
            ..Default::default()
        }
    }

    /// Preset for shallow water (strong returns, less gain needed).
    pub fn shallow_water() -> Self {
        Self {
            tvg_spreading_factor: 15.0,
            tvg_absorption_db_per_m: 0.10,
            noise_floor_db: -50.0,
            ..Self::default()
        }
    }

    /// Preset for deep water (weak returns, more gain needed).
    pub fn deep_water() -> Self {
        Self {
            tvg_spreading_factor: 30.0,
            tvg_absorption_db_per_m: 0.20,
            noise_floor_db: -70.0,
            ..Self::default()
        }
    }
}

/// Result of enhanced video export.
#[derive(Debug, Clone, Serialize)]
pub struct EnhancedVideoResult {
    pub success: bool,
    pub output_path: Option<String>,
    pub status: String,
    pub processing_stats: Option<ProcessingStats>,
}

/// Statistics about the processing pipeline.
#[derive(Debug, Clone, Serialize)]
pub struct ProcessingStats {
    pub total_pings: usize,
    pub frames_generated: u32,
    pub primary_channel: u32,
    pub video_width: u32,
    pub video_height: u32,
    pub fps: u32,
    pub duration_secs: f32,
    pub file_size_mb: f64,

    // Signal statistics
    pub raw_min: f32,
    pub raw_max: f32,
    pub raw_mean: f32,
    pub processed_min: f32,
    pub processed_max: f32,
    pub processed_mean: f32,

    // Processing flags
    pub tvg_applied: bool,
    pub log_compression_applied: bool,
    pub filtering_applied: bool,
    pub histogram_eq_applied: bool,
    pub clahe_applied: bool,
}

/// Scrolling waterfall frames from a stitched mosaic (bottom-fill, then scroll up).
pub fn mosaic_to_scroll_frames(
    mosaic: &image::RgbImage,
    params: &SonarProcessingParams,
    guide_pings: Option<&[crate::garmin_rsd_parser::Ping]>,
) -> Vec<ProcessedFrame> {
    use hud::draw_scroll_hud_guide;
    use scroll::{build_scroll_timeline, scroll_window, VideoSpeedMode};

    let width = mosaic.width();
    let height = mosaic.height();
    if width == 0 || height == 0 {
        return vec![];
    }
    let viewport = params.video_height.max(1).min(height) as usize;
    let speed = VideoSpeedMode::from_option(&params.video_speed_mode);
    let timeline = build_scroll_timeline(
        height as usize,
        guide_pings.unwrap_or(&[]),
        speed,
        params.video_readable_pings_per_sec,
        params.fps,
    );

    let hud_on = params.overlay_depth || params.overlay_speed || params.overlay_gps;
    let bg = [5u8, 10, 20];
    let mut frames = Vec::with_capacity(timeline.end_ping_indices.len());
    for &end_row in &timeline.end_ping_indices {
        let (data_start, data_end, top_pad) = scroll_window(end_row, viewport);
        let mut pixels = vec![0u8; width as usize * viewport * 3];
        for i in 0..pixels.len() {
            pixels[i] = bg[i % 3];
        }
        for dst_y in 0..(data_end - data_start) {
            let src_y = (data_start + dst_y) as u32;
            let out_y = top_pad + dst_y;
            for x in 0..width {
                let px = mosaic.get_pixel(x, src_y);
                let off = (out_y * width as usize + x as usize) * 3;
                pixels[off] = px[0];
                pixels[off + 1] = px[1];
                pixels[off + 2] = px[2];
            }
        }
        if hud_on {
            if let Some(guide) = guide_pings {
                draw_scroll_hud_guide(
                    &mut pixels,
                    width,
                    viewport as u32,
                    guide,
                    end_row,
                    params.overlay_depth,
                    params.overlay_speed,
                    params.overlay_gps,
                );
            }
        }
        frames.push(ProcessedFrame {
            pixels,
            width,
            height: viewport as u32,
        });
    }
    frames
}

/// Encode video directly from an enhanced stitched mosaic image.
pub fn render_mosaic_waterfall<F>(
    mosaic: image::RgbImage,
    output_dir: &Path,
    params: SonarProcessingParams,
    guide_pings: Option<Vec<crate::garmin_rsd_parser::Ping>>,
    on_progress: F,
) -> anyhow::Result<EnhancedVideoResult>
where
    F: Fn(u32, u32) + Send + 'static,
{
    use anyhow::Context;
    let params = params;
    let guide_ref = guide_pings.as_deref();
    let frames = mosaic_to_scroll_frames(&mosaic, &params, guide_ref);
    let stats = DatasetStatistics {
        total_pings: frames.len(),
        primary_channel: 0,
        max_samples: mosaic.width() as usize / 2,
        raw_min: 0.0,
        raw_max: 255.0,
        raw_mean: 128.0,
        raw_stddev: 64.0,
        percentile_floor: 1.0,
        percentile_ceiling: 254.0,
        histogram: [0; 256],
        gaps: vec![],
    };
    encode_to_video(frames, output_dir, &params, &stats, on_progress)
        .context("Failed to encode mosaic video")
}

/// High-level API: Render enhanced waterfall with automatic parameter selection.
///
/// This function:
/// 1. Analyzes the dataset to compute statistics
/// 2. Applies the full processing pipeline
/// 3. Encodes video with progress callbacks
///
/// # Arguments
/// - `pings`: Sonar ping data (consumed)
/// - `output_dir`: Directory for output video
/// - `params`: Processing parameters (use `Default::default()` for sensible defaults)
/// - `on_progress`: Callback for progress updates (frame_index, total_frames)
pub fn render_enhanced_waterfall<F>(
    pings: Vec<crate::garmin_rsd_parser::Ping>,
    output_dir: &Path,
    params: SonarProcessingParams,
    on_progress: F,
) -> anyhow::Result<EnhancedVideoResult>
where
    F: Fn(u32, u32) + Send + 'static,
{
    use anyhow::Context;

    // Pass 1: Analyze dataset
    let stats = compute_dataset_statistics(&pings, &params)
        .context("Failed to compute dataset statistics")?;

    // Pass 2: Apply processing pipeline
    let processed = apply_processing_pipeline(&pings, &params, &stats)
        .context("Failed to apply processing pipeline")?;

    // Pass 3: Encode video
    let result = encode_to_video(processed, output_dir, &params, &stats, on_progress)
        .context("Failed to encode video")?;

    Ok(result)
}

/// Convenience function: Render with default parameters.
pub fn render_enhanced_waterfall_auto<F>(
    pings: Vec<crate::garmin_rsd_parser::Ping>,
    output_dir: &Path,
    on_progress: F,
) -> anyhow::Result<EnhancedVideoResult>
where
    F: Fn(u32, u32) + Send + 'static,
{
    let params = auto_params_from_dataset(&pings);
    render_enhanced_waterfall(pings, output_dir, params, on_progress)
}

/// Build runtime presets from observed dataset size and depth profile.
pub fn auto_params_from_dataset(pings: &[crate::garmin_rsd_parser::Ping]) -> SonarProcessingParams {
    let mut params = if pings.len() > 20_000 {
        SonarProcessingParams::fast()
    } else {
        SonarProcessingParams::high_quality()
    };

    let (depth_sum, depth_count) = pings
        .iter()
        .filter_map(|p| {
            if p.depth_m.is_finite() && p.depth_m > 0.0 {
                Some(p.depth_m)
            } else {
                None
            }
        })
        .fold((0.0f32, 0usize), |(s, c), d| (s + d, c + 1));

    let mean_depth = if depth_count > 0 {
        depth_sum / depth_count as f32
    } else {
        0.0
    };

    let water_profile = if mean_depth > 20.0 {
        SonarProcessingParams::deep_water()
    } else {
        SonarProcessingParams::shallow_water()
    };

    params.tvg_spreading_factor = water_profile.tvg_spreading_factor;
    params.tvg_absorption_db_per_m = water_profile.tvg_absorption_db_per_m;
    params.noise_floor_db = water_profile.noise_floor_db;
    params
}
