//! WASM / browser pipeline surface.
//!
//! `parse_rsd_bytes` accepts the raw bytes of a Garmin `.RSD` file (typically
//! from a `File.arrayBuffer()` in the browser) and returns:
//!
//! 1. A `ParseResult` (the same struct the native CLI uses, with all
//!    channel info, pings, healing actions, etc.).
//! 2. A `DiscoveryResult` (the channel-discovery output: profiles, side-scan
//!    pairs, composite scanlines).
//!
//! The full `Vec<Ping>` of sonar samples stays in WASM memory (we never
//! copy it across the JS/WASM boundary — only the per-ping metadata
//! crosses).  The browser UI can request ping windows on demand via
//! `get_ping_samples(channel, index)` to draw waterfall tiles.

use crate::channel_discovery;
use crate::format_detector;
use crate::garmin_rsd_parser::{GarminRSDParser, ParseResult, Ping};

/// One parsed recording, ready for the JS side.  The `pings` field is the
/// raw per-ping metadata; the samples themselves are *not* in this struct —
/// call `get_ping_samples` to fetch them (avoids a 100+ MB JSON copy).
#[derive(serde::Serialize)]
pub struct PipelineOutput {
    pub parse: ParseResult,
    pub discovery: channel_discovery::DiscoveryResult,
    /// Sanity-check ping count we found via discovery (must match
    /// `parse.record_count` modulo the `first_n` cap).
    pub discovery_ping_count: usize,
    /// First 8 detected channels summarised for quick UI rendering.
    pub channel_summary: Vec<ChannelSummary>,
    /// Truncated pings (capped at `MAX_PINGS_IN_JSON`) — the JS side
    /// uses these to draw the timeline / metadata.  The full sample
    /// vector lives only in the parser and is reachable via
    /// `get_ping_samples`.
    pub pings: Vec<PingMetadata>,
}

#[derive(serde::Serialize)]
pub struct ChannelSummary {
    pub channel: u32,
    pub archetype: String,
    pub spatial_role: String,
    pub frequency_tier: String,
    pub ping_count: usize,
    pub gps_ping_count: usize,
    pub median_sample_count: usize,
    pub archetype_confidence: f32,
    pub classification_reason: String,
    pub was_flipped: bool,
}

#[derive(serde::Serialize)]
pub struct PingMetadata {
    pub file_offset: usize,
    pub sequence: u32,
    pub timestamp_ms: u64,
    pub latitude: f64,
    pub longitude: f64,
    pub depth_m: f32,
    pub depth_ft: f32,
    pub altitude_m: f32,
    pub temp_c: Option<f32>,
    pub beam_angle_deg: f32,
    pub heading_deg: Option<f32>,
    pub pitch_deg: Option<f32>,
    pub roll_deg: Option<f32>,
    pub channel: u32,
    pub sample_count: usize,
    pub sample_format: String,
    /// `false` if the ping has GPS; `true` if the position is interpolated
    /// (heuristic: lat/lon is exactly 0).
    pub position_interpolated: bool,
}

/// Cap the number of pings shipped across the JS boundary as JSON.  Each
/// ping metadata is ~100 bytes; 50,000 pings → 5 MB JSON.  The full
/// sample vector stays in WASM memory and is requested per-ping.
pub const MAX_PINGS_IN_JSON: usize = 50_000;

/// Run the full parse + discovery pipeline on raw RSD bytes.  Returns
/// the JSON-friendly `PipelineOutput` plus the underlying `ParseResult`
/// (held in a `parking_lot::Mutex` cell keyed by the recording id so
/// follow-up `get_ping_samples` calls can reach the samples).
pub fn run_pipeline(bytes: Vec<u8>) -> PipelineOutput {
    let mut parser = GarminRSDParser::new();
    let parse = parser.parse_bytes(bytes, None);
    let discovery = channel_discovery::discover_and_profile(&parse);
    let discovery_ping_count = discovery
        .profiles
        .iter()
        .map(|p| p.ping_count)
        .sum();
    let channel_summary: Vec<ChannelSummary> = discovery
        .profiles
        .iter()
        .map(|p| ChannelSummary {
            channel: p.channel_id,
            archetype: format!("{:?}", p.archetype),
            spatial_role: format!("{:?}", p.spatial_role),
            frequency_tier: format!("{:?}", p.frequency_tier),
            ping_count: p.ping_count,
            gps_ping_count: p.gps_ping_count,
            median_sample_count: p.median_sample_count,
            archetype_confidence: p.archetype_confidence,
            classification_reason: p.classification_reason.clone(),
            was_flipped: p.was_flipped,
        })
        .collect();
    let pings: Vec<PingMetadata> = parse
        .pings
        .iter()
        .take(MAX_PINGS_IN_JSON)
        .map(ping_to_meta)
        .collect();
    PipelineOutput {
        parse,
        discovery,
        discovery_ping_count,
        channel_summary,
        pings,
    }
}

fn ping_to_meta(p: &Ping) -> PingMetadata {
    PingMetadata {
        file_offset: p.file_offset,
        sequence: p.sequence,
        timestamp_ms: p.timestamp_ms,
        latitude: p.latitude,
        longitude: p.longitude,
        depth_m: p.depth_m,
        depth_ft: p.depth_ft,
        altitude_m: p.altitude_m,
        temp_c: p.temp_c,
        beam_angle_deg: p.beam_angle_deg,
        heading_deg: p.heading_deg,
        pitch_deg: p.pitch_deg,
        roll_deg: p.roll_deg,
        channel: p.channel,
        sample_count: p.sample_count,
        sample_format: p.sample_format.clone(),
        position_interpolated: p.latitude == 0.0 && p.longitude == 0.0,
    }
}

/// Return a copy of the sonar samples for one ping.  Used by the
/// browser waterfall view to draw a tile.
pub fn get_ping_samples(
    parse: &ParseResult,
    channel: u32,
    index_in_channel: usize,
) -> Option<Vec<u16>> {
    let mut seen = 0usize;
    for p in &parse.pings {
        if p.channel != channel {
            continue;
        }
        if seen == index_in_channel {
            return Some(p.samples.clone());
        }
        seen += 1;
    }
    None
}

/// Re-export the format detection entry point so the WASM API can
/// sniff non-RSD inputs (returning a clear "not Garmin" error).
pub use format_detector::detect_and_parse_rsd_bytes;
