# SonarSniffer Cargo / build flags

Single inventory for **production** builds. Installers, sidecars, smoke tests, and
GitHub Release CI must use these — not a bare `cargo build` debug default.

## Feature flags (`Cargo.toml` `[features]`)

| Feature | Default? | Purpose |
|---------|----------|---------|
| *(none)* | `default = []` | Production CLI/desktop: pure-Rust AV1 (`rav1e`), no GStreamer/OpenCV |
| `video-gstreamer` | no | Legacy H.264 / GStreamer path (optional; requires system GStreamer) |
| `soundtiles` | no | OpenCV-backed SoundTiles **in-process** (desktop normally uses the `soundtiles` sidecar binary instead) |
| `full-license` | no | License gate unlock (propagated to Tauri via `tauri-appsonarsniffer/full-license`) |
| `jemalloc` | no | Linux-only allocator (`tikv-jemallocator`); optional host tuning |

Desktop crate features (`desktop/src-tauri/Cargo.toml`):

| Feature | Notes |
|---------|-------|
| `default = []` | Matches core — no GStreamer in production Tauri build |
| `full-license` | Enables `sonarsniffer/full-license` |

## Production native flags (master / release line)

```bash
cargo build --release --no-default-features \
  --bin sonarsniffer-cli --bin parse_cli
```

Linux optional allocator:

```bash
cargo build --release --no-default-features --features jemalloc \
  --bin sonarsniffer-cli --bin parse_cli
```

Sidecars (Tauri):

```bash
# tools/stage_tauri_sidecars.sh | .ps1
cargo build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli
cargo build --release -p soundtiles --bin soundtiles
```

**Do not** pass `--features video-gstreamer` for Release artifacts unless intentionally
shipping the legacy H.264 path. AV1 video works without that feature.

### Recommended env

| Variable | Typical value |
|----------|----------------|
| `CARGO_TARGET_DIR` | `/data/cargo-target` (Linux fleet) or `%LOCALAPPDATA%\SonarSniffer-build\target` (Windows) |
| `RUSTFLAGS` | unset for production (no experimental target-cpu unless validated) |

Helper: `tools/prod_cargo_build.sh` (native CLI) — sources this policy.

## WASM flags (`wasm` branch)

Native-heavy crates (`mbtiles`, `rav1e`, `rusqlite`, `nauticuvs`, …) are
`target.'cfg(not(target_arch = "wasm32"))'` only. The wasm lib exposes `wasm_api`
(`greet`, `version`).

```bash
# scripts/build_wasm.sh
wasm-pack build --target web --out-dir dist/wasm/pkg --release --no-default-features
```

| Flag | Why |
|------|-----|
| `--release` | Production wasm (not debug) |
| `--no-default-features` | No GStreamer/OpenCV |
| `--target web` | Browser `wasm-bindgen` glue |

Optional (experimental, not used in release by default):

```bash
export RUSTFLAGS='--cfg getrandom_backend="wasm_js"'
```

Native installers are **not** built from the `wasm` branch.

## LLM packed self-healing (`ip` branch)

No extra Cargo features. Install assist is **PowerShell** packed into
`SonarSniffer-Setup.exe` via `scripts/lib/SonarSniffer.InstallAssist.psm1`.

| Env | Effect |
|-----|--------|
| `SONARSNIFFER_INSTALL_ASSIST=1` | Enable local Ollama assist + deterministic heal hints |
| `SONARSNIFFER_OLLAMA_URL` | Default `http://127.0.0.1:11434` |
| `SONARSNIFFER_OLLAMA_MODEL` | Default `tinyllama` |

CLI/desktop binaries on `ip` still use the **same** production Cargo flags as `master`
(`--release --no-default-features`).

## Branch → build matrix

| Branch | Primary artifact | Cargo / pack flags |
|--------|------------------|--------------------|
| `master` | CLI zips, MSI/NSIS, Setup.exe | `--release --no-default-features` |
| `wasm` | `dist/wasm/pkg/` | `wasm-pack … --release --no-default-features` |
| `ip` | Setup.exe + InstallAssist.psm1 | Same as master + pack assist module |

## Anti-patterns

- `cargo build` (debug) for smoke/release
- Omitting `--no-default-features` (future default drift)
- Enabling `video-gstreamer` in CI Release without documenting a legacy SKU
- Building wasm without `--release`
