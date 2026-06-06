//! Video encoding from processed frames.
//!
//! Supports two backends:
//! - **GStreamer** (feature: video-gstreamer): MP4/H.264 output
//! - **GIF fallback** (no feature): Animated GIF

use crate::video_enhanced::{statistics::DatasetStatistics, EnhancedVideoResult, ProcessedFrame, ProcessingStats, SonarProcessingParams};
use std::path::Path;

#[cfg(feature = "video-gstreamer")]
pub fn encode_to_video<F>(
    frames: Vec<ProcessedFrame>,
    output_dir: &Path,
    params: &SonarProcessingParams,
    stats: &DatasetStatistics,
    on_progress: F,
) -> anyhow::Result<EnhancedVideoResult>
where
    F: Fn(u32, u32) + Send + 'static,
{
    use anyhow::Context;
    use gstreamer as gst;
    use gstreamer::prelude::*;
    use gstreamer_app as gst_app;
    
    if frames.is_empty() {
        return Ok(EnhancedVideoResult {
            success: false,
            output_path: None,
            status: "No frames to encode".to_string(),
            processing_stats: None,
        });
    }
    
    gst::init().context("GStreamer initialization failed")?;
    
    let width = frames[0].width;
    let height = frames[0].height;
    let n_frames = frames.len() as u32;
    let fps = params.fps;
    let frame_ns = 1_000_000_000u64 / fps as u64;
    
    // Output path
    let mp4_path = output_dir.join("sonar_waterfall_enhanced.mp4");
    let mp4_location = mp4_path.to_string_lossy().replace('\\', "/");
    
    // Select encoder (prefer hardware if requested)
    let encoder = if params.prefer_hardware_encoding {
        // Try NVENC first, fall back to x264
        "nvh264enc"
    } else {
        "x264enc speed-preset=ultrafast tune=zerolatency"
    };
    
    // Build pipeline
    let pipeline_str = format!(
        "appsrc name=src \
        ! videoconvert \
        ! {encoder} \
        ! mp4mux \
        ! filesink name=fsink sync=false"
    );
    
    let element = {
        let primary = gst::parse::launch(&pipeline_str);
        match primary {
            Ok(elem) => Ok(elem),
            Err(e) if params.prefer_hardware_encoding => {
                // NVENC failed — retry with software x264enc
                let fallback_str = format!(
                    "appsrc name=src \
                    ! videoconvert \
                    ! x264enc speed-preset=ultrafast tune=zerolatency \
                    ! mp4mux \
                    ! filesink name=fsink sync=false"
                );
                gst::parse::launch(&fallback_str).map_err(|_| e)
            }
            Err(e) => Err(e),
        }
    }
    .map_err(|e| anyhow::anyhow!("Pipeline parse failed: {e}"))?;
    
    let pipeline = element
        .dynamic_cast::<gst::Pipeline>()
        .map_err(|_| anyhow::anyhow!("Not a pipeline"))?;
    
    // Configure filesink
    pipeline
        .by_name("fsink")
        .context("filesink not found")?
        .set_property("location", mp4_location.as_str());
    
    // Configure appsrc
    let appsrc = pipeline
        .by_name("src")
        .context("appsrc not found")?
        .dynamic_cast::<gst_app::AppSrc>()
        .map_err(|_| anyhow::anyhow!("src not an AppSrc"))?;
    
    let caps = gst::Caps::builder("video/x-raw")
        .field("format", "RGB")
        .field("width", width as i32)
        .field("height", height as i32)
        .field("framerate", gst::Fraction::new(fps as i32, 1))
        .build();
    appsrc.set_caps(Some(&caps));
    appsrc.set_property("format", gst::Format::Time);
    appsrc.set_property("is-live", false);
    appsrc.set_property("block", true);
    
    // Start pipeline
    pipeline
        .set_state(gst::State::Playing)
        .map_err(|e| anyhow::anyhow!("set_state(Playing) failed: {e:?}"))?;
    
    // Push frames
    for (i, frame) in frames.iter().enumerate() {
        let frame_size = frame.pixels.len();
        let mut buf = gst::Buffer::with_size(frame_size)
            .map_err(|_| anyhow::anyhow!("Buffer allocation failed"))?;
        
        {
            let buf_ref = buf.get_mut().unwrap();
            buf_ref.set_pts(gst::ClockTime::from_nseconds(i as u64 * frame_ns));
            buf_ref.set_duration(gst::ClockTime::from_nseconds(frame_ns));
            
            let mut map = buf_ref
                .map_writable()
                .map_err(|_| anyhow::anyhow!("Buffer map failed"))?;
            map.copy_from_slice(&frame.pixels);
        }
        
        if appsrc.push_buffer(buf).is_err() {
            break;
        }
        on_progress((i + 1) as u32, n_frames);
    }
    
    let _ = appsrc.end_of_stream();
    
    // Wait for EOS
    let bus = pipeline.bus().context("No bus")?;
    let export_ok = loop {
        match bus.timed_pop(gst::ClockTime::from_seconds(300)) {
            Some(msg) => match msg.view() {
                gst::MessageView::Eos(..) => break true,
                gst::MessageView::Error(err) => {
                    pipeline.set_state(gst::State::Null).ok();
                    anyhow::bail!("GStreamer error: {} — {}", err.error(), err.debug().unwrap_or_default());
                }
                _ => {}
            },
            None => {
                pipeline.set_state(gst::State::Null).ok();
                return Ok(EnhancedVideoResult {
                    success: false,
                    output_path: None,
                    status: "Video encoding timed out".to_string(),
                    processing_stats: None,
                });
            }
        }
    };
    
    pipeline.set_state(gst::State::Null).ok();
    
    if !export_ok {
        return Ok(EnhancedVideoResult {
            success: false,
            output_path: None,
            status: "Video encoding failed".to_string(),
            processing_stats: None,
        });
    }
    
    let file_mb = std::fs::metadata(&mp4_path)
        .map(|m| m.len() as f64 / 1_048_576.0)
        .unwrap_or(0.0);

    let gap_count = stats.gaps.len();
    let histogram_total: u32 = stats.histogram.iter().copied().sum();
    let percentile_span = (stats.percentile_ceiling - stats.percentile_floor).max(1.0);
    let processed_mean = ((stats.raw_mean - stats.percentile_floor) / percentile_span).clamp(0.0, 1.0);
    
    Ok(EnhancedVideoResult {
        success: true,
        output_path: Some(mp4_path.display().to_string()),
        status: format!(
            "Enhanced video export complete: {} frames, {}x{} @ {}fps ({:.1} MB), gaps={}, stdev={:.1}, histogram_samples={}",
            n_frames, width, height, fps, file_mb, gap_count, stats.raw_stddev, histogram_total
        ),
        processing_stats: Some(ProcessingStats {
            total_pings: stats.total_pings,
            frames_generated: n_frames,
            primary_channel: stats.primary_channel,
            video_width: width,
            video_height: height,
            fps,
            duration_secs: n_frames as f32 / fps as f32,
            file_size_mb: file_mb,
            raw_min: stats.raw_min,
            raw_max: stats.raw_max,
            raw_mean: stats.raw_mean,
            processed_min: 0.0,
            processed_max: 1.0,
            processed_mean,
            tvg_applied: true,
            log_compression_applied: true,
            filtering_applied: true,
            histogram_eq_applied: true,
            clahe_applied: false,
        }),
    })
}

