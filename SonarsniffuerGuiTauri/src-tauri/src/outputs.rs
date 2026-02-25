use crate::garmin_rsd_parser::{ParseResult, Ping};
use anyhow::{Context, Result};
use chrono::Utc;
use image::codecs::png::PngEncoder;
use image::{ColorType, GrayImage, ImageBuffer, ImageEncoder, Rgb, RgbImage};
use rusqlite::Connection;
use serde::Serialize;
use std::collections::BTreeMap;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use zip::write::SimpleFileOptions;

#[derive(Debug, Clone, Serialize)]
pub struct OutputArtifact {
    pub kind: String,
    pub path: String,
    pub details: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct OutputSummary {
    pub output_dir: String,
    pub artifacts: Vec<OutputArtifact>,
}

#[derive(Debug, Clone, Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PipelineOptions {
    pub output_dir: Option<String>,
    pub video: bool,
    pub kml: bool,
    pub kmz: bool,
    pub mbtiles: bool,
    pub mosaic: bool,
    pub waterfall: bool,
    pub arcgis: bool,
    pub web_viewer: bool,
    #[serde(default)]
    pub colormap: String,
}

impl Default for PipelineOptions {
    fn default() -> Self {
        Self {
            output_dir: None,
            video: true,
            kml: true,
            kmz: true,
            mbtiles: true,
            mosaic: true,
            waterfall: true,
            arcgis: true,
            web_viewer: true,
            colormap: "sonar".to_string(),
        }
    }
}

pub fn build_outputs(
    input_file: &Path,
    parsed: &ParseResult,
    options: &PipelineOptions,
) -> Result<OutputSummary> {
    let parent = input_file
        .parent()
        .map_or_else(|| PathBuf::from("."), Path::to_path_buf);

    let run_stamp = Utc::now().format("%Y%m%d_%H%M%S").to_string();
    let output_dir = options
        .output_dir
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| parent.join(format!("sniffer_output_{run_stamp}")));

    fs::create_dir_all(&output_dir)
        .with_context(|| format!("Failed to create output directory: {}", output_dir.display()))?;

    let mut artifacts = Vec::new();

    if options.waterfall {
        artifacts.extend(write_waterfall_per_channel(parsed, &output_dir)?);
    }

    if options.mosaic {
        artifacts.extend(write_mosaic_per_channel(parsed, &output_dir, &options.colormap)?);
    }

    if options.mbtiles {
        let path = output_dir.join("sonar.mbtiles");
        let n = pings_by_channel(parsed).values().map(|v| v.len()).max().unwrap_or(0);
        match write_mbtiles(parsed, &path, &options.colormap) {
            Ok(()) => artifacts.push(OutputArtifact {
                kind: "mbtiles".to_string(),
                path: path.display().to_string(),
                details: format!(
                    "MBTiles z0–z{} · {} pings · georeferenced bounds",
                    MBTILES_MAX_ZOOM, n
                ),
            }),
            Err(e) => artifacts.push(OutputArtifact {
                kind: "mbtiles".to_string(),
                path: path.display().to_string(),
                details: format!("ERROR: {e:#}"),
            }),
        }
    }

    if options.kml {
        let path = output_dir.join("track.kml");
        match write_kml(parsed, &path) {
            Ok(n) => artifacts.push(OutputArtifact {
                kind: "kml".to_string(),
                path: path.display().to_string(),
                details: format!(
                    "Trackline + {} depth placemarks · styled · LookAt camera",
                    n
                ),
            }),
            Err(e) => artifacts.push(OutputArtifact {
                kind: "kml".to_string(),
                path: path.display().to_string(),
                details: format!("ERROR: {e:#}"),
            }),
        }
    }

    if options.kmz {
        let kml = output_dir.join("track.kml");
        let kml_ready = kml.exists() || write_kml(parsed, &kml).is_ok();
        if kml_ready {
            let kmz = output_dir.join("track.kmz");
            match write_kmz(&kml, &kmz, parsed, &output_dir, &options.colormap) {
                Ok(has_overlay) => artifacts.push(OutputArtifact {
                    kind: "kmz".to_string(),
                    path: kmz.display().to_string(),
                    details: if has_overlay {
                        "KMZ with stitched sidescan GroundOverlay georeferenced to sonar swath".to_string()
                    } else {
                        "KMZ + trackline (no GPS bounding box — GroundOverlay skipped)".to_string()
                    },
                }),
                Err(e) => artifacts.push(OutputArtifact {
                    kind: "kmz".to_string(),
                    path: output_dir.join("track.kmz").display().to_string(),
                    details: format!("ERROR: {e:#}"),
                }),
            }
        } else {
            artifacts.push(OutputArtifact {
                kind: "kmz".to_string(),
                path: output_dir.join("track.kmz").display().to_string(),
                details: "Skipped — KML prerequisite failed".to_string(),
            });
        }
    }

    if options.arcgis {
        let path = output_dir.join("arcgis_layer.json");
        match write_arcgis_sidecar(parsed, &path) {
            Ok(()) => artifacts.push(OutputArtifact {
                kind: "arcgis".to_string(),
                path: path.display().to_string(),
                details: "ArcGIS EsriJSON FeatureCollection with all ping attributes".to_string(),
            }),
            Err(e) => artifacts.push(OutputArtifact {
                kind: "arcgis".to_string(),
                path: path.display().to_string(),
                details: format!("ERROR: {e:#}"),
            }),
        }
    }

    if options.web_viewer {
        let viewer_dir = output_dir.join("viewer");
        match write_native_viewer(parsed, &viewer_dir) {
            Ok(()) => artifacts.push(OutputArtifact {
                kind: "viewer".to_string(),
                path: viewer_dir.display().to_string(),
                details: "MapLibre viewer · track + depth-coloured ping layer · click popup".to_string(),
            }),
            Err(e) => artifacts.push(OutputArtifact {
                kind: "viewer".to_string(),
                path: viewer_dir.display().to_string(),
                details: format!("ERROR: {e:#}"),
            }),
        }
    }

    Ok(OutputSummary {
        output_dir: output_dir.display().to_string(),
        artifacts,
    })
}

