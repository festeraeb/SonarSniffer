//! Host capability probe and pipeline tuning suggestions.
//!
//! Combines CPU/RAM/path signals with optional sonar survey hints to recommend
//! `PipelineOptions` tiers (fast / balanced / full).

use crate::outputs::PipelineOptions;
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::sync::OnceLock;

static HOST_CACHE: OnceLock<HostProfile> = OnceLock::new();

/// Performance tier derived from host RAM + cores.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PerformanceTier {
    Low,
    Mid,
    High,
}

impl PerformanceTier {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Low => "low",
            Self::Mid => "mid",
            Self::High => "high",
        }
    }
}

/// Host machine snapshot (cached for process lifetime).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct HostProfile {
    pub logical_cores: usize,
    pub total_ram_gb: f64,
    pub tier: PerformanceTier,
    pub suggested_rayon_threads: usize,
    pub platform: String,
    pub jemalloc_active: bool,
}

/// Optional context from a parsed or probed survey file.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SonarSurveyHint {
    pub ping_count: usize,
    pub format: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub hardware: Option<String>,
}

/// Named tuning preset.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SettingsTier {
    Fast,
    Balanced,
    Full,
    Auto,
}

impl SettingsTier {
    pub fn parse(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "fast" | "smoke" | "quick" => Self::Fast,
            "balanced" | "default" => Self::Balanced,
            "full" | "quality" | "max" => Self::Full,
            _ => Self::Auto,
        }
    }
}

/// Full recommendation returned to CLI / desktop.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SuggestedSettings {
    pub host: HostProfile,
    pub survey: SonarSurveyHint,
    pub tier: SettingsTier,
    pub resolved_tier: SettingsTier,
    pub output_on_network_share: bool,
    pub options: PipelineOptions,
    pub notes: Vec<String>,
}

pub fn probe_host() -> HostProfile {
    HOST_CACHE.get_or_init(probe_host_uncached).clone()
}

pub fn init_runtime() {
    let host = probe_host();
    let threads = host.suggested_rayon_threads.max(1);
    let _ = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global();
}

fn probe_host_uncached() -> HostProfile {
    let logical_cores = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);
    let total_ram_gb = detect_total_ram_gb();
    let tier = classify_tier(logical_cores, total_ram_gb);
    let suggested_rayon_threads = match tier {
        PerformanceTier::Low => (logical_cores.saturating_sub(1)).max(1),
        PerformanceTier::Mid => logical_cores.saturating_sub(1).max(2),
        PerformanceTier::High => logical_cores.max(2),
    };

    HostProfile {
        logical_cores,
        total_ram_gb,
        tier,
        suggested_rayon_threads,
        platform: crate::deps::platform_id().to_string(),
        jemalloc_active: jemalloc_enabled(),
    }
}

fn classify_tier(cores: usize, ram_gb: f64) -> PerformanceTier {
    if cores >= 8 && ram_gb >= 24.0 {
        PerformanceTier::High
    } else if cores >= 4 && ram_gb >= 12.0 {
        PerformanceTier::Mid
    } else {
        PerformanceTier::Low
    }
}