#[cfg(not(feature = "video-gstreamer"))]
pub fn encode_to_video<F>(
    frames: Vec<ProcessedFrame>,
    output_dir: &Path,
    params: &SonarProcessingParams,
    stats: &DatasetStatistics,
    on_progress: F,
) -> anyhow::Result<EnhancedVideoResult>
where
    F: Fn(u32, u32) + Send + 'static,
{
    // Pure-Rust AV1 (rav1e) → hand-written MP4 muxer. No system libs, no NASM,
    // no pkg-config — the default build path that never flakes CI. Output is a
    // standards-compliant .mp4 that plays in browsers, VLC, mpv, and the
    // Tauri desktop webview.
    use crate::mp4_av1::{write_mp4, Av1Packet};
    use rav1e::prelude::*;

    if frames.is_empty() {
        return Ok(EnhancedVideoResult {
            success: false,
            output_path: None,
            status: "No frames to encode".to_string(),
            processing_stats: None,
        });
    }

    let width = frames[0].width as usize;
    let height = frames[0].height as usize;
    let n_frames = frames.len() as u32;
    let fps = params.fps.max(1);

    // rav1e encoder config: 8-bit 4:2:0, speed preset tuned for snappy encode of
    // low-motion sonar waterfall content. Keyframe interval keeps seeking fast.
    let enc = EncoderConfig {
        width,
        height,
        time_base: Rational { num: 1, den: fps as u64 },
        bit_depth: 8,
        chroma_sampling: ChromaSampling::Cs420,
        speed_settings: SpeedSettings::from_preset(9),
        min_key_frame_interval: 12,
        max_key_frame_interval: 120,
        low_latency: true,
        ..Default::default()
    };
    let cfg = Config::new().with_encoder_config(enc);
    let mut ctx: Context<u8> = cfg
        .new_context()
        .map_err(|e| anyhow::anyhow!("rav1e context init failed: {e:?}"))?;

    let chroma_w = width.div_ceil(2);
    let chroma_h = height.div_ceil(2);

    // Feed frames: RGB → BT.601 YUV420 planar.
    for (i, frame) in frames.iter().enumerate() {
        let mut f = ctx.new_frame();
        rgb_to_yuv420_into(&frame.pixels, width, height, chroma_w, chroma_h, &mut f);
        ctx.send_frame(f)
            .map_err(|e| anyhow::anyhow!("rav1e send_frame failed: {e:?}"))?;
        on_progress((i + 1) as u32, n_frames);
    }
    ctx.flush();

    // Drain encoded packets.
    let mut packets: Vec<Av1Packet> = Vec::with_capacity(frames.len());
    loop {
        match ctx.receive_packet() {
            Ok(pkt) => {
                let is_key = matches!(pkt.frame_type, FrameType::KEY);
                packets.push(Av1Packet { data: pkt.data, is_key });
            }
            Err(EncoderStatus::Encoded) => continue,
            Err(EncoderStatus::LimitReached) => break,
            Err(EncoderStatus::NeedMoreData) => break,
            Err(e) => return Err(anyhow::anyhow!("rav1e receive_packet failed: {e:?}")),
        }
    }

    if packets.is_empty() {
        return Ok(EnhancedVideoResult {
            success: false,
            output_path: None,
            status: "AV1 encoder produced no packets".to_string(),
            processing_stats: None,
        });
    }

    let mp4_path = output_dir.join("sonar_waterfall.mp4");
    let mut file = std::fs::File::create(&mp4_path)?;
    // seq_level_idx 8 (≈ level 4.0) covers typical waterfall sizes safely.
    write_mp4(&mut file, &packets, width as u32, height as u32, fps, 8)?;
    {
        use std::io::Write as _;
        file.flush()?;
    }
    drop(file);

    let file_mb = std::fs::metadata(&mp4_path)
        .map(|m| m.len() as f64 / 1_048_576.0)
        .unwrap_or(0.0);

    let gap_count = stats.gaps.len();
    let histogram_total: u32 = stats.histogram.iter().copied().sum();
    let percentile_span = (stats.percentile_ceiling - stats.percentile_floor).max(1.0);
    let processed_mean =
        ((stats.raw_mean - stats.percentile_floor) / percentile_span).clamp(0.0, 1.0);

    Ok(EnhancedVideoResult {
        success: true,
        output_path: Some(mp4_path.display().to_string()),
        status: format!(
            "Pure-Rust AV1/MP4 export complete: {} frames, {}x{} @ {}fps ({:.1} MB), gaps={}, stdev={:.1}, histogram_samples={}",
            n_frames, width, height, fps, file_mb, gap_count, stats.raw_stddev, histogram_total
        ),
        processing_stats: Some(ProcessingStats {
            total_pings: stats.total_pings,
            frames_generated: n_frames,
            primary_channel: stats.primary_channel,
            video_width: width as u32,
            video_height: height as u32,
            fps,
            duration_secs: n_frames as f32 / fps as f32,
            file_size_mb: file_mb,
            raw_min: stats.raw_min,
            raw_max: stats.raw_max,
            raw_mean: stats.raw_mean,
            processed_min: 0.0,
            processed_max: 1.0,
            processed_mean,
            tvg_applied: true,
            log_compression_applied: true,
            filtering_applied: true,
            histogram_eq_applied: true,
            clahe_applied: false,
        }),
    })
}