// ── Colour palette system ────────────────────────────────────────────────────

/// Multi-stop linear interpolation between RGB colour stops.
fn lerp_colormap(n: f32, stops: &[(f32, [u8; 3])]) -> Rgb<u8> {
    let n = n.clamp(0.0, 1.0);
    for i in 1..stops.len() {
        let (t0, c0) = stops[i - 1];
        let (t1, c1) = stops[i];
        if n <= t1 || i == stops.len() - 1 {
            let t = if t1 > t0 { (n - t0) / (t1 - t0) } else { 1.0 };
            return Rgb([
                (c0[0] as f32 + (c1[0] as f32 - c0[0] as f32) * t).clamp(0.0, 255.0) as u8,
                (c0[1] as f32 + (c1[1] as f32 - c0[1] as f32) * t).clamp(0.0, 255.0) as u8,
                (c0[2] as f32 + (c1[2] as f32 - c0[2] as f32) * t).clamp(0.0, 255.0) as u8,
            ]);
        }
    }
    Rgb([255, 255, 240])
}

/// Map a normalised intensity `n ∈ [0,1]` to RGB using one of the named palettes.
/// Unknown names fall back to the `"sonar"` palette.
pub fn apply_colormap(n: f32, name: &str) -> Rgb<u8> {
    let nm = if name.is_empty() { "sonar" } else { name };
    match nm {
        "grayscale" => {
            let v = (n.clamp(0.0, 1.0) * 255.0) as u8;
            Rgb([v, v, v])
        }
        "ocean" => lerp_colormap(n, &[
            (0.00, [  0,   0,  80]),
            (0.30, [  0,  40, 120]),
            (0.55, [  0, 100, 160]),
            (0.75, [ 30, 180, 200]),
            (0.90, [160, 230, 240]),
            (1.00, [255, 255, 255]),
        ]),
        "inferno" => lerp_colormap(n, &[
            (0.00, [  0,   0,   4]),
            (0.20, [ 40,  11,  84]),
            (0.40, [101,  21, 110]),
            (0.60, [182,  55,  76]),
            (0.80, [237, 121,  18]),
            (1.00, [252, 255, 164]),
        ]),
        "iron" => lerp_colormap(n, &[
            (0.00, [  0,   0,   0]),
            (0.25, [  0,   0, 200]),
            (0.50, [160,   0, 200]),
            (0.75, [255, 160,   0]),
            (1.00, [255, 255, 200]),
        ]),
        "rainbow" => lerp_colormap(n, &[
            (0.00, [  0,   0, 255]),
            (0.25, [  0, 255, 255]),
            (0.50, [  0, 255,   0]),
            (0.75, [255, 255,   0]),
            (1.00, [255,   0,   0]),
        ]),
        "plasma" => lerp_colormap(n, &[
            (0.00, [ 13,   8, 135]),
            (0.25, [126,   3, 167]),
            (0.50, [204,  71, 120]),
            (0.75, [248, 149,  64]),
            (1.00, [240, 249,  33]),
        ]),
        _ => lerp_colormap(n, &[   // "sonar" (default & fallback)
            (0.00, [  0,   0,   0]),
            (0.15, [  0,   0, 210]),
            (0.35, [  0, 160, 255]),
            (0.55, [  0, 220,  80]),
            (0.70, [230, 200,   0]),
            (0.85, [255,  55,   0]),
            (1.00, [255, 255, 240]),
        ]),
    }
}

// ── Per-ping image helpers ────────────────────────────────────────────────────

