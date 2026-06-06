# SonarSniffer Mosaic Engine Fixes — v0.9 Spec

**Author:** Thom Hadfield — NautiDog Sailing / Cesarops  
**Date:** 2026-06-06  
**Status:** Spec ready, implementation pending

## Three issues (priority order)

### 1. CRITICAL — Turn floating/weave (arc-aware projection)

**Problem:** On turns, sonar tiles fan outward because each tile is projected 
perpendicular to the *instantaneous* GPS heading. During a turn, the heading 
changes between pings, so consecutive tiles diverge — leaving gaps on the 
inside of turns and overlaps on the outside. Creates the "floating ribbon" 
artifact visible in Google Earth.

**Root cause:** `src/mosaic/engine.rs` computes tile corners as:
```
port_corner  = ping_pos + rotate(heading + 90°) × range
star_corner  = ping_pos + rotate(heading - 90°) × range
```
This assumes straight-line travel. On turns, it's wrong.

**Fix — Arc-aware tile projection:**

For each tile (group of N pings):
1. Compute the **heading at the tile's leading edge** and **trailing edge**.
2. If the heading change exceeds a threshold (~2°), treat the tile as an arc:
   - Leading edge corners use `heading_start ± 90°`
   - Trailing edge corners use `heading_end ± 90°`
   - The tile becomes a trapezoid (not a rectangle) — which `gx:LatLonQuad` 
     already supports perfectly.
3. **Adjacent tiles share their edge exactly** by construction: tile N's 
   trailing edge = tile N+1's leading edge (same corners, same heading).

This eliminates both the turn weave AND the gap lines in one change, because:
- Trapezoidal tiles follow the arc naturally (no fan-out)
- Shared edges mean zero gap by geometry

**Detection:** Heading rate of change per ping. When `abs(heading[i] - heading[i-1]) > 1.5°`, that ping is "in a turn" and gets arc treatment.

**Where:** `src/mosaic/engine.rs` — the tile projection loop.

---

### 2. MINOR — Gap lines between overlay tiles

**Problem:** Thin dark lines between adjacent KMZ segments. Originally added 
as a hack to prevent fractaling on corners.

**Fix:** Remove the gap spacing entirely once arc-aware projection is 
implemented. The arc projection inherently prevents fractaling because tile 
edges are geometrically continuous (shared corners). The KMZ already produces 
0.000m gaps in the coordinate data — the visible gaps are likely in the PNG 
mosaic rasterizer (1-pixel border between tiles in the grid), not the KMZ 
LatLonQuad path.

**Where:** Likely a `-1` or `+1` offset in the tile rasterization bounds in 
`engine.rs`. May also be a sub-pixel rounding issue in the WebP tile renderer.

---

### 3. MINOR — Interleaving instead of overlay on crossing passes

**Problem:** When the boat crosses over a previous pass, newer tiles stack 
opaquely on top of older ones (last-write-wins). A professional tool should 
blend or select the best data at each pixel.

**Fix — Quality-weighted compositing:**

At each pixel in the mosaic grid, when multiple passes contribute:
1. Score each contribution by **distance from nadir** (closer = higher 
   resolution = better quality).
2. **Take the best score** (not alpha blend — sonar data shouldn't be 
   averaged, it should be selected). This is "closest to nadir wins."
3. For the KMZ tiles: use `<drawOrder>` based on distance-to-nadir quality, 
   so Google Earth naturally shows the better data on top.

Alternative (simpler, less correct): reverse the draw order so the first pass 
is on top (first-pass-wins). This at least prevents a sloppy re-pass from 
overwriting good earlier data.

**Where:** `src/mosaic/engine.rs` — the pixel write loop (currently just 
overwrites `grid[row][col]`). Add a parallel quality grid and conditional write.

---

## Implementation order

1. Arc-aware projection (fixes #1 and #2 together)
2. Remove gap hack (verify #2 is gone)
3. Nadir-distance pixel selection (fixes #3)

## Test files

- **Holloway.RSD** (GT54 UHD) — has clear turns + one crossing pass
- **Millers Folley Cove.RSD** — long linear runs with gentle curves
- **Sonar010.RSD** (GT51) — single-arm, will test arc on tight turns

## Validation

Open KMZ in Google Earth, check:
- [ ] No floating/weave on turns
- [ ] No gap lines between segments
- [ ] Crossing passes show best-quality pixel (nadir preference)
- [ ] Tile continuity: zoom in on segment boundaries, no visible seam
