use clap::Parser;
use gstreamer::prelude::*;
use std::io::{self, Read};
use std::process::exit;

#[derive(Parser)]
struct Args {
    #[clap(long)]
    width: u32,
    #[clap(long)]
    height: u32,
    #[clap(long, default_value = "30")]
    fps: u32,
    #[clap(long, default_value = "output.mp4")]
    output: String,
    #[clap(long)]
    encoder: Option<String>,
    /// Path to a directory of image frames (PNG/JPG). If set, images in the directory will be
    /// read (sorted) and pushed to the pipeline instead of reading raw frames from stdin.
    #[clap(long, default_value = "")]
    input_dir: String,
    /// Optional glob-like pattern (not fully supported, just kept for future use)
    #[clap(long, default_value = "frame_%06d.png")]
    input_pattern: String,
}

fn find_encoder(name_opt: &Option<String>) -> Option<String> {
    let candidates = if let Some(name) = name_opt {
        vec![name.clone()]
    } else {
        // preference list: NVIDIA, VAAPI/Intel, Apple, AMD, software
        vec![
            "nvh264enc".to_string(),
            "nvv4l2h264enc".to_string(),
            "vaapih264enc".to_string(),
            "msdkh264enc".to_string(),
            "vtenc_h264".to_string(),
            "amdh264enc".to_string(),
            "x264enc".to_string(),
            "avenc_h264".to_string(),
        ]
    };

    for c in candidates {
        if gstreamer::ElementFactory::find(&c).is_some() {
            return Some(c);
        }
    }
    None
}