/// Resample one sonar ping into a `dst_w`-wide grey byte row using:
/// * bilinear horizontal interpolation (handles variable sample counts)
/// * per-ping 2 %–98 % percentile contrast stretch
/// * gamma correction to lift shadow detail
fn ping_to_gray_row(ping: &Ping, dst_w: usize, gamma: f32) -> Vec<u8> {
    let mut row = vec![0u8; dst_w];
    let src = &ping.samples;
    if src.is_empty() || dst_w == 0 {
        return row;
    }
    // Collect non-zero samples for robust percentile estimation
    let mut nonzero: Vec<u16> = src.iter().copied().filter(|&x| x > 0).collect();
    if nonzero.is_empty() {
        return row;
    }
    nonzero.sort_unstable();
    let nz = nonzero.len();
    let p2  = nonzero[(nz / 50).min(nz - 1)] as f32;
    let p98 = nonzero[(nz * 49 / 50).min(nz - 1)] as f32;
    let span = (p98 - p2).max(1.0);

    let src_n = src.len();
    let inv = if dst_w <= 1 || src_n <= 1 {
        0.0_f32
    } else {
        (src_n - 1) as f32 / (dst_w - 1) as f32
    };
    for i in 0..dst_w {
        let flt  = i as f32 * inv;
        let lo   = flt as usize;
        let hi   = (lo + 1).min(src_n - 1);
        let frac = flt - lo as f32;
        let v    = src[lo] as f32 * (1.0 - frac) + src[hi] as f32 * frac;
        let norm = ((v - p2) / span).clamp(0.0, 1.0).powf(gamma);
        row[i]   = (norm * 255.0) as u8;
    }
    row
}

/// Canonical output width for a channel: median non-zero sample count clamped
/// to `max_w`.  The median avoids giant images from a handful of anomalous pings.
fn canonical_width(pings: &[&Ping], max_w: u32) -> u32 {
    let mut counts: Vec<usize> = pings
        .iter()
        .map(|p| p.samples.len())
        .filter(|&n| n > 0)
        .collect();
    if counts.is_empty() {
        return 512_u32.min(max_w).max(1);
    }
    counts.sort_unstable();
    (counts[counts.len() / 2] as u32).min(max_w).max(1)
}

/// Group pings by channel ID; preserves temporal ping ordering.
fn pings_by_channel(parsed: &ParseResult) -> BTreeMap<u32, Vec<&Ping>> {
    let mut map: BTreeMap<u32, Vec<&Ping>> = BTreeMap::new();
    for ping in &parsed.pings {
        map.entry(ping.channel).or_default().push(ping);
    }
    map
}

/// Render a channel's pings as a GRAY8 waterfall image.
/// Each ping occupies one output row (vertically subsampled for large files).
/// Uses bilinear horizontal resampling + per-ping 2–98 % percentile stretch + gamma.
fn render_gray(pings: &[&Ping], max_w: u32, max_h: u32) -> GrayImage {
    if pings.is_empty() {
        return ImageBuffer::from_pixel(1, 1, image::Luma([0u8]));
    }
    let img_w = canonical_width(pings, max_w);
    let src_h = pings.len();
    let img_h = (src_h as u32).min(max_h).max(1);
    let mut img: GrayImage = ImageBuffer::new(img_w, img_h);
    for dst_y in 0..img_h {
        let src_y = (dst_y as usize * src_h) / img_h as usize;
        let ping  = &pings[src_y.min(src_h - 1)];
        let row   = ping_to_gray_row(ping, img_w as usize, WATERFALL_GAMMA);
        for (x, &v) in row.iter().enumerate() {
            img.put_pixel(x as u32, dst_y, image::Luma([v]));
        }
    }
    img
}

/// Render a channel's pings as a false-colour RGB mosaic.
/// Each ping occupies one output row; uses bilinear resampling + per-ping stretch + gamma.
fn render_mosaic_rgb(pings: &[&Ping], max_w: u32, max_h: u32, colormap: &str) -> RgbImage {
    if pings.is_empty() {
        return ImageBuffer::from_pixel(1, 1, Rgb([0u8, 0, 0]));
    }
    let img_w = canonical_width(pings, max_w);
    let src_h = pings.len();
    let img_h = (src_h as u32).min(max_h).max(1);
    let mut img: RgbImage = ImageBuffer::new(img_w, img_h);
    for dst_y in 0..img_h {
        let src_y = (dst_y as usize * src_h) / img_h as usize;
        let ping  = &pings[src_y.min(src_h - 1)];
        let gray  = ping_to_gray_row(ping, img_w as usize, MOSAIC_GAMMA);
        for (x, &g) in gray.iter().enumerate() {
            img.put_pixel(x as u32, dst_y, apply_colormap(g as f32 / 255.0, colormap));
        }
    }
    img
}

/// Stitch port + starboard sidescan pings into a single butterfly mosaic.
/// Port arm (ch4) is reversed so both arms radiate outward from a shared nadir line.
/// Returns `None` when both inputs are empty.
fn render_sidescan_stitched(
    port_pings: &[&Ping],
    star_pings: &[&Ping],
    single_w:   u32,
    max_h:      u32,
    colormap:   &str,
) -> Option<RgbImage> {
    if port_pings.is_empty() && star_pings.is_empty() {
        return None;
    }
    let n_pings = port_pings.len().max(star_pings.len());
    let src_h   = n_pings;
    let img_h   = (n_pings as u32).min(max_h).max(1);
    let total_w = single_w * 2;
    let mut img: RgbImage = ImageBuffer::from_pixel(total_w, img_h, Rgb([5u8, 10, 20]));

    for dst_y in 0..img_h {
        let src_y = (dst_y as usize * src_h) / img_h as usize;

        // Starboard → right half (nadir at left edge of this half)
        if !star_pings.is_empty() {
            let ping = &star_pings[src_y.min(star_pings.len() - 1)];
            let gray = ping_to_gray_row(ping, single_w as usize, MOSAIC_GAMMA);
            for (xi, &g) in gray.iter().enumerate() {
                img.put_pixel(single_w + xi as u32, dst_y, apply_colormap(g as f32 / 255.0, colormap));
            }
        }
        // Port → left half, reversed so the outer edge is at x = 0
        if !port_pings.is_empty() {
            let ping = &port_pings[src_y.min(port_pings.len() - 1)];
            let gray = ping_to_gray_row(ping, single_w as usize, MOSAIC_GAMMA);
            for (xi, &g) in gray.iter().enumerate() {
                let dst_x = single_w - 1 - xi as u32;
                img.put_pixel(dst_x, dst_y, apply_colormap(g as f32 / 255.0, colormap));
            }
        }
    }
    Some(img)
}

