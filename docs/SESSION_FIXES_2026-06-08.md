# Session fixes (2026-06-08) — merged into v0.8.6

# Session fixes (2026-06-08) — local `R:\sonarsniffer` only

These changes exist on the **network worktree** `R:\sonarsniffer` but are **not** on [GitHub master](https://github.com/festeraeb/SonarSniffer) or `R:\_sonarsniffer_ci` as of this date. They must be ported after syncing the rav1e video base.

---

## 1. Dynamic channel stitch orientation (Garmin nadir probe)

**Problem:** Static rules (`port always flip`) fail across Garmin transducer / generation / firmware variants.

**Files:**
- `src/channel_discovery.rs` — §13b
- `desktop/src-tauri/src/channel_discovery.rs` — §13b

**What was added:**
- `probe_nadir_edge_for_channel()` — sliding-window nadir edge on post-parse pings
- `resolve_stitch_flip()` — decision order: user alignment overrides → discovery profile (nadir edge + spatial role) → live probe → gradient vote fallback
- `stitch_flip_for_half()` — maps `NadirEdge::Left|Right|Center` to port/star mirror
- Logs: `[stitch-flip] ch{N} role=… nadir=… parser_rev=… → flip=…`

**How:** Replaced parser `reversed_channels` heuristics with per-file, per-channel probe at stitch time.

---

## 2. Stitch flip wired through all geospatial outputs

**Files:**
- `src/outputs.rs`
- `desktop/src-tauri/src/outputs.rs`

**What changed:**
- `should_flip()` delegates to `channel_discovery::resolve_stitch_flip()`
- `render_stitched_overlay_strip()`, `render_sidescan_stitched()`, `build_stitched_mosaic_rgb()` take `parsed` + `discovery` instead of `reversed_channels`
- `write_mosaic_per_channel()`, `write_kmz()`, `write_native_viewer()`, `generate_viewer_sonar_overlays()` take `discovery`
- `build_outputs()` hoists `discover_and_profile()` once when mosaic/kmz/viewer enabled; threads `discovery_ref` to all writers

**Effect:** KMZ segments, web viewer overlays, `mosaic_combined.png`, and video mosaic path share one orientation decision per file.

---

## 3. KMZ / viewer segment sizing (flat overlays)

**Files:** `src/outputs.rs`, `desktop/src-tauri/src/outputs.rs`

**What changed:**
- KMZ segment length: `raw_base.clamp(12, 48)` (was 80–400) — shorter strips follow track curves, less “ribbon standing on edge”
- Viewer segment length: `raw_base.clamp(40, 100)` (was 200+)

---

## 4. Enhanced mosaic video export

**Files:**
- `src/video.rs`, `desktop/src-tauri/src/video.rs`
- `src/video_enhanced/mod.rs`, `desktop/.../video_enhanced/mod.rs`
- `build_stitched_mosaic_rgb()` in both `outputs.rs`

**What changed:**
- Video can render from `build_stitched_mosaic_rgb()` (same EGN/TVG/nadir pipeline as `mosaic_combined.png`) via `render_mosaic_waterfall()`
- Video thread passes `discover_and_profile()` for correct stitch orientation

**Note:** On this tree video still uses **GStreamer** when `video-gstreamer` is enabled (see sync section below).

---

## 5. UI / pipeline (earlier in same session)

**Files:** `desktop/ui/app.js`, `index.html`, `styles.css`, `desktop/src-tauri/src/lib.rs`

**What changed:**
- Removed standalone SoundTiles nav; inline alignment in full pipeline
- Progress bar (`pipeline-progress`, `video-progress`)
- “Open output folder” on completion
- Fixed Tauri JSON: `outputDir`, `curveletDenoise` camelCase
- SoundTiles inline uses `find_sidescan_pair()` not highest ping-count channel
- Fixed missing `#[tauri_command]` on `discover_channels`

---

## Sync status vs GitHub / `_sonarsniffer_ci`

| Capability | `R:\sonarsniffer` (this session) | GitHub / `R:\_sonarsniffer_ci` |
|------------|----------------------------------|--------------------------------|
| rav1e AV1 default video | **No** — GStreamer default in root `Cargo.toml` | **Yes** — pure Rust, Mac-safe |
| `mp4_av1.rs` muxer | Missing | Present |
| Dynamic stitch flip | **Yes** | **No** — still `reversed_channels` |
| Mosaic-based video | **Yes** | Unknown / likely older path |
| Desktop version | 0.77.5 | 0.8.5 |

**Recommended merge order:**
1. Use `R:\_sonarsniffer_ci` or `git clone https://github.com/festeraeb/SonarSniffer` as base (rav1e, v0.8.5).
2. Port §13b + outputs wiring from this doc into that tree.
3. Re-run `cargo check` on Windows desktop + CLI without `--features video-gstreamer`.

**Terminology:** README refers to **rav1e** (pure-Rust AV1 encoder), not a UI framework named “Ravel”. GStreamer remains optional via `--features video-gstreamer` for legacy H.264 / NVENC.