fn main() {
    let args = Args::parse();
    gstreamer::init().expect("Failed to init GStreamer");

    let enc_name = match find_encoder(&args.encoder) {
        Some(n) => n,
        None => {
            eprintln!("No suitable encoder element found on this system.");
            exit(2);
        }
    };
    eprintln!("Using encoder: {}", enc_name);

    // Build pipeline: appsrc name=src ! videoconvert ! encoder [parse?] ! queue ! mp4mux ! filesink location=...
    // Insert a parser element for h264/h265 encoders when necessary (e.g., nvh264enc needs h264parse before mp4mux)
    let parse_elem = if enc_name.to_lowercase().contains("h264") || enc_name.to_lowercase().contains("264") {
        "! h264parse"
    } else if enc_name.to_lowercase().contains("h265") || enc_name.to_lowercase().contains("hevc") {
        "! h265parse"
    } else {
        ""
    };

    if !parse_elem.is_empty() {
        eprintln!("Inserting parser element ({}) for encoder {}", parse_elem, enc_name);
    }

    let pipeline_str = format!(
        "appsrc name=src is-live=true block=true format=time caps=video/x-raw,format=RGB,width={w},height={h},framerate={fps}/1 ! videoconvert ! {enc} {parse} ! queue ! mp4mux ! filesink location={out}",
        w = args.width,
        h = args.height,
        fps = args.fps,
        enc = enc_name,
        parse = parse_elem,
        out = args.output
    );

    eprintln!("Pipeline: {}", pipeline_str);

    let pipeline = gstreamer::parse_launch(&pipeline_str).expect("Failed to create pipeline");
    let pipeline = pipeline
        .downcast::<gstreamer::Pipeline>()
        .expect("Not a pipeline");

    // Retrieve appsrc
    let appsrc = pipeline
        .by_name("src")
        .expect("appsrc not present")
        .downcast::<gstreamer_app::AppSrc>()
        .expect("Failed to cast to AppSrc");

    // Set caps explicitly including width/height/framerate so downstream elements can negotiate
    let caps = gstreamer::Caps::builder("video/x-raw")
        .field("format", &"RGB")
        .field("width", &(args.width as i32))
        .field("height", &(args.height as i32))
        .field("framerate", &gstreamer::Fraction::new(args.fps as i32, 1))
        .build();
    appsrc.set_caps(Some(&caps));
    appsrc.set_max_bytes(0);

    pipeline
        .set_state(gstreamer::State::Playing)
        .expect("Unable to set pipeline to Playing");

    // If input_dir is provided, read images from disk and push them into appsrc
    if !args.input_dir.is_empty() {
        use std::fs;
        use image::io::Reader as ImageReader;
        let mut frame_idx: u64 = 0;
        let pattern = args.input_pattern.clone();
        let dir = args.input_dir.clone();
        // Expand pattern: if pattern contains %d-like pattern we'll find files that match frame_*.png
        let mut files: Vec<String> = fs::read_dir(&dir)
            .unwrap()
            .filter_map(|e| e.ok())
            .map(|e| e.path().to_string_lossy().to_string())
            .collect();
        files.sort();
        for fpath in files {
            if !fpath.to_lowercase().ends_with(".png") && !fpath.to_lowercase().ends_with(".jpg") && !fpath.to_lowercase().ends_with(".jpeg") {
                continue;
            }
            match ImageReader::open(&fpath) {
                Ok(reader) => match reader.decode() {
                    Ok(img) => {
                        let rgb = img.to_rgb8();
                        let raw = rgb.into_raw();
                        let mut gst_buf = gstreamer::Buffer::from_mut_slice(raw);
                        {
                            let buf = gst_buf.get_mut().unwrap();
                            let pts = (frame_idx * 1_000_000_000u64) / (args.fps as u64);
                            buf.set_pts(gstreamer::ClockTime::from_nseconds(pts as u64));
                            buf.set_duration(gstreamer::ClockTime::from_nseconds((1_000_000_000u64) / (args.fps as u64)));
                        }
                        let _ = appsrc.push_buffer(gst_buf);
                        frame_idx += 1;
                    }
                    Err(e) => {
                        eprintln!("Failed to decode {}: {:?}", fpath, e);
                    }
                },
                Err(e) => {
                    eprintln!("Failed to open {}: {:?}", fpath, e);
                }
            }
        }
        let _ = appsrc.end_of_stream();
    } else {
        // Read raw frames from stdin and push to appsrc
        let frame_size = (args.width * args.height * 3) as usize;
        let mut stdin = io::stdin();
        let mut frame_buf = vec![0u8; frame_size];
        let mut frame_idx: u64 = 0;

        loop {
            match stdin.read_exact(&mut frame_buf) {
                Ok(()) => {
                    let mut gst_buf = gstreamer::Buffer::from_mut_slice(frame_buf.clone());
                    {
                        let buf = gst_buf.get_mut().unwrap();
                        let pts = (frame_idx * 1_000_000_000u64) / (args.fps as u64);
                        buf.set_pts(gstreamer::ClockTime::from_nseconds(pts as u64));
                        buf.set_duration(gstreamer::ClockTime::from_nseconds((1_000_000_000u64) / (args.fps as u64)));
                    }
                    let _ = appsrc.push_buffer(gst_buf);
                    frame_idx += 1;
                }
                Err(e) => {
                    // EOF or error - send EOS
                    eprintln!("Finished reading frames or error: {:?}", e);
                    let _ = appsrc.end_of_stream();
                    break;
                }
            }
        }
    }

    // Wait for EOS on the bus
    let bus = pipeline.bus().unwrap();
    for msg in bus.iter_timed(gstreamer::ClockTime::NONE) {
        use gstreamer::MessageView;
        match msg.view() {
            MessageView::Eos(_) => {
                eprintln!("Pipeline reached EOS");
                break;
            }
            MessageView::Error(err) => {
                eprintln!("Error from {:?}: {} ({:?})", err.src().map(|s| s.path_string()), err.error(), err.debug());
                pipeline.set_state(gstreamer::State::Null).ok();
                exit(1);
            }
            _ => {}
        }
    }

    pipeline.set_state(gstreamer::State::Null).ok();
    eprintln!("Encoding finished, written to {}", args.output);
}