/// Encode an RgbImage to PNG bytes in memory (used by KMZ ground overlay).
fn encode_png_rgb(img: &RgbImage) -> Result<Vec<u8>> {
    let mut buf = Vec::new();
    let encoder = PngEncoder::new(&mut buf);
    encoder
        .write_image(img.as_raw(), img.width(), img.height(), ColorType::Rgb8.into())
        .context("In-memory PNG encode failed")?;
    Ok(buf)
}

// ── Geographic helpers ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy)]
struct BBox {
    min_lat: f64,
    max_lat: f64,
    min_lon: f64,
    max_lon: f64,
}

impl BBox {
    fn from_pings(pings: &[Ping]) -> Option<Self> {
        let valid: Vec<_> = pings
            .iter()
            .filter(|p| p.latitude != 0.0 || p.longitude != 0.0)
            .collect();
        if valid.is_empty() {
            return None;
        }
        let min_lat = valid.iter().map(|p| p.latitude).fold(f64::INFINITY, f64::min);
        let max_lat = valid.iter().map(|p| p.latitude).fold(f64::NEG_INFINITY, f64::max);
        let min_lon = valid.iter().map(|p| p.longitude).fold(f64::INFINITY, f64::min);
        let max_lon = valid.iter().map(|p| p.longitude).fold(f64::NEG_INFINITY, f64::max);
        Some(BBox { min_lat, max_lat, min_lon, max_lon })
    }

    fn center_lat(&self) -> f64 {
        (self.min_lat + self.max_lat) / 2.0
    }
    fn center_lon(&self) -> f64 {
        (self.min_lon + self.max_lon) / 2.0
    }

    /// Approximate camera range in metres for KML `<LookAt>`.
    fn kml_range_m(&self) -> f64 {
        let lat_km = (self.max_lat - self.min_lat).abs() * 111.0;
        let lon_km = (self.max_lon - self.min_lon).abs()
            * 111.0
            * self.center_lat().to_radians().cos();
        (lat_km.max(lon_km) * 1000.0 * 2.5).max(200.0)
    }

    /// MBTiles spec `bounds` string: "min_lon,min_lat,max_lon,max_lat".
    fn mbtiles_bounds(&self) -> String {
        format!(
            "{:.6},{:.6},{:.6},{:.6}",
            self.min_lon, self.min_lat, self.max_lon, self.max_lat
        )
    }

    /// MBTiles spec `center` string: "lon,lat,zoom".
    fn mbtiles_center(&self, zoom: u8) -> String {
        format!(
            "{:.6},{:.6},{}",
            self.center_lon(),
            self.center_lat(),
            zoom
        )
    }
}

// ── Output writers ────────────────────────────────────────────────────────────

const WATERFALL_MAX_W: u32 = 4096;
const WATERFALL_MAX_H: u32 = 8192;
/// Gamma < 1 lifts shadow detail; 0.70 gives good waterfall contrast.
const WATERFALL_GAMMA: f32 = 0.70;
/// Slightly stronger lift for false-colour mosaics.
const MOSAIC_GAMMA: f32 = 0.65;
/// Per-channel width of the stitched butterfly mosaic / KMZ ground overlay.
const MOSAIC_COMBINED_W: u32 = 2048;
const MBTILES_MAX_ZOOM: u8 = 0;
const KML_MAX_PLACEMARKS: usize = 600;
const VIEWER_MAX_PINGS: usize = 2000;

fn write_waterfall_per_channel(
    parsed: &ParseResult,
    output_dir: &Path,
) -> Result<Vec<OutputArtifact>> {
    let channels = pings_by_channel(parsed);
    let mut arts = Vec::new();
    for (ch, pings) in &channels {
        let img   = render_gray(pings, WATERFALL_MAX_W, WATERFALL_MAX_H);
        let fname = format!("waterfall_ch{ch}.png");
        let path  = output_dir.join(&fname);
        let ch_label = channel_label(parsed, *ch);
        match img.save(&path) {
            Ok(()) => arts.push(OutputArtifact {
                kind: "waterfall".to_string(),
                path: path.display().to_string(),
                details: format!(
                    "Ch {} ({}) · {}×{} · per-ping 2–98% stretch · γ{WATERFALL_GAMMA:.2}",
                    ch, ch_label, img.width(), img.height()
                ),
            }),
            Err(e) => arts.push(OutputArtifact {
                kind: "waterfall".to_string(),
                path: path.display().to_string(),
                details: format!("ERROR writing {fname}: {e:#}"),
            }),
        }
    }
    Ok(arts)
}

