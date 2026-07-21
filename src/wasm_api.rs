//! Browser WASM surface (experimental). Built with:
//! `wasm-pack build --target web --release --no-default-features`
//! See docs/BUILD_FLAGS.md / docs/WASM.md.

use wasm_bindgen::prelude::*;

#[wasm_bindgen(start)]
pub fn wasm_start() {
    console_error_panic_hook::set_once();
}

#[wasm_bindgen]
pub fn greet() -> String {
    "Hello from SonarSniffer WASM!".to_string()
}

#[wasm_bindgen]
pub fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}
