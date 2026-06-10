# SonarSniffer — top-tier punch list

Status as of **v0.8.8 overnight build** (2026-06-09). See `docs/IMPLEMENTATION_NOTES.md` for debug steps.

## Done (v0.8.6–0.8.8)

- [x] Dynamic stitch flip + layout picker + scrolling video + v0.8.7 release
- [x] KMZ segment ExtendedData + balloon (depth, speed, ping range)
- [x] Video HUD (`overlay_depth` / `overlay_speed` / `overlay_gps`)
- [x] **Nadir fill hardening** — wider downscan strip on single-wing (24% vs 16%)
- [x] **Geographic mosaic** — engine `EngineStitchConfig` honours layout pair + transducer offset
- [x] **Single library crate** — desktop depends on `sonarsniffer`; `tools/publish.ps1` blocks mirror drift
- [x] **MBTiles** — stitched port+star rows when layout pair resolved
- [x] **KMZ balloon** — per-segment BalloonStyle + `detections.kml` sidecar
- [x] **Target detection** — auto-run when `detectionMode` set → JSON, GeoJSON, KML, viewer
- [x] **Per-wing TVG** — discovery noise-floor scale in MBTiles (`perWingTvg`)
- [x] **Channel alignment UI** — port/star flip checkboxes → `channelAlignments`
- [x] **Velocity-aware video** — `videoSpeedMode: velocity`
- [x] **Transducer offset** — `transducerOffsetM` in geographic engine
- [x] **Multi-file mosaic** — plan stub (`extraInputFiles` → `multi_mosaic_plan.json`)
- [x] **Export presets** — `export_presets.rs` + desktop dropdown

## Verify tomorrow (human review)

1. Run `.\tools\regression_smoke.ps1` — three regression files
2. Holloway / Sonar010 `mosaic_combined.png` — nadir centre, no ribbon
3. Google Earth `track.kmz` — segment balloons + optional `detections.kml`
4. Video — readable / survey / velocity scroll modes
5. CI **v0.8.7** release assets on GitHub

## Follow-up (post-review)

- [ ] Wire `multi_mosaic::merge_parsed_runs` pixel merge
- [ ] 2D blob target detection on stitched mosaic
- [ ] Golden PNG diff in regression script
- [ ] Push **v0.8.8** after sign-off