fn detect_total_ram_gb() -> f64 {
    #[cfg(target_os = "linux")]
    {
        if let Ok(text) = std::fs::read_to_string("/proc/meminfo") {
            for line in text.lines() {
                if let Some(kb) = line.strip_prefix("MemTotal:") {
                    if let Ok(k) = kb.trim().split_whitespace().next().unwrap_or("0").parse::<f64>()
                    {
                        return (k / (1024.0 * 1024.0)).max(1.0);
                    }
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        if let Ok(out) = std::process::Command::new("powershell")
            .creation_flags(CREATE_NO_WINDOW)
            .args([
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ])
            .output()
        {
            if out.status.success() {
                let text = String::from_utf8_lossy(&out.stdout);
                if let Ok(bytes) = text.trim().parse::<f64>() {
                    return (bytes / (1024.0 * 1024.0 * 1024.0)).max(1.0);
                }
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        if let Ok(out) = std::process::Command::new("sysctl")
            .args(["-n", "hw.memsize"])
            .output()
        {
            if out.status.success() {
                let text = String::from_utf8_lossy(&out.stdout);
                if let Ok(bytes) = text.trim().parse::<f64>() {
                    return (bytes / (1024.0 * 1024.0 * 1024.0)).max(1.0);
                }
            }
        }
    }

    16.0
}

pub fn path_on_network_share(path: &Path) -> bool {
    let s = path.display().to_string();
    s.starts_with("\\\\") || s.starts_with("//")
}

pub fn auto_tier(host: &HostProfile, survey: &SonarSurveyHint, output_on_network: bool) -> SettingsTier {
    if output_on_network || host.tier == PerformanceTier::Low {
        return SettingsTier::Fast;
    }
    if survey.ping_count > 60_000 || host.tier == PerformanceTier::High {
        return SettingsTier::Balanced;
    }
    if host.tier == PerformanceTier::Mid {
        return SettingsTier::Balanced;
    }
    SettingsTier::Fast
}

pub fn suggest_settings(
    tier: SettingsTier,
    survey: &SonarSurveyHint,
    output_dir: Option<&Path>,
) -> SuggestedSettings {
    init_runtime();
    let host = probe_host();
    let output_on_network_share = output_dir.map(path_on_network_share).unwrap_or(false);
    let resolved = if tier == SettingsTier::Auto {
        auto_tier(&host, survey, output_on_network_share)
    } else {
        tier
    };

    let mut notes = Vec::new();
    let mut options = PipelineOptions::default();

    match resolved {
        SettingsTier::Fast => apply_fast(&mut options, &host, survey, output_on_network_share, &mut notes),
        SettingsTier::Balanced => {
            apply_balanced(&mut options, &host, survey, output_on_network_share, &mut notes)
        }
        SettingsTier::Full => apply_full(&mut options, &host, &mut notes),
        SettingsTier::Auto => unreachable!("resolved tier cannot be Auto"),
    }

    SuggestedSettings {
        host,
        survey: survey.clone(),
        tier,
        resolved_tier: resolved,
        output_on_network_share,
        options,
        notes,
    }
}

fn apply_fast(
    options: &mut PipelineOptions,
    host: &HostProfile,
    survey: &SonarSurveyHint,
    network_out: bool,
    notes: &mut Vec<String>,
) {
    options.video = false;
    options.mosaic = true;
    options.kml = true;
    options.kmz = false;
    options.mbtiles = false;
    options.waterfall = false;
    options.arcgis = false;
    options.web_viewer = false;
    options.curvelet_denoise = false;
    options.mosaic_max_grid_dim = Some(4096);

    notes.push(format!(
        "Fast tier: mosaic + KML only ({:.0} GB RAM, {} cores, {} threads).",
        host.total_ram_gb, host.logical_cores, host.suggested_rayon_threads
    ));
    if network_out {
        notes.push("Network output path — skipped MBTiles/KMZ/viewer to reduce I/O.".into());
    }
    if survey.ping_count > 50_000 {
        notes.push(format!(
            "Large survey ({} pings) — coarser mosaic grid cap (4096 px).",
            survey.ping_count
        ));
    }
}

fn apply_balanced(
    options: &mut PipelineOptions,
    host: &HostProfile,
    survey: &SonarSurveyHint,
    network_out: bool,
    notes: &mut Vec<String>,
) {
    options.video = false;
    options.mosaic = true;
    options.kml = true;
    options.kmz = !network_out;
    options.mbtiles = !network_out && host.tier != PerformanceTier::Low;
    options.waterfall = true;
    options.arcgis = false;
    options.web_viewer = !network_out;
    options.curvelet_denoise = host.tier == PerformanceTier::High;
    options.mosaic_max_grid_dim = Some(if survey.ping_count > 60_000 { 6144 } else { 8192 });

    notes.push(format!(
        "Balanced tier: mosaic + waterfall + {} ({} cores).",
        if network_out {
            "KML only on network share"
        } else {
            "KMZ + viewer"
        },
        host.suggested_rayon_threads
    ));
}

fn apply_full(options: &mut PipelineOptions, host: &HostProfile, notes: &mut Vec<String>) {
    *options = PipelineOptions::default();
    options.mosaic_max_grid_dim = Some(8192);
    notes.push(format!(
        "Full tier: all default exports ({} cores, {:.0} GB RAM).",
        host.suggested_rayon_threads, host.total_ram_gb
    ));
}

pub fn survey_hint_from_parse(ping_count: usize, format: &str) -> SonarSurveyHint {
    SonarSurveyHint {
        ping_count,
        format: format.to_string(),
        hardware: None,
    }
}

pub fn jemalloc_enabled() -> bool {
    cfg!(all(not(debug_assertions), target_os = "linux", feature = "jemalloc"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tier_classification() {
        assert_eq!(classify_tier(12, 32.0), PerformanceTier::High);
        assert_eq!(classify_tier(4, 16.0), PerformanceTier::Mid);
        assert_eq!(classify_tier(2, 8.0), PerformanceTier::Low);
    }

    #[test]
    fn fast_settings_skip_heavy_exports() {
        let host = HostProfile {
            logical_cores: 4,
            total_ram_gb: 8.0,
            tier: PerformanceTier::Low,
            suggested_rayon_threads: 3,
            platform: "test".into(),
            jemalloc_active: false,
        };
        let survey = SonarSurveyHint {
            ping_count: 80_000,
            format: "Garmin RSD".into(),
            hardware: None,
        };
        let s = suggest_settings(SettingsTier::Fast, &survey, None);
        assert!(!s.options.mbtiles);
        assert!(!s.options.web_viewer);
        assert!(s.options.mosaic);
    }
}
