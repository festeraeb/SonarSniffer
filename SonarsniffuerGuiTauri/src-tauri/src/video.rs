use crate::garmin_rsd_parser::ParseResult;
use serde::Serialize;
use std::path::Path;

#[derive(Debug, Clone, Serialize)]
pub struct VideoExportResult {
    pub enabled: bool,
    pub status: String,
    pub output_path: Option<String>,
}

// ── Feature-disabled stub ─────────────────────────────────────────────────────

#[cfg(not(feature = "video-gstreamer"))]
pub fn run_video_export(_parsed: &ParseResult, _output_dir: &Path) -> VideoExportResult {
    VideoExportResult {
        enabled: false,
        status: "Video export requires the video-gstreamer feature. \
                 Rebuild with --features video-gstreamer after installing the GStreamer MSVC runtime."
            .to_string(),
        output_path: None,
    }
}

// ── GStreamer implementation ───────────────────────────────────────────────────

#[cfg(feature = "video-gstreamer")]
pub fn run_video_export(parsed: &ParseResult, output_dir: &Path) -> VideoExportResult {
    match export_inner(parsed, output_dir) {
        Ok(r) => r,
        Err(e) => VideoExportResult {
            enabled: true,
            status: format!("Video export failed: {e:#}"),
            output_path: None,
        },
    }
}

