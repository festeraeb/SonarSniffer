//! Browser WASM surface for SonarSniffer. Built with:
//! `wasm-pack build --target web --release --no-default-features`
//! See docs/BUILD_FLAGS.md / docs/WASM.md.
//!
//! The browser pipeline runs `parse_rsd_bytes` (parse + channel discovery
//! on raw `.RSD` bytes from a `File.arrayBuffer()`) and ships the result
//! back to JS as JSON.  The native-heavy modules (rusqlite mbtiles,
//! gstreamer video, opencv SoundTiles) stay native-only.

use wasm_bindgen::prelude::*;

use crate::wasm_pipeline::{run_pipeline, PipelineOutput, MAX_PINGS_IN_JSON};

#[wasm_bindgen(start)]
pub fn wasm_start() {
    console_error_panic_hook::set_once();
}

/// Build version exposed to the GUI.  Mirrors the native `--version` flag.
#[wasm_bindgen]
pub fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// Compatibility greeting (kept for the original demo pages).
#[wasm_bindgen]
pub fn greet() -> String {
    "SonarSniffer WASM ready.  Drop a .RSD file to parse.".to_string()
}

/// Returns `true` if the given byte buffer starts with a recognised
/// Garmin RSD record-header magic.  Cheap sniff used by the GUI to
/// filter obviously-non-RSD uploads before invoking the full pipeline.
/// The full parser is more permissive (it also supports files where the
/// magic is found after a header preamble), so this returns false only
/// for clearly non-RSD inputs.
#[wasm_bindgen]
pub fn looks_like_rsd(bytes: &[u8]) -> bool {
    if bytes.len() < 4 {
        return false;
    }
    // First four bytes = little-endian u32 record header magic.
    let m = u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
    if matches!(m, 0xB7E9DA86 | 0xB7E9DA87 | 0xB7E9DA88 | 0xB7E9DA89) {
        return true;
    }
    // Fall through: let the parser try.  Real CV / Sonar files have a
    // different first-byte signature but parse fine via the Garmin
    // record-header scan.  We only reject obviously non-RSD inputs
    // (text files, PNGs, JPEGs).
    // Magic byte checks for common non-sonar formats:
    //   PNG  89 50 4E 47
    //   JFIF  FF D8 FF
    //   PDF  25 50 44 46
    //   ZIP  50 4B 03 04
    let m0 = bytes[0];
    if m0 == 0x89 || m0 == 0xFF || m0 == 0x25 || m0 == 0x50 {
        return false;
    }
    // Default: optimistically let the parser try.
    true
}

/// Run the full parse + discovery pipeline on raw RSD bytes and return
/// the result as a JS object.  Heavy work — expects to be called from a
/// Web Worker for files > 10 MB.
#[wasm_bindgen]
pub fn parse_rsd_bytes(bytes: Vec<u8>) -> Result<JsValue, JsValue> {
    let out = run_pipeline(bytes);
    serde_wasm_bindgen::to_value(&out)
        .map_err(|e| JsValue::from_str(&format!("serialize error: {e}")))
}

/// Cap constant exposed to JS so the UI can show "showing N of M pings".
#[wasm_bindgen]
pub fn max_pings_in_json() -> usize {
    MAX_PINGS_IN_JSON
}

/// Run the pipeline and return a `PipelineHandle` so subsequent
/// `ping_samples(handle, ch, idx)` calls stay cheap.  For small files
/// `parse_rsd_bytes` is fine; for files > 50 MB prefer this entry point
/// to avoid keeping two copies of the metadata alive.
#[wasm_bindgen]
pub fn parse_rsd_handle(bytes: Vec<u8>) -> Result<PipelineHandle, JsValue> {
    let out = run_pipeline(bytes);
    Ok(PipelineHandle { inner: out })
}

/// Wrapper so JS can hold the pipeline output and query parts of it
/// without re-serialising the whole thing every call.
#[wasm_bindgen]
pub struct PipelineHandle {
    pub(crate) inner: PipelineOutput,
}

#[wasm_bindgen]
impl PipelineHandle {
    #[wasm_bindgen(getter)]
    pub fn discovery_ping_count(&self) -> usize {
        self.inner.discovery_ping_count
    }
    #[wasm_bindgen(getter)]
    pub fn parse_record_count(&self) -> usize {
        self.inner.parse.record_count
    }
    #[wasm_bindgen(getter)]
    pub fn parse_channels(&self) -> JsValue {
        serde_wasm_bindgen::to_value(&self.inner.parse.channels).unwrap_or(JsValue::NULL)
    }
    #[wasm_bindgen(getter)]
    pub fn discovery_log(&self) -> Vec<JsValue> {
        self.inner
            .discovery
            .discovery_log
            .iter()
            .map(|s| JsValue::from_str(s))
            .collect()
    }
    #[wasm_bindgen(getter)]
    pub fn channel_summary(&self) -> JsValue {
        serde_wasm_bindgen::to_value(&self.inner.channel_summary).unwrap_or(JsValue::NULL)
    }
    #[wasm_bindgen(getter)]
    pub fn pings(&self) -> JsValue {
        serde_wasm_bindgen::to_value(&self.inner.pings).unwrap_or(JsValue::NULL)
    }
    #[wasm_bindgen(getter)]
    pub fn sidescan_pairs(&self) -> JsValue {
        serde_wasm_bindgen::to_value(&self.inner.discovery.sidescan_pairs).unwrap_or(JsValue::NULL)
    }
    #[wasm_bindgen(getter)]
    pub fn center_channels(&self) -> JsValue {
        serde_wasm_bindgen::to_value(&self.inner.discovery.center_channels).unwrap_or(JsValue::NULL)
    }
    #[wasm_bindgen(getter)]
    pub fn scanlines(&self) -> JsValue {
        serde_wasm_bindgen::to_value(&self.inner.discovery.scanlines).unwrap_or(JsValue::NULL)
    }
}

/// State-less ping-samples lookup.  The full `ParseResult` is held
/// inside `PipelineHandle`; we expose samples per (channel, index) so
/// the GUI can draw waterfall tiles without copying the whole sample
/// vector across the JS boundary.
#[wasm_bindgen]
pub fn ping_samples(handle: &PipelineHandle, channel: u32, index: usize) -> JsValue {
    match crate::wasm_pipeline::get_ping_samples(&handle.inner.parse, channel, index) {
        Some(samples) => serde_wasm_bindgen::to_value(&samples).unwrap_or(JsValue::NULL),
        None => JsValue::NULL,
    }
}
