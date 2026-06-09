//! Scrolling waterfall timeline — new pings enter at the bottom, fill the viewport,
//! then scroll upward (top row drops off as each new row arrives).

use crate::garmin_rsd_parser::Ping;

/// How fast the waterfall scrolls relative to survey time.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VideoSpeedMode {
    /// Fixed readable rate (~2 pings/s) for study and review.
    Readable,
    /// Match average survey ping rate from timestamps (capped for sanity).
    Survey,
}

impl VideoSpeedMode {
    pub fn from_option(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "survey" | "boat" | "realtime" | "real_time" => Self::Survey,
            _ => Self::Readable,
        }
    }
}

/// Per-frame end ping index (inclusive) for the scrolling window.
#[derive(Debug, Clone)]
pub struct ScrollTimeline {
    pub fps: u32,
    /// Last ping row shown in each frame (inclusive, 0-based).
    pub end_ping_indices: Vec<usize>,
    pub display_pings_per_second: f64,
}

/// Build a timeline: one advancing ping window per frame at a digestible speed.
pub fn build_scroll_timeline(
    num_pings: usize,
    pings: &[Ping],
    speed_mode: VideoSpeedMode,
    readable_pings_per_sec: f32,
    target_fps: u32,
) -> ScrollTimeline {
    let fps = target_fps.max(1).min(60);
    let readable_pps = readable_pings_per_sec.clamp(0.25, 30.0) as f64;

    let survey_pps = survey_pings_per_second(pings).unwrap_or(readable_pps);

    let display_pps = match speed_mode {
        VideoSpeedMode::Readable => readable_pps,
        VideoSpeedMode::Survey => survey_pps.clamp(0.25, 60.0),
    };

    let step = display_pps / fps as f64;
    let mut end_indices = Vec::new();
    if num_pings == 0 {
        return ScrollTimeline {
            fps,
            end_ping_indices: end_indices,
            display_pings_per_second: display_pps,
        };
    }

    let mut pos = 0.0f64;
    let last = num_pings - 1;
    while (pos as usize) < last {
        end_indices.push(pos as usize);
        pos += step;
    }
    if end_indices.last().copied() != Some(last) {
        end_indices.push(last);
    }

    ScrollTimeline {
        fps,
        end_ping_indices: end_indices,
        display_pings_per_second: display_pps,
    }
}

fn survey_pings_per_second(pings: &[Ping]) -> Option<f64> {
    if pings.len() < 2 {
        return None;
    }
    let mut by_ch: std::collections::HashMap<u32, Vec<u64>> = std::collections::HashMap::new();
    for p in pings {
        if p.timestamp_ms > 0 {
            by_ch.entry(p.channel).or_default().push(p.timestamp_ms);
        }
    }
    let (_ch, mut ts) = by_ch.into_iter().max_by_key(|(_, v)| v.len())?;
    if ts.len() < 2 {
        return None;
    }
    ts.sort_unstable();
    let span_ms = ts.last()? - ts.first()?;
    if span_ms == 0 {
        return None;
    }
    Some((ts.len() as f64 - 1.0) / (span_ms as f64 / 1000.0))
}

/// Inclusive data row range for a scrolling frame ending at `end_ping`.
pub fn scroll_window(end_ping: usize, viewport_height: usize) -> (usize, usize, usize) {
    let h = viewport_height.max(1);
    let end = end_ping.min(usize::MAX);
    let data_end = end + 1;
    let data_start = data_end.saturating_sub(h);
    let visible = data_end - data_start;
    let top_pad = h - visible;
    (data_start, data_end, top_pad)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scroll_window_fills_then_scrolls() {
        let (s, e, pad) = scroll_window(0, 1080);
        assert_eq!((s, e, pad), (0, 1, 1079));
        let (s, e, pad) = scroll_window(1079, 1080);
        assert_eq!((s, e, pad), (0, 1080, 0));
        let (s, e, pad) = scroll_window(2000, 1080);
        assert_eq!((s, e, pad), (921, 2001, 0));
    }

    #[test]
    fn readable_timeline_is_slow() {
        let tl = build_scroll_timeline(1000, &[], VideoSpeedMode::Readable, 2.0, 24);
        assert!(tl.end_ping_indices.len() > 100);
        assert!((tl.display_pings_per_second - 2.0).abs() < 0.01);
        assert_eq!(*tl.end_ping_indices.last().unwrap(), 999);
    }
}
