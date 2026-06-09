use crate::garmin_rsd_parser::{ParseResult, Ping};
use crate::outputs::{build_stitched_mosaic_rgb, PipelineOptions};
use crate::video_enhanced::{render_enhanced_waterfall, render_mosaic_waterfall, Colormap, SonarProcessingParams};
use serde::Serialize;
use std::path::Path;

#[derive(Debug, Clone, Serialize)]
pub struct VideoExportResult {
    pub enabled: bool,
    pub status: String,
    pub output_path: Option<String>,
}

/// ParseResult entry point used by CLI/tests.
#[allow(dead_code)]
pub fn run_video_export(parsed: &ParseResult, output_dir: &Path) -> VideoExportResult {
    export_with_params(parsed.pings.clone(), output_dir, Box::new(|_, _| {}), SonarProcessingParams::default())
}

/// Owned-pings variant called from the background thread (lib.rs).
/// Renders from the same enhanced stitched mosaic pipeline as `mosaic_combined.png`.
pub fn run_video_export_pings(
    parsed: &ParseResult,
    pings: Vec<Ping>,
    output_dir: &Path,
    on_progress: Box<dyn Fn(u32, u32) + Send>,
    options: &PipelineOptions,
    sidescan_pair: (Option<u32>, Option<u32>),
    discovery: Option<&crate::channel_discovery::DiscoveryResult>,
) -> VideoExportResult {
    let mut parse_for_mosaic = parsed.clone();
    parse_for_mosaic.pings = pings;

    if let Some(mosaic) = build_stitched_mosaic_rgb(
        &parse_for_mosaic,
        &options.colormap,
        options.remove_water_column,
        &options.nadir_mode,
        &options.channel_alignments,
        sidescan_pair,
        discovery,
    ) {
        let progress = move |frame: u32, total: u32| on_progress(frame, total);
        match render_mosaic_waterfall(
            mosaic,
            output_dir,
            options.video_fps,
            options.video_height,
            progress,
        ) {
            Ok(result) => VideoExportResult {
                enabled: true,
                status: result.status,
                output_path: result.output_path,
            },
            Err(err) => VideoExportResult {
                enabled: true,
                status: format!("Mosaic video export failed: {err:#}"),
                output_path: None,
            },
        }
    } else {
        export_with_params_fallback(parse_for_mosaic.pings, output_dir, on_progress, options)
    }
}

fn export_with_params_fallback(
    pings: Vec<Ping>,
    output_dir: &Path,
    on_progress: Box<dyn Fn(u32, u32) + Send>,
    options: &PipelineOptions,
) -> VideoExportResult {
    let colormap = match options.colormap.to_lowercase().as_str() {
        "grayscale" | "gray" | "greyscale" => Colormap::Grayscale,
        "sonar" => Colormap::SonarCustom,
        "plasma" => Colormap::Plasma,
        "ocean" => Colormap::Ocean,
        "inferno" => Colormap::Inferno,
        "iron" => Colormap::Iron,
        "rainbow" => Colormap::Rainbow,
        "viridis" => Colormap::Viridis,
        "magma" => Colormap::Magma,
        "jet" => Colormap::Jet,
        _ => Colormap::Amber,
    };
    let params = SonarProcessingParams {
        remove_water_column: options.remove_water_column,
        colormap,
        video_height: options.video_height,
        fps: options.video_fps,
        median_filter_enabled: true,
        median_kernel_size: if options.curvelet_denoise { 5 } else { 3 },
        ..SonarProcessingParams::high_quality()
    };
    export_with_params(pings, output_dir, on_progress, params)
}

fn export_with_params(
    pings: Vec<Ping>,
    output_dir: &Path,
    on_progress: Box<dyn Fn(u32, u32) + Send>,
    params: SonarProcessingParams,
) -> VideoExportResult {
    if pings.is_empty() {
        return VideoExportResult {
            enabled: true,
            status: "No pings available for video export".to_string(),
            output_path: None,
        };
    }

    let progress = move |frame: u32, total: u32| {
        on_progress(frame, total);
    };

    match render_enhanced_waterfall(pings, output_dir, params, progress) {
        Ok(result) => VideoExportResult {
            enabled: true,
            status: result.status,
            output_path: result.output_path,
        },
        Err(err) => VideoExportResult {
            enabled: true,
            status: format!("Video export failed: {err:#}"),
            output_path: None,
        },
    }
}