fn write_mosaic_per_channel(
    parsed: &ParseResult,
    output_dir: &Path,
    colormap: &str,
) -> Result<Vec<OutputArtifact>> {
    let channels = pings_by_channel(parsed);
    let mut arts = Vec::new();

    // Per-channel mosaics
    for (ch, pings) in &channels {
        let img   = render_mosaic_rgb(pings, WATERFALL_MAX_W, WATERFALL_MAX_H, colormap);
        let fname = format!("mosaic_ch{ch}.png");
        let path  = output_dir.join(&fname);
        let ch_label = channel_label(parsed, *ch);
        match img.save(&path) {
            Ok(()) => arts.push(OutputArtifact {
                kind: "mosaic".to_string(),
                path: path.display().to_string(),
                details: format!(
                    "Ch {} ({}) · {}×{} · {} palette",
                    ch, ch_label, img.width(), img.height(), colormap
                ),
            }),
            Err(e) => arts.push(OutputArtifact {
                kind: "mosaic".to_string(),
                path: path.display().to_string(),
                details: format!("ERROR writing {fname}: {e:#}"),
            }),
        }
    }

    // Stitched butterfly mosaic when port (ch4/ch0) + starboard (ch5/ch1) detected
    let port_key = [4u32, 0].iter().find(|&&k| channels.contains_key(&k)).copied();
    let star_key = [5u32, 1].iter().find(|&&k| channels.contains_key(&k)).copied();
    if let (Some(pk), Some(sk)) = (port_key, star_key) {
        let port_pings = &channels[&pk];
        let star_pings = &channels[&sk];
        if let Some(combined) = render_sidescan_stitched(
            port_pings, star_pings, MOSAIC_COMBINED_W, WATERFALL_MAX_H, colormap,
        ) {
            let path = output_dir.join("mosaic_combined.png");
            match combined.save(&path) {
                Ok(()) => arts.push(OutputArtifact {
                    kind: "mosaic_combined".to_string(),
                    path: path.display().to_string(),
                    details: format!(
                        "Stitched port+starboard butterfly · {}×{} · {} palette",
                        combined.width(), combined.height(), colormap
                    ),
                }),
                Err(e) => arts.push(OutputArtifact {
                    kind: "mosaic_combined".to_string(),
                    path: path.display().to_string(),
                    details: format!("ERROR writing mosaic_combined.png: {e:#}"),
                }),
            }
        }
    }
    Ok(arts)
}

fn write_mbtiles(parsed: &ParseResult, path: &Path, colormap: &str) -> Result<()> {
    let conn = Connection::open(path)
        .with_context(|| format!("Failed to create MBTiles DB: {}", path.display()))?;

    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS metadata (name TEXT, value TEXT);
         CREATE TABLE IF NOT EXISTS tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB);
         CREATE UNIQUE INDEX IF NOT EXISTS tile_index ON tiles (zoom_level, tile_column, tile_row);
         DELETE FROM metadata;
         DELETE FROM tiles;",
    )?;

    // Metadata — bounds and center are required by most MBTiles consumers
    let bbox = BBox::from_pings(&parsed.pings);
    let bounds_str = bbox
        .map(|b| b.mbtiles_bounds())
        .unwrap_or_else(|| "-180,-85,180,85".to_string());
    let center_str = bbox
        .map(|b| b.mbtiles_center(MBTILES_MAX_ZOOM))
        .unwrap_or_else(|| "0,0,0".to_string());

    for (name, value) in &[
        ("name", "SonarSniffer Mosaic"),
        ("description", &format!("{} pings", parsed.pings.len())),
        ("type", "overlay"),
        ("format", "png"),
        ("minzoom", "0"),
        ("maxzoom", &MBTILES_MAX_ZOOM.to_string()),
        ("bounds", &bounds_str),
        ("center", &center_str),
    ] {
        conn.execute(
            "INSERT INTO metadata (name, value) VALUES (?1, ?2)",
            (name, value),
        )?;
    }

    // Zoom-0 tile — render the dominant channel as a 256×256 mosaic
    let channels = pings_by_channel(parsed);
    let dominant: Vec<&Ping> = channels
        .values()
        .max_by_key(|v| v.len())
        .cloned()
        .unwrap_or_default();

    let tile = render_mosaic_rgb(&dominant, 256, 256, colormap);
    let png = encode_png_rgb(&tile)?;

    conn.execute(
        "INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (?1, ?2, ?3, ?4)",
        (0i32, 0i32, 0i32, png),
    )?;

    Ok(())
}

