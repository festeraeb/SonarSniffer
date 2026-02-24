use std::env;

use tauri_appsonarsniffer_lib::{run_pipeline_internal, outputs::PipelineOptions};

fn main() {
    let mut args = env::args().skip(1);
    let mut file: Option<String> = None;

    let mut options = PipelineOptions::default();
    let mut summary_only = false;
    let mut first_n: Option<usize> = None;

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--light" => {
                options.video = false;
                options.mosaic = false;
                options.waterfall = false;
                options.mbtiles = false;
                options.kmz = false;
                options.arcgis = false;
                options.web_viewer = false;
            }
            "--no-video" => options.video = false,
            "--no-kml" => options.kml = false,
            "--no-kmz" => options.kmz = false,
            "--no-mbtiles" => options.mbtiles = false,
            "--no-mosaic" => options.mosaic = false,
            "--no-waterfall" => options.waterfall = false,
            "--no-arcgis" => options.arcgis = false,
            "--no-viewer" => options.web_viewer = false,
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

    let Some(file_name) = file else {
        eprintln!("usage: parse_cli <file> [--light] [--output-dir DIR] [--no-video] [--no-kml] [--no-kmz] [--no-mbtiles] [--no-mosaic] [--no-waterfall] [--no-arcgis] [--no-viewer] [--summary] [--first-n N]");
        std::process::exit(1);
    };

    let mut resp = run_pipeline_internal(&file_name, Some(options));

    if summary_only {
        resp.parse.pings.clear();
    } else if let Some(n) = first_n {
        resp.parse.pings.truncate(n);
    }

    println!("{}", serde_json::to_string_pretty(&resp).unwrap_or_else(|_| "<failed to serialize response>".to_string()));
}
