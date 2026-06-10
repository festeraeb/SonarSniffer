# SonarSniffer agent notes

## Stitch orientation (critical)

Read `.cursor/rules/stitch-orientation.mdc` before changing `channel_discovery.rs` or stitch paths in `outputs.rs`.

**Summary:** No hardcoded port/star flips. Probe on `samples[probe_skip..]` via `effective_flip_nadir_skip`, geometric mirror, then shallow port correction when `parser_rev && probe_skip < 45`.

**Regression mosaics:** Millers Folley Cove, Holloway, Sonar010 (GT51UHD/GT54).

**Export layouts:** UHD classic = ch4+ch5 paired. GT51 (medium-CHIRP, Y-cable) often exports ch4+ch6 only (sidescan + downscan) — never butterfly ch6; use `gt51_single_wing_pair` + downscan nadir fill. Shallow nadir gap (`<45` samples): trust `profile.nadir_edge` over post-strip gap votes.

**Layout confidence:** `propose_stitch_layouts()` — if `needs_confirmation` and no `stitchLayoutId`, pipeline stops before mosaic/video; desktop shows picker.

**Video:** scrolling waterfall — `readable` (~2 pings/s) or `survey` (match file ping rate); bottom-fill then scroll up (`video_enhanced/scroll.rs`).

**Host tuning:** `host_profile.rs` probes CPU/RAM/output path and suggests pipeline tiers (`--fast`, `--suggested` on CLI). Regression: `.\tools\regression_smoke.ps1 -Fast`.

## Build

Network share `R:\sonarsniffer\target` may deny writes. Build under `%LOCALAPPDATA%\SonarSniffer-build` with `CARGO_TARGET_DIR` set.

**Single library crate:** edit `src/` only. Desktop is a thin Tauri shell (`desktop/src-tauri/src/{main,lib,commands}.rs`). Before release run `.\tools\publish.ps1`.
