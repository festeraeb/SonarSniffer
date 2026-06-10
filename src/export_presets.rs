//! Named export presets — one-click pipeline option bundles.
//!
//! DEBUG tomorrow: verify each preset against Millers / Holloway / Sonar010 expectations.

use crate::outputs::PipelineOptions;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExportPreset {
    Default,
    GoogleEarth,
    ReefMasterStyle,
    Publication,
}

impl ExportPreset {
    pub fn parse(s: &str) -> Self {
        match s.to_lowercase().replace('_', "-").as_str() {
            "google-earth" | "googleearth" | "ge" => Self::GoogleEarth,
            "reefmaster" | "reefmaster-style" | "reef" => Self::ReefMasterStyle,
            "publication" | "pub" => Self::Publication,
            _ => Self::Default,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Default => "default",
            Self::GoogleEarth => "google_earth",
            Self::ReefMasterStyle => "reefmaster",
            Self::Publication => "publication",
        }
    }
}

/// Apply toggles for a named preset (mutates `options` in place).
pub fn apply_export_preset(preset: ExportPreset, options: &mut PipelineOptions) {
    match preset {
        ExportPreset::Default => {}
        ExportPreset::GoogleEarth => {
            options.kml = true;
            options.kmz = true;
            options.mosaic = true;
            options.web_viewer = true;
            options.mbtiles = true;
            options.video = false;
            options.arcgis = false;
            options.waterfall = false;
            options.nadir_mode = "fill".to_string();
            options.colormap = "amber".to_string();
            options.remove_water_column = true;
        }
        ExportPreset::ReefMasterStyle => {
            options.mosaic = true;
            options.waterfall = true;
            options.curvelet_denoise = true;
            options.curvelet_auto = true;
            options.remove_water_column = true;
            options.nadir_mode = "stitch".to_string();
            options.kmz = false;
            options.mbtiles = false;
            options.web_viewer = false;
            options.video = false;
            options.colormap = "grayscale".to_string();
        }
        ExportPreset::Publication => {
            options.video = true;
            options.mosaic = true;
            options.kmz = true;
            options.curvelet_denoise = false;
            options.colormap = "viridis".to_string();
            options.overlay_depth = true;
            options.overlay_speed = true;
            options.video_speed_mode = "readable".to_string();
            options.video_fps = 24;
        }
    }
}
