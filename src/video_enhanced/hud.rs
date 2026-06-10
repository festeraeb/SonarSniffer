//! Minimal bitmap HUD for scrolling mosaic video (no font dependency).

use crate::garmin_rsd_parser::Ping;

const HUD_H: usize = 22;
const SCALE: usize = 2;

fn draw_string(pixels: &mut [u8], frame_w: usize, y: usize, text: &str, color: [u8; 3]) {
    let mut x = 8usize;
    for ch in text.chars() {
        if x + 6 * SCALE > frame_w {
            break;
        }
        draw_char(pixels, frame_w, x, y, ch, color);
        x += 6 * SCALE;
    }
}

fn draw_char(pixels: &mut [u8], frame_w: usize, x: usize, y: usize, ch: char, color: [u8; 3]) {
    let glyph = glyph_5x7(ch);
    for (row, bits) in glyph.iter().enumerate() {
        for col in 0..5 {
            if bits & (1 << (4 - col)) != 0 {
                for sy in 0..SCALE {
                    for sx in 0..SCALE {
                        let px = x + col * SCALE + sx;
                        let py = y + row * SCALE + sy;
                        if px < frame_w {
                            let off = (py * frame_w + px) * 3;
                            if off + 2 < pixels.len() {
                                pixels[off] = color[0];
                                pixels[off + 1] = color[1];
                                pixels[off + 2] = color[2];
                            }
                        }
                    }
                }
            }
        }
    }
}

fn glyph_5x7(ch: char) -> [u8; 7] {
    match ch {
        '0' => [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
        '1' => [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
        '2' => [0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F],
        '3' => [0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E],
        '4' => [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
        '5' => [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
        '6' => [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
        '7' => [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
        '8' => [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
        '9' => [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
        '.' => [0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C],
        ',' => [0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C, 0x08],
        '-' => [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],
        'f' => [0x07, 0x08, 0x1E, 0x08, 0x08, 0x08, 0x08],
        't' => [0x08, 0x08, 0x1C, 0x08, 0x08, 0x09, 0x06],
        'k' => [0x10, 0x10, 0x12, 0x1C, 0x12, 0x11, 0x11],
        ' ' => [0x00; 7],
        _ => [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    }
}

/// Speed between consecutive guide pings (knots) for HUD at `end_row`.
pub fn speed_kts_at(guide: &[Ping], end_row: usize) -> f32 {
    if guide.len() < 2 || end_row == 0 {
        return 0.0;
    }
    let i = end_row.min(guide.len() - 1);
    let a = &guide[i.saturating_sub(1)];
    let b = &guide[i];
    ping_pair_speed_kts(a, b)
}

fn ping_pair_speed_kts(a: &Ping, b: &Ping) -> f32 {
    const M_PER_DEG_LAT: f64 = 111_320.0;
    let valid = |p: &Ping| {
        p.latitude.is_finite()
            && p.longitude.is_finite()
            && (p.latitude != 0.0 || p.longitude != 0.0)
    };
    if !valid(a) || !valid(b) || b.timestamp_ms <= a.timestamp_ms {
        return 0.0;
    }
    let dlat = (b.latitude - a.latitude) * M_PER_DEG_LAT;
    let dlon = (b.longitude - a.longitude) * M_PER_DEG_LAT * b.latitude.to_radians().cos();
    let dist_m = (dlat * dlat + dlon * dlon).sqrt();
    let dt_s = (b.timestamp_ms - a.timestamp_ms) as f64 / 1000.0;
    if dt_s <= 0.0 {
        return 0.0;
    }
    (dist_m / dt_s * 1.94384) as f32
}

/// HUD variant that uses guide ping row and optional speed from neighbours.
pub fn draw_scroll_hud_guide(
    pixels: &mut [u8],
    width: u32,
    height: u32,
    guide: &[Ping],
    end_row: usize,
    overlay_depth: bool,
    overlay_speed: bool,
    overlay_gps: bool,
) {
    if !overlay_depth && !overlay_speed && !overlay_gps {
        return;
    }
    let w = width as usize;
    let h = height as usize;
    if w == 0 || h < HUD_H + 4 || guide.is_empty() {
        return;
    }
    let idx = end_row.min(guide.len() - 1);
    let p = &guide[idx];
    let bar_top = h - HUD_H;
    for y in bar_top..h {
        for x in 0..w {
            let off = (y * w + x) * 3;
            if off + 2 >= pixels.len() {
                break;
            }
            pixels[off] = (pixels[off] as u16 * 35 / 100) as u8;
            pixels[off + 1] = (pixels[off + 1] as u16 * 35 / 100) as u8;
            pixels[off + 2] = (pixels[off + 2] as u16 * 55 / 100) as u8;
        }
    }
    let mut parts: Vec<String> = Vec::new();
    if overlay_depth {
        parts.push(format!("{:.0}ft", p.depth_ft));
    }
    if overlay_speed {
        let kts = speed_kts_at(guide, idx);
        parts.push(format!("{:.1}kt", kts));
    }
    if overlay_gps {
        parts.push(format!("{:.5},{:.5}", p.latitude, p.longitude));
    }
    draw_string(pixels, w, bar_top + 4, &parts.join("  "), [240, 248, 255]);
}
