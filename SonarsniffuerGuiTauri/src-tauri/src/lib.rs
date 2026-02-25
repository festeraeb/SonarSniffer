mod corpus_scan;
mod garmin_rsd_parser;
mod firmware_lookup;
pub mod outputs;
mod video;

use corpus_scan::CorpusScanResult;
use garmin_rsd_parser::GarminRSDParser;
use outputs::{build_outputs, PipelineOptions};
use serde::Serialize;
use std::path::{Path, PathBuf};
use video::VideoExportResult;

#[derive(Debug, Clone, Serialize)]
pub struct PipelineResponse {
    pub input_file: String,
    pub parse: garmin_rsd_parser::ParseResult,
    pub outputs: Option<outputs::OutputSummary>,
    pub video: Option<VideoExportResult>,
    /// [min_ft, max_ft, avg_ft] computed before pings are cleared.
    pub depth_stats: [f32; 3],
    pub status: String,
}

#[derive(Debug, Clone, Serialize)]
struct FirmwareLookupResponse {
    analysis: firmware_lookup::FirmwareLookupResult,
    status: String,
}

#[derive(Debug, Clone, Serialize)]
struct CorpusScanResponse {
    scan: CorpusScanResult,
    status: String,
}

#[tauri::command]
fn pick_input_file() -> Option<String> {
    rfd::FileDialog::new()
        .add_filter("Sonar logs", &["rsd", "RSD"])
        .pick_file()
        .map(|path| path.display().to_string())
}

#[tauri::command]
fn pick_any_file() -> Option<String> {
    rfd::FileDialog::new()
        .pick_file()
        .map(|path| path.display().to_string())
}

#[tauri::command]
fn pick_folder() -> Option<String> {
    rfd::FileDialog::new()
        .pick_folder()
        .map(|path| path.display().to_string())
}

#[tauri::command]
fn run_sonar_pipeline(file_name: &str, options: Option<PipelineOptions>) -> PipelineResponse {
    run_pipeline_internal(file_name, options)
}

pub fn run_pipeline_internal(file_name: &str, options: Option<PipelineOptions>) -> PipelineResponse {
    let options = options.unwrap_or_default();
    let mut parser = GarminRSDParser::new();
    let path = Path::new(file_name);
    let mut parse = parser.parse_file(path);

    let outputs = if parse.error_message.is_none() {
        build_outputs(path, &parse, &options).ok()
    } else {
        None
    };

    // Compute depth stats BEFORE clearing pings so the frontend can still show them.
    let depth_stats = {
        let depths: Vec<f32> = parse.pings.iter()
            .map(|p| p.depth_ft)
            .filter(|&d| d > 0.0)
            .collect();
        if depths.is_empty() {
            [0.0_f32; 3]
        } else {
            let min = depths.iter().cloned().fold(f32::MAX, f32::min);
            let max = depths.iter().cloned().fold(f32::MIN, f32::max);
            let avg = depths.iter().sum::<f32>() / depths.len() as f32;
            [min, max, avg]
        }
    };

    // Video – spawn in a background thread so the IPC call returns immediately.
    // We take the pings out of `parse` for the thread; this also prevents the
    // massive JSON serialisation of ~80 k pings across the Tauri IPC bridge.
    let video = if options.video {
        let vid_dir: PathBuf = outputs
            .as_ref()
            .map(|o| PathBuf::from(&o.output_dir))
            .unwrap_or_else(|| {
                path.parent()
                    .map(|p| p.to_path_buf())
                    .unwrap_or_else(|| PathBuf::from("."))
            });
        let pings_for_video = std::mem::take(&mut parse.pings);
        let vid_dir_clone = vid_dir.clone();
        std::thread::spawn(move || {
            video::run_video_export_pings(pings_for_video, &vid_dir_clone);
        });
        Some(VideoExportResult {
            enabled: true,
            status: "Video rendering in background — check output folder for sonar_waterfall.mp4"
                .to_string(),
            output_path: Some(vid_dir.join("sonar_waterfall.mp4").display().to_string()),
        })
    } else {
        // Still clear pings to avoid 160 MB IPC serialisation
        parse.pings.clear();
        None
    };

    let status = if let Some(err) = &parse.error_message {
        format!("Parsing failed: {err}")
    } else {
        "Pipeline complete".to_string()
    };

    PipelineResponse {
        input_file: file_name.to_string(),
        parse,
        outputs,
        video,
        depth_stats,
        status,
    }
}

#[tauri::command]
fn analyze_firmware(file_name: &str) -> FirmwareLookupResponse {
    let analysis = firmware_lookup::analyze_firmware_file(Path::new(file_name));
    let status = if let Some(err) = &analysis.error_message {
        format!("Firmware analysis failed: {err}")
    } else {
        format!(
            "Firmware analysis complete ({} float hits, {} XOR blocks)",
            analysis.float_hits.len(),
            analysis.xor_blocks.len()
        )
    };

    FirmwareLookupResponse { analysis, status }
}

/// Open a file or folder in the native file manager (Windows Explorer).
/// If `path` points to a file the containing folder is opened with the file
/// selected; if it points to a directory the directory is opened directly.
#[tauri::command]
fn reveal_path(path: String, app: tauri::AppHandle) -> Result<(), String> {
    use tauri_plugin_opener::OpenerExt;
    app.opener()
        .reveal_item_in_dir(&path)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn scan_corpus_directory(root_dir: &str) -> CorpusScanResponse {
    let scan = corpus_scan::scan_corpus_dir(Path::new(root_dir));
    let status = if let Some(err) = &scan.error_message {
        format!("Corpus scan failed: {err}")
    } else if scan.truncated {
        format!(
            "Corpus scan complete ({} matched files, showing first {} hits)",
            scan.matched_files,
            scan.hits.len()
        )
    } else {
        format!("Corpus scan complete ({} matched files)", scan.matched_files)
    };

    CorpusScanResponse { scan, status }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
    .invoke_handler(tauri::generate_handler![
            pick_input_file,
            pick_any_file,
            pick_folder,
            reveal_path,
            run_sonar_pipeline,
            analyze_firmware,
            scan_corpus_directory
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
