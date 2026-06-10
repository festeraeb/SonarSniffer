/// parse_cli — Full pipeline CLI for SonarSniffer.
///
/// Parses a sonar file, runs the output pipeline, and prints results as JSON.

use std::env;
use std::path::Path;

use sonarsniffer_lib::format_detector;
use sonarsniffer_lib::host_profile::{self, SettingsTier, SonarSurveyHint};
use sonarsniffer_lib::outputs::{build_outputs, PipelineOptions};

fn main() {
    sonarsniffer_lib::host_profile::init_runtime();

    let mut args = env::args().skip(1);
    let mut file: Option<String> = None;

    let mut options = PipelineOptions::default();
    let mut summary_only = false;
    let mut preflight_only = false;
    let mut host_info_only = false;
    let mut first_n: Option<usize> = None;
    let mut settings_tier: Option<SettingsTier> = None;

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--preflight" => preflight_only = true,
            "--host-info" => host_info_only = true,
            "--fast" => settings_tier = Some(SettingsTier::Fast),
            "--suggested" | "--auto-settings" => settings_tier = Some(SettingsTier::Auto),
            "--full" => settings_tier = Some(SettingsTier::Full),
            "--light" => {
                options.video = false;
                options.mosaic = false;
                options.waterfall = false;
                options.mbtiles = false;
                options.kmz = false;
                options.arcgis = false;
                options.web_viewer = false;
            }
            "--curvelet" => {
                options.curvelet_denoise = true;
            }
            "--curvelet-auto" => {
                options.curvelet_denoise = true;
                options.curvelet_auto = true;
            }
            "--curvelet-threshold" => {
                if let Some(t) = args.next() {
                    if let Ok(v) = t.parse::<f32>() {
                        options.curvelet_denoise = true;
                        options.curvelet_auto = false;
                        options.curvelet_threshold = v;
                    }
                }
            }
            "--no-video" => options.video = false,
            "--no-kml" => options.kml = false,
            "--no-kmz" => options.kmz = false,
            "--no-mbtiles" => options.mbtiles = false,
            "--no-mosaic" => options.mosaic = false,
            "--no-waterfall" => options.waterfall = false,
            "--no-arcgis" => options.arcgis = false,
            "--no-viewer" => options.web_viewer = false,
            "--video-downscope-rtl" => options.video_downscope_rtl = true,
            "--summary" => summary_only = true,
            "--first-n" => {
                if let Some(n_str) = args.next() {
                    match n_str.parse::<usize>() {
                        Ok(n) => first_n = Some(n),
                        Err(_) => eprintln!("--first-n requires an integer argument"),
                    }
                } else {
                    eprintln!("--first-n requires an integer argument");
                }
            }
            "--output-dir" => {
                if let Some(dir) = args.next() {
                    options.output_dir = Some(dir);
                }
            }
            val if val.starts_with('-') => {
                eprintln!("Unknown flag: {val}");
            }
            val => {
                file = Some(val.to_string());
            }
        }
    }

    if preflight_only {
        let deps = sonarsniffer_lib::deps::preflight_report();
        let host = host_profile::probe_host();
        let output = serde_json::json!({
            "deps": deps,
            "host": host,
        });
        println!("{}", serde_json::to_string_pretty(&output).unwrap_or_default());
        std::process::exit(if deps.ready { 0 } else { 2 });
    }

    if host_info_only {
        let host = host_profile::probe_host();
        println!("{}", serde_json::to_string_pretty(&host).unwrap_or_default());
        return;
    }

    let Some(file_name) = file else {
        eprintln!("usage: parse_cli <file> | --preflight | --host-info");
        eprintln!("  [--fast] [--suggested] [--full] [--output-dir DIR] [--summary] ...");
        std::process::exit(1);
    };

    let path = Path::new(&file_name);
    if !path.exists() {
        eprintln!("File not found: {}", file_name);
        std::process::exit(1);
    }

    let detected = format_detector::detect_and_parse(path);
    let mut parse_result = detected.parse;
    eprintln!("parsed pings: {}", parse_result.pings.len());
    eprintln!("format: {}", detected.format);

    if let Some(tier) = settings_tier {
        let out_dir = options.output_dir.clone();
        let out_path = out_dir.as_deref().map(Path::new);
        let survey = SonarSurveyHint {
            ping_count: parse_result.pings.len(),
            format: detected.format.to_string(),
            hardware: None,
        };
        let suggested = host_profile::suggest_settings(tier, &survey, out_path);
        for note in &suggested.notes {
            eprintln!("[settings] {note}");
        }
        options = suggested.options;
        if options.output_dir.is_none() {
            if let Some(d) = out_path.and_then(|p| p.parent()) {
                options.output_dir = Some(d.display().to_string());
            }
        }
    }

    let output_summary = if !parse_result.pings.is_empty() {
        match build_outputs(path, &parse_result, &options, None, None) {
            Ok(summary) => Some(summary),
            Err(e) => {
                eprintln!("Output pipeline error: {:#}", e);
                None
            }
        }
    } else {
        None
    };

    let ping_count = parse_result.pings.len();

    if summary_only {
        parse_result.pings.clear();
    } else if let Some(n) = first_n {
        parse_result.pings.truncate(n);
        for (i, p) in parse_result.pings.iter().enumerate() {
            eprintln!(
                "PING {i}: ch={} seq={} t_ms={} depth_m={:.2} depth_ft={:.2} samples={} lat={} lon={}",
                p.channel,
                p.sequence,
                p.timestamp_ms,
                p.depth_m,
                p.depth_ft,
                p.sample_count,
                p.latitude,
                p.longitude,
            );
        }
    }

    let output = serde_json::json!({
        "input_file": file_name,
        "format": detected.format.to_string(),
        "record_count": parse_result.record_count,
        "ping_count": ping_count,
        "channels": parse_result.channels,
        "host": host_profile::probe_host(),
        "outputs": output_summary,
    });

    println!("{}", serde_json::to_string_pretty(&output).unwrap_or_else(|_| "{}".to_string()));
}