/// Write KML with a styled trackline + decimated depth placemarks + LookAt camera.
/// Returns the number of placemarks written.
fn write_kml(parsed: &ParseResult, path: &Path) -> Result<usize> {
    let bbox = BBox::from_pings(&parsed.pings);

    // LookAt element (omit if no GPS)
    let look_at = bbox
        .map(|b| {
            format!(
                "\n  <LookAt>\
                \n    <longitude>{:.6}</longitude>\
                \n    <latitude>{:.6}</latitude>\
                \n    <altitude>0</altitude>\
                \n    <range>{:.0}</range>\
                \n    <tilt>0</tilt>\
                \n    <heading>0</heading>\
                \n    <altitudeMode>relativeToGround</altitudeMode>\
                \n  </LookAt>",
                b.center_lon(),
                b.center_lat(),
                b.kml_range_m()
            )
        })
        .unwrap_or_default();

    // Trackline coordinates (lon,lat,-depth_m for altitude)
    let track_coords: String = parsed
        .pings
        .iter()
        .filter(|p| p.latitude != 0.0 || p.longitude != 0.0)
        .map(|p| {
            format!(
                "{:.7},{:.7},{:.1}",
                p.longitude,
                p.latitude,
                -(p.depth_m.max(0.0) as f64)
            )
        })
        .collect::<Vec<_>>()
        .join("\n              ");

    // Decimated ping placemarks with depth / channel data
    let step = (parsed.pings.len() / KML_MAX_PLACEMARKS).max(1);
    let placemarks: Vec<String> = parsed
        .pings
        .iter()
        .step_by(step)
        .take(KML_MAX_PLACEMARKS)
        .filter(|p| p.latitude != 0.0 || p.longitude != 0.0)
        .map(|p| {
            format!(
                "    <Placemark>\
                \n      <styleUrl>#pingStyle</styleUrl>\
                \n      <ExtendedData>\
                \n        <Data name=\"depth_ft\"><value>{:.1}</value></Data>\
                \n        <Data name=\"depth_m\"><value>{:.2}</value></Data>\
                \n        <Data name=\"channel\"><value>{}</value></Data>\
                \n        <Data name=\"sample_count\"><value>{}</value></Data>\
                \n        <Data name=\"timestamp_ms\"><value>{}</value></Data>\
                \n      </ExtendedData>\
                \n      <Point>\
                \n        <altitudeMode>clampToGround</altitudeMode>\
                \n        <coordinates>{:.7},{:.7},{:.1}</coordinates>\
                \n      </Point>\
                \n    </Placemark>",
                p.depth_ft,
                p.depth_m,
                p.channel,
                p.sample_count,
                p.timestamp_ms,
                p.longitude,
                p.latitude,
                -(p.depth_m.max(0.0) as f64)
            )
        })
        .collect();

    let n = placemarks.len();
    let ping_block = placemarks.join("\n");

    let kml = format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>SonarSniffer Track</name>{look_at}
  <Style id="trackStyle">
    <LineStyle><color>ff0050ff</color><width>3</width></LineStyle>
    <PolyStyle><fill>0</fill></PolyStyle>
  </Style>
  <Style id="pingStyle">
    <IconStyle>
      <color>ffffffff</color>
      <scale>0.35</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png</href></Icon>
    </IconStyle>
    <BalloonStyle>
      <text><![CDATA[<b>Ping</b><br/>
Depth: <b>$[depth_ft] ft</b> ($[depth_m] m)<br/>
Channel: $[channel]<br/>
Samples: $[sample_count]]]></text>
    </BalloonStyle>
  </Style>
  <Folder>
    <name>Trackline</name>
    <Placemark>
      <name>Track</name>
      <styleUrl>#trackStyle</styleUrl>
      <LineString>
        <tessellate>1</tessellate>
        <altitudeMode>clampToGround</altitudeMode>
        <coordinates>
              {track_coords}
        </coordinates>
      </LineString>
    </Placemark>
  </Folder>
  <Folder>
    <name>Depth Pings (1-in-{step})</name>
{ping_block}
  </Folder>
</Document>
</kml>
"#
    );

    fs::write(path, kml).with_context(|| format!("Failed to write KML: {}", path.display()))?;
    Ok(n)
}

/// Write a KMZ containing the KML and (if GPS is available) a georeferenced
/// sidescan GroundOverlay.  Prefers `mosaic_combined.png` from `output_dir`;
/// falls back to an inline render of the dominant channel.
/// Returns `true` if the GroundOverlay was embedded.
fn write_kmz(
    kml_path:   &Path,
    kmz_path:   &Path,
    parsed:     &ParseResult,
    output_dir: &Path,
    colormap:   &str,
) -> Result<bool> {
    let kml_str = fs::read_to_string(kml_path)
        .with_context(|| format!("Failed to read KML for KMZ: {}", kml_path.display()))?;

    // Build overlay PNG: prefer already-rendered combined mosaic for quality
    let overlay: Option<(Vec<u8>, BBox)> = BBox::from_pings(&parsed.pings).and_then(|bbox| {
        // 1. Try pre-rendered combined mosaic (highest quality, correct aspect)
        let combined_path = output_dir.join("mosaic_combined.png");
        if combined_path.exists() {
            if let Ok(bytes) = fs::read(&combined_path) {
                return Some((bytes, bbox));
            }
        }
        // 2. Fall back to inline render of dominant channel at overlay resolution
        let channels = pings_by_channel(parsed);
        let dominant: Vec<&Ping> = channels.values().max_by_key(|v| v.len()).cloned()?;
        let img = render_mosaic_rgb(&dominant, MOSAIC_COMBINED_W, WATERFALL_MAX_H, colormap);
        encode_png_rgb(&img).ok().map(|png| (png, bbox))
    });

    // Inject GroundOverlay into KML before </Document>
    let final_kml = if let Some((_, bbox)) = &overlay {
        let ground_overlay = format!(
            "  <GroundOverlay>\
            \n    <name>Sonar Sidescan Mosaic</name>\
            \n    <color>c8ffffff</color>\
            \n    <drawOrder>1</drawOrder>\
            \n    <Icon><href>mosaic.png</href></Icon>\
            \n    <LatLonBox>\
            \n      <north>{:.7}</north>\
            \n      <south>{:.7}</south>\
            \n      <east>{:.7}</east>\
            \n      <west>{:.7}</west>\
            \n      <rotation>0</rotation>\
            \n    </LatLonBox>\
            \n  </GroundOverlay>\
            \n</Document>",
            bbox.max_lat, bbox.min_lat, bbox.max_lon, bbox.min_lon
        );
        kml_str.replace("</Document>", &ground_overlay)
    } else {
        kml_str
    };

    let file = fs::File::create(kmz_path)
        .with_context(|| format!("Failed to create KMZ: {}", kmz_path.display()))?;
    let mut zip = zip::ZipWriter::new(file);
    zip.start_file("doc.kml", SimpleFileOptions::default())?;
    zip.write_all(final_kml.as_bytes())?;
    if let Some((png_bytes, _)) = &overlay {
        zip.start_file("mosaic.png", SimpleFileOptions::default())?;
        zip.write_all(png_bytes)?;
    }
    zip.finish()?;

    Ok(overlay.is_some())
}

