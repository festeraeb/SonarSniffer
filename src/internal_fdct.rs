//! Bundled full-precision FDCT (internal `nauticuvs-full`, not crates.io).
//! Public diagnostics use neutral labels only.

use image::imageops::FilterType;
use image::GrayImage;
use ndarray::Array2;
use nauticuvs::{curvelet_forward, curvelet_inverse};

/// Shown in curvelet_diag — no external crate name.
pub const BACKEND_LABEL: &str = "ss-fdct";

const FDCT_MAX_DIM: u32 = 512;
const MIN_DIM: u32 = 32;

/// Light compile-time obfuscation for build fingerprint strings (not security).
pub fn build_fingerprint() -> String {
    const K: u8 = 0x5a;
    const ENC: &[u8] = &[
        0x34, 0x3f, 0x2e, 0x34, 0x33, 0x2f, 0x2c, 0x29, 0x74, 0x33, 0x34, 0x2e, 0x3f, 0x28,
        0x34, 0x3b, 0x2e,
    ];
    ENC.iter().map(|b| (b ^ K) as char).collect()
}

fn gray_to_array(img: &GrayImage) -> Array2<f32> {
    let (w, h) = (img.width() as usize, img.height() as usize);
    Array2::from_shape_fn((h, w), |(r, c)| img.get_pixel(c as u32, r as u32)[0] as f32 / 255.0)
}

fn array_to_gray(arr: &Array2<f32>, w: u32, h: u32) -> GrayImage {
    let mut out = GrayImage::new(w, h);
    for r in 0..h as usize {
        for c in 0..w as usize {
            let v = (arr[[r, c]].clamp(0.0, 1.0) * 255.0).round() as u8;
            out.put_pixel(c as u32, r as u32, image::Luma([v]));
        }
    }
    out
}

fn num_scales(rows: usize, cols: usize) -> usize {
    let m = rows.min(cols).max(MIN_DIM as usize);
    ((m as f64).log2() - 2.0).round().clamp(3.0, 6.0) as usize
}

fn resize_gray(img: &GrayImage, tw: u32, th: u32) -> GrayImage {
    image::imageops::resize(img, tw, th, FilterType::Triangle)
}

/// Downscale for FDCT, run transform at working resolution.
fn working_array(img: &GrayImage) -> (Array2<f32>, u32, u32, u32, u32) {
    let (ow, oh) = (img.width(), img.height());
    let scale = (FDCT_MAX_DIM as f32 / ow.max(oh) as f32).min(1.0);
    let (ww, wh) = if scale < 1.0 {
        (
            ((ow as f32) * scale).round().max(MIN_DIM as f32) as u32,
            ((oh as f32) * scale).round().max(MIN_DIM as f32) as u32,
        )
    } else {
        (ow, oh)
    };
    let work = if (ww, wh) != (ow, oh) {
        gray_to_array(&resize_gray(img, ww, wh))
    } else {
        gray_to_array(img)
    };
    (work, ow, oh, ww, wh)
}

fn mad_sigma(coeffs: &nauticuvs::CurveletCoeffs) -> f64 {
    let mut mags: Vec<f64> = Vec::new();
    for scale in &coeffs.detail {
        for sb in scale {
            for c in sb.iter() {
                let m = c.norm_sqr().sqrt();
                if m > 1e-12 {
                    mags.push(m);
                }
            }
        }
    }
    if mags.is_empty() {
        return 0.05;
    }
    mags.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let med = mags[mags.len() / 2];
    let sigma = med / 0.6745;
    let n = mags.len() as f64;
    let universal = sigma * (2.0 * n.ln()).sqrt();
    universal.clamp(0.01, 0.35)
}

/// Full-precision curvelet denoise. Returns `(image, suggested_threshold)`.
pub fn denoise_gray(
    img: GrayImage,
    threshold: f32,
) -> Result<(GrayImage, f32), String> {
    let (work, ow, oh, ww, wh) = working_array(&img);
    let rows = work.nrows();
    let cols = work.ncols();
    if rows < MIN_DIM as usize || cols < MIN_DIM as usize {
        return Err(format!("image too small ({ow}x{oh})"));
    }
    let scales = num_scales(rows, cols);
    let mut coeffs = curvelet_forward(&work, scales).map_err(|e| format!("fdct forward: {e}"))?;

    let suggested = mad_sigma(&coeffs) as f32;

    if threshold > 0.0 {
        coeffs.soft_threshold(threshold as f64);
    }

    let recon = curvelet_inverse(&coeffs).map_err(|e| format!("fdct inverse: {e}"))?;
    let mut denoised = if (ww, wh) != (ow, oh) {
        array_to_gray(&recon, ww, wh)
    } else {
        array_to_gray(&recon, ow, oh)
    };
    if (ww, wh) != (ow, oh) {
        denoised = resize_gray(&denoised, ow, oh);
    }

    Ok((denoised, if threshold > 0.0 { threshold } else { suggested }))
}
