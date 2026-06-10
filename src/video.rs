use crate::garmin_rsd_parser::{ParseResult, Ping};
use crate::outputs::{build_stitched_mosaic_rgb, mosaic_guide_pings, PipelineOptions};
use crate::video_enhanced::{render_enhanced_waterfall, render_mosaic_waterfall, auto_params_from_dataset, Colormap, SonarProcessingParams};
use serde::Serialize;
use std::path::Path;

#[derive(Debug, Clone, Serialize)]
pub struct VideoExportResult {
    pub enabled: bool,
    pub status: String,
    pub output_path: Option<String>,
}

/// ParseResult entry point used by CLI/tests — uses enhanced stitched mosaic when possible.
pub fn run_video_export(parsed: &ParseResult, output_dir: &Path) -> VideoExportResult {
    let discovery = crate::channel_discovery::discover_and_profile(parsed);
    let proposal = crate::channel_discovery::propose_stitch_layouts(parsed, &discovery);
    let (pk, sk, align) =
        crate::channel_discovery::sidescan_pair_from_layout(&proposal, None);
    let mut options = PipelineOptions::default();
    options.channel_alignments = align;
    run_video_export_stitch(
        parsed,
        output_dir,
        &options,
        (pk, sk),
        Some(&discovery),
    )
}

/// Pipeline path — respects layout proposal, alignments, and scroll speed options.
pub fn run_video_export_stitch(
    parsed: &ParseResult,
    output_dir: &Path,
    options: &PipelineOptions,
    sidescan_pair: (Option<u32>, Option<u32>),
    discovery: Option<&crate::channel_discovery::DiscoveryResult>,
) -> VideoExportResult {
    run_video_export_pings(
        parsed,
        parsed.pings.clone(),
        output_dir,
        Box::new(|_, _| {}),
        options,
        sidescan_pair,
        discovery,
    )
}

/// Owned-pings variant called from the background thread (lib.rs).
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
        let mut vparams = SonarProcessingParams::high_quality();
        vparams.fps = options.video_fps.max(1);
        vparams.video_height = options.video_height.max(1);
        vparams.video_speed_mode = options.video_speed_mode.clone();
        vparams.video_readable_pings_per_sec = options.video_readable_pings_per_sec;
        vparams.overlay_depth = options.overlay_depth;
        vparams.overlay_speed = options.overlay_speed;
        vparams.overlay_gps = options.overlay_gps;
        let guide = mosaic_guide_pings(&parse_for_mosaic, sidescan_pair);
        vparams.colormap = match options.colormap.to_lowercase().as_str() {
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
        match render_mosaic_waterfall(mosaic, output_dir, vparams, Some(guide), progress) {
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
    let mut params = SonarProcessingParams::high_quality();
    let auto = auto_params_from_dataset(&pings);
    params.tvg_spreading_factor = auto.tvg_spreading_factor;
    params.tvg_absorption_db_per_m = auto.tvg_absorption_db_per_m;
    params.noise_floor_db = auto.noise_floor_db;
    params.remove_water_column = options.remove_water_column;
    params.colormap = colormap;
    params.video_height = options.video_height;
    params.fps = options.video_fps.max(1);
    params.video_height = options.video_height.max(1);
    params.video_speed_mode = options.video_speed_mode.clone();
    params.video_readable_pings_per_sec = options.video_readable_pings_per_sec;
    params.median_filter_enabled = true;
    params.median_kernel_size = if options.curvelet_denoise { 5 } else { 3 };
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