#[cfg(feature = "video-gstreamer")]
fn export_inner(
    parsed: &ParseResult,
    output_dir: &Path,
) -> anyhow::Result<VideoExportResult> {
    use anyhow::Context as _;
    use gstreamer as gst;
    use gstreamer::prelude::*;
    use gstreamer_app as gst_app;
    use std::collections::HashMap;

    // Frame geometry
    const VIDEO_H: u32 = 64; // pings rendered per video frame (rows)
    const FPS: u32 = 10;

    gst::init().context("GStreamer init")?;

    // ── Select the channel with the most pings ────────────────────────────────
    let mut by_channel: HashMap<u32, Vec<usize>> = HashMap::new();
    for (i, ping) in parsed.pings.iter().enumerate() {
        by_channel.entry(ping.channel).or_default().push(i);
    }
    let (primary_ch, ping_indices) = by_channel
        .into_iter()
        .max_by_key(|(_, v)| v.len())
        .context("No pings found in ParseResult")?;

    let total_pings = ping_indices.len();

    // ── Compute video width from the actual sample data ───────────────────────
    let max_samples = ping_indices
        .iter()
        .map(|&i| parsed.pings[i].samples.len())
        .max()
        .unwrap_or(512)
        .max(64);
    // Round up to nearest 16 (encoder alignment) and cap at 1920
    let video_w = ((max_samples as u32).min(1920) + 15) & !15u32;

    let n_frames = (total_pings + VIDEO_H as usize - 1) / VIDEO_H as usize;
    let n_frames = n_frames.max(1);
    let frame_size = (video_w * VIDEO_H) as usize;
    let frame_ns = 1_000_000_000u64 / FPS as u64;

    // ── Output path ───────────────────────────────────────────────────────────
    let mp4_path = output_dir.join("sonar_waterfall.mp4");
    // GStreamer filesink on Windows accepts forward-slash paths
    let mp4_location = mp4_path.to_string_lossy().replace('\\', "/");

    // ── Build pipeline ────────────────────────────────────────────────────────
    // appsrc provides raw GRAY8 frames → x264enc (H.264) → mp4mux → file
    // Requires: gst-plugins-ugly (x264enc) + gst-plugins-good (mp4mux)
    let pipeline_str = "appsrc name=src \
        ! videoconvert \
        ! x264enc speed-preset=ultrafast tune=zerolatency \
        ! mp4mux \
        ! filesink name=fsink sync=false";

    let element = gst::parse::launch(pipeline_str).map_err(|e| {
        anyhow::anyhow!(
            "Pipeline parse failed: {e}. \
             Ensure gst-plugins-ugly (x264enc) and gst-plugins-good (mp4mux) are installed."
        )
    })?;

    let pipeline = element
        .dynamic_cast::<gst::Pipeline>()
        .map_err(|_| anyhow::anyhow!("Parsed element is not a GstPipeline"))?;

    // Set output file location on filesink
    pipeline
        .by_name("fsink")
        .context("filesink element not found")?
        .set_property("location", mp4_location.as_str());

    // Configure appsrc
    let appsrc = pipeline
        .by_name("src")
        .context("appsrc element not found")?
        .dynamic_cast::<gst_app::AppSrc>()
        .map_err(|_| anyhow::anyhow!("src element is not an AppSrc"))?;

    let caps = gst::Caps::builder("video/x-raw")
        .field("format", "GRAY8")
        .field("width", video_w as i32)
        .field("height", VIDEO_H as i32)
        .field("framerate", gst::Fraction::new(FPS as i32, 1))
        .build();
    appsrc.set_caps(Some(&caps));
    appsrc.set_property("format", gst::Format::Time);
    appsrc.set_property("is-live", false);
    appsrc.set_property("block", true);

    // ── Start pipeline ────────────────────────────────────────────────────────
    pipeline
        .set_state(gst::State::Playing)
        .map_err(|e| anyhow::anyhow!("set_state(Playing) failed: {e:?}"))?;

    // ── Push frames ───────────────────────────────────────────────────────────
    for frame_idx in 0..n_frames {
        let row_start = frame_idx * VIDEO_H as usize;
        let row_end = (row_start + VIDEO_H as usize).min(total_pings);

        // Render GRAY8 pixels: each ping → one row
        let mut raw = vec![0u8; frame_size];
        for (row_offset, &ping_i) in ping_indices[row_start..row_end].iter().enumerate() {
            let ping = &parsed.pings[ping_i];
            if ping.samples.is_empty() {
                continue;
            }
            let max = ping.samples.iter().copied().max().unwrap_or(1).max(1) as f32;
            for col in 0..video_w as usize {
                let sample_idx = (col * ping.samples.len()) / video_w as usize;
                let norm = ping.samples[sample_idx] as f32 / max;
                raw[row_offset * video_w as usize + col] = (norm * 255.0) as u8;
            }
        }

        // Wrap in a GstBuffer with timestamp + duration
        let mut buf = gst::Buffer::with_size(frame_size)
            .map_err(|_| anyhow::anyhow!("GstBuffer allocation failed (size={frame_size})"))?;
        {
            let buf_ref = buf.get_mut().unwrap();
            buf_ref.set_pts(gst::ClockTime::from_nseconds(frame_idx as u64 * frame_ns));
            buf_ref.set_duration(gst::ClockTime::from_nseconds(frame_ns));
            let mut map = buf_ref
                .map_writable()
                .map_err(|_| anyhow::anyhow!("GstBuffer map_writable failed"))?;
            let slice: &mut [u8] = &mut map;
            slice.copy_from_slice(&raw);
        }

        // push_buffer returns Err on Flushing/Eos → stop early
        if appsrc.push_buffer(buf).is_err() {
            break;
        }
    }

    // Signal end-of-stream
    let _ = appsrc.end_of_stream();

    // ── Wait for EOS (up to 5 minutes) ────────────────────────────────────────
    let bus = pipeline.bus().context("Pipeline has no message bus")?;
    let export_ok = loop {
        match bus.timed_pop(gst::ClockTime::from_seconds(300)) {
            Some(msg) => match msg.view() {
                gst::MessageView::Eos(..) => break true,
                gst::MessageView::Error(err) => {
                    pipeline.set_state(gst::State::Null).ok();
                    return Err(anyhow::anyhow!(
                        "GStreamer pipeline error: {} — {}",
                        err.error(),
                        err.debug().unwrap_or_default()
                    ));
                }
                _ => {}
            },
            None => {
                // timed_pop timeout (5 min elapsed)
                pipeline.set_state(gst::State::Null).ok();
                return Ok(VideoExportResult {
                    enabled: true,
                    status: "Video export timed out — partial file may exist".to_string(),
                    output_path: None,
                });
            }
        }
    };

    pipeline.set_state(gst::State::Null).ok();

    if !export_ok {
        return Ok(VideoExportResult {
            enabled: true,
            status: "Video export ended without EOS confirmation".to_string(),
            output_path: None,
        });
    }

    let file_mb = std::fs::metadata(&mp4_path)
        .map(|m| m.len() as f64 / 1_048_576.0)
        .unwrap_or(0.0);

    Ok(VideoExportResult {
        enabled: true,
        status: format!(
            "{n_frames} frames · {total_pings} pings · ch{primary_ch} · \
             {video_w}×{VIDEO_H} @ {FPS}fps → {} ({file_mb:.1} MB)",
            mp4_path.display()
        ),
        output_path: Some(mp4_path.display().to_string()),
    })
}