/// Convert an RGB8 frame to BT.601 limited-range YUV420 planar, writing directly
/// into a rav1e frame's three planes.
#[cfg(not(feature = "video-gstreamer"))]
fn rgb_to_yuv420_into(
    rgb: &[u8],
    width: usize,
    height: usize,
    chroma_w: usize,
    chroma_h: usize,
    frame: &mut rav1e::prelude::Frame<u8>,
) {
    // Y plane (full res).
    {
        let y_plane = &mut frame.planes[0];
        let mut rows = y_plane.mut_slice(Default::default());
        let mut rows_iter = rows.rows_iter_mut();
        for y in 0..height {
            let row = rows_iter.next().unwrap();
            for x in 0..width {
                let idx = (y * width + x) * 3;
                let r = rgb[idx] as f32;
                let g = rgb[idx + 1] as f32;
                let b = rgb[idx + 2] as f32;
                // BT.601 luma, limited range (16..235).
                let yv = 16.0 + (0.257 * r + 0.504 * g + 0.098 * b);
                row[x] = yv.clamp(16.0, 235.0) as u8;
            }
        }
    }
    // U and V planes (quarter res, 2x2 average).
    // Build U then V separately to satisfy the borrow checker.
    for plane_idx in 1..=2usize {
        let p = &mut frame.planes[plane_idx];
        let mut rows = p.mut_slice(Default::default());
        let mut rows_iter = rows.rows_iter_mut();
        for cy in 0..chroma_h {
            let row = rows_iter.next().unwrap();
            for cx in 0..chroma_w {
                // 2x2 source block.
                let mut acc = 0.0f32;
                let mut cnt = 0.0f32;
                for dy in 0..2 {
                    for dx in 0..2 {
                        let sx = cx * 2 + dx;
                        let sy = cy * 2 + dy;
                        if sx < width && sy < height {
                            let idx = (sy * width + sx) * 3;
                            let r = rgb[idx] as f32;
                            let g = rgb[idx + 1] as f32;
                            let b = rgb[idx + 2] as f32;
                            let v = if plane_idx == 1 {
                                // Cb
                                128.0 + (-0.148 * r - 0.291 * g + 0.439 * b)
                            } else {
                                // Cr
                                128.0 + (0.439 * r - 0.368 * g - 0.071 * b)
                            };
                            acc += v;
                            cnt += 1.0;
                        }
                    }
                }
                let val = if cnt > 0.0 { acc / cnt } else { 128.0 };
                row[cx] = val.clamp(16.0, 240.0) as u8;
            }
        }
    }
}