fn write_arcgis_sidecar(parsed: &ParseResult, path: &Path) -> Result<()> {
    let features = parsed
        .pings
        .iter()
        .map(|p| {
            serde_json::json!({
                "geometry": {
                    "x": p.longitude,
                    "y": p.latitude,
                    "spatialReference": {"wkid": 4326}
                },
                "attributes": {
                    "sequence":       p.sequence,
                    "timestamp_ms":   p.timestamp_ms,
                    "depth_m":        (p.depth_m * 1000.0).round() / 1000.0,
                    "depth_ft":       (p.depth_ft * 100.0).round() / 100.0,
                    "altitude_m":     p.altitude_m,
                    "beam_angle_deg": p.beam_angle_deg,
                    "channel":        p.channel,
                    "sample_count":   p.sample_count
                }
            })
        })
        .collect::<Vec<_>>();

    let doc = serde_json::json!({
        "geometryType": "esriGeometryPoint",
        "spatialReference": {"wkid": 4326},
        "fields": [
            {"name":"sequence",       "type":"esriFieldTypeInteger"},
            {"name":"timestamp_ms",   "type":"esriFieldTypeDouble"},
            {"name":"depth_m",        "type":"esriFieldTypeDouble"},
            {"name":"depth_ft",       "type":"esriFieldTypeDouble"},
            {"name":"altitude_m",     "type":"esriFieldTypeDouble"},
            {"name":"beam_angle_deg", "type":"esriFieldTypeDouble"},
            {"name":"channel",        "type":"esriFieldTypeInteger"},
            {"name":"sample_count",   "type":"esriFieldTypeInteger"}
        ],
        "features": features
    });

    fs::write(path, serde_json::to_vec_pretty(&doc)?)
        .with_context(|| format!("Failed to write ArcGIS sidecar: {}", path.display()))?;
    Ok(())
}

