# v0.8.8 overnight implementation — debug checklist

Review these in order tomorrow with human eyes on mosaics + Google Earth.

## Regression

```powershell
.\tools\regression_smoke.ps1
```

Outputs under `%LOCALAPPDATA%\sonar-regression\`. Check `regression_summary.json` for layout id, confidence, port/star pair.

| File | Expect |
|------|--------|
| Millers | butterfly ch4+ch3, high confidence |
| Holloway | butterfly, port flip true |
| Sonar010 | single_wing ch4, downscan nadir fill |

## Visual review

1. `mosaic_combined.png` — nadir at centre, no hard seam on Sonar010
2. `mosaic_geographic.png` — engine uses `stitch_layout_id` channels (see stderr `[engine::build_mosaic]`)
3. `track.kmz` — segment balloon shows depth/speed; ExtendedData in placemark
4. `detections.kml` — only if `detectionMode` set (e.g. `basic`)
5. Scrolling video with `videoSpeedMode: velocity` — faster on straightaways

## New pipeline options

| Option | Purpose |
|--------|---------|
| `exportPreset` | `google_earth` \| `reefmaster` \| `publication` |
| `transducerOffsetM` | GT51 Y-cable metres in geographic engine |
| `perWingTvg` | MBTiles + mosaic wing TVG from discovery noise floor |
| `detectionMode` | `basic` \| `advanced` \| `off` |
| `extraInputFiles` | Writes `multi_mosaic/multi_mosaic_plan.json` (stub) |
| `videoSpeedMode` | `velocity` for GPS-weighted scroll |

## Desktop UI additions

- Export preset dropdown
- Target detection toggle
- Video overlays (depth/speed/GPS)
- Per-wing flip overrides (port/star)

## Known gaps (intentional stubs)

- `multi_mosaic::merge_parsed_runs` — plan only, no unified grid yet
- Target detection — run-length threshold, not 2D blob on mosaic

## Build

```powershell
$env:CARGO_TARGET_DIR = "$env:LOCALAPPDATA\SonarSniffer-build\target"
cd R:\sonarsniffer
.\tools\publish.ps1
```

Library code lives in `src/` only. The desktop app depends on the `sonarsniffer` crate — do not copy sources into `desktop/src-tauri/src/`.