fn write_native_viewer(parsed: &ParseResult, viewer_dir: &Path) -> Result<()> {
    fs::create_dir_all(viewer_dir)
        .with_context(|| format!("Failed to create viewer dir: {}", viewer_dir.display()))?;

    // ── track.geojson ────────────────────────────────────────────────────────
    let track_coords: Vec<_> = parsed
        .pings
        .iter()
        .filter(|p| p.latitude != 0.0 || p.longitude != 0.0)
        .map(|p| serde_json::json!([p.longitude, p.latitude]))
        .collect();

    let track_geojson = serde_json::json!({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": { "type": "LineString", "coordinates": track_coords },
            "properties": { "name": "Sonar track" }
        }]
    });

    fs::write(
        viewer_dir.join("track.geojson"),
        serde_json::to_vec_pretty(&track_geojson)?,
    )
    .context("Failed to write track.geojson")?;

    // ── pings.geojson (decimated, with depth + channel) ───────────────────────
    let step = (parsed.pings.len() / VIEWER_MAX_PINGS).max(1);
    let ping_features: Vec<_> = parsed
        .pings
        .iter()
        .step_by(step)
        .filter(|p| p.latitude != 0.0 || p.longitude != 0.0)
        .map(|p| {
            serde_json::json!({
                "type": "Feature",
                "geometry": { "type": "Point", "coordinates": [p.longitude, p.latitude] },
                "properties": {
                    "sequence":     p.sequence,
                    "depth_ft":     (p.depth_ft * 10.0).round() / 10.0,
                    "depth_m":      (p.depth_m * 100.0).round() / 100.0,
                    "channel":      p.channel,
                    "sample_count": p.sample_count,
                    "timestamp_ms": p.timestamp_ms
                }
            })
        })
        .collect();

    let pings_geojson = serde_json::json!({
        "type": "FeatureCollection",
        "features": ping_features
    });

    fs::write(
        viewer_dir.join("pings.geojson"),
        serde_json::to_vec_pretty(&pings_geojson)?,
    )
    .context("Failed to write pings.geojson")?;

    // ── index.html ────────────────────────────────────────────────────────────
    let html = r#"<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SonarSniffer Viewer</title>
  <link href="https://unpkg.com/maplibre-gl@5.2.0/dist/maplibre-gl.css" rel="stylesheet" />
  <script src="https://unpkg.com/maplibre-gl@5.2.0/dist/maplibre-gl.js"></script>
  <style>
    html, body, #map { margin: 0; height: 100%; width: 100%; }
    .panel {
      position: absolute; top: 12px; left: 12px;
      background: rgba(255,255,255,0.92); padding: 10px 14px;
      font: 12px/1.5 sans-serif; border-radius: 8px; max-width: 280px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    }
    .panel strong { font-size: 13px; }
    .legend { margin-top: 8px; display: flex; align-items: center; gap: 6px; }
    .legend-bar {
      width: 100px; height: 10px; border-radius: 4px;
      background: linear-gradient(to right, #d0f0ff, #00aaff, #00dd88, #ffcc00, #ff2200);
    }
    .legend-labels { display: flex; justify-content: space-between; width: 100px; font-size: 10px; color: #555; }
  </style>
</head>
<body>
<div id="map"></div>
<div class="panel">
  <strong>SonarSniffer Viewer</strong><br />
  Track: <span style="color:#ff5a36">&#x2014;</span>&nbsp;
  Pings coloured by depth.  Click a ping for details.<br />
  <div class="legend">
    <div>
      <div class="legend-bar"></div>
      <div class="legend-labels"><span id="dmin">0</span><span id="dmax">…</span></div>
    </div>
    <span style="font-size:10px">ft</span>
  </div>
</div>
<script src="app.js"></script>
</body>
</html>
"#;

    // ── app.js ────────────────────────────────────────────────────────────────
    let js = r#"const map = new maplibregl.Map({
  container: 'map',
  style: {
    version: 8,
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '&copy; OpenStreetMap contributors'
      }
    },
    layers: [{ id: 'osm', type: 'raster', source: 'osm' }]
  },
  center: [-90, 30],
  zoom: 3
});

async function load() {
  const [trackGeo, pingsGeo] = await Promise.all([
    fetch('track.geojson').then(r => r.json()),
    fetch('pings.geojson').then(r => r.json())
  ]);

  const coords = trackGeo.features?.[0]?.geometry?.coordinates ?? [];
  if (coords.length > 1) {
    const bounds = coords.reduce(
      (b, c) => b.extend(c),
      new maplibregl.LngLatBounds(coords[0], coords[0])
    );
    map.fitBounds(bounds, { padding: 48, duration: 0 });
  }

  const depths = pingsGeo.features.map(f => f.properties.depth_ft || 0).filter(d => d > 0);
  const maxDepth = depths.length ? Math.ceil(Math.max(...depths)) : 60;
  const el = document.getElementById;
  el('dmax').textContent = maxDepth;

  map.on('load', () => {
    // Track line
    map.addSource('track', { type: 'geojson', data: trackGeo });
    map.addLayer({
      id: 'track-line',
      type: 'line',
      source: 'track',
      paint: { 'line-color': '#ff5a36', 'line-width': 2.5 }
    });

    // Ping depth circles
    map.addSource('pings', { type: 'geojson', data: pingsGeo });
    map.addLayer({
      id: 'pings-dots',
      type: 'circle',
      source: 'pings',
      paint: {
        'circle-radius': 4,
        'circle-color': [
          'interpolate', ['linear'], ['get', 'depth_ft'],
          0,              '#d0f0ff',
          maxDepth * 0.25, '#00aaff',
          maxDepth * 0.5,  '#00dd88',
          maxDepth * 0.75, '#ffcc00',
          maxDepth,        '#ff2200'
        ],
        'circle-opacity': 0.85,
        'circle-stroke-width': 0.5,
        'circle-stroke-color': 'rgba(0,0,0,0.25)'
      }
    });

    map.on('click', 'pings-dots', e => {
      if (!e.features.length) return;
      const p = e.features[0].properties;
      new maplibregl.Popup()
        .setLngLat(e.lngLat)
        .setHTML(
          `<b>Ping #${p.sequence}</b><br>` +
          `Depth: <b>${p.depth_ft} ft</b> (${p.depth_m} m)<br>` +
          `Channel: ${p.channel} &nbsp;·&nbsp; Samples: ${p.sample_count}`
        )
        .addTo(map);
    });

    map.on('mouseenter', 'pings-dots', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'pings-dots', () => { map.getCanvas().style.cursor = ''; });
  });
}

load().catch(console.error);
"#;

    fs::write(viewer_dir.join("index.html"), html).context("Failed to write viewer index.html")?;
    fs::write(viewer_dir.join("app.js"), js).context("Failed to write viewer app.js")?;
    Ok(())
}

// ── Misc helpers ──────────────────────────────────────────────────────────────

fn channel_label(parsed: &ParseResult, ch: u32) -> String {
    parsed
        .channels
        .iter()
        .find(|c| c.id == ch)
        .and_then(|c| c.mapped_type.clone())
        .unwrap_or_else(|| "unknown".to_string())
}
