use serde::{Deserialize, Serialize};
use anyhow::Result;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SettingsManager {
    pub default_parser: String,
    pub default_encoder: String,
    pub enable_telemetry: bool,
    pub telemetry_send_interval_minutes: i32,
    pub export_format: String,
    pub quality_preset: String,
    pub video_fps: i32,
    pub video_height: i32,
    pub hardware_acceleration: bool,
}

impl Default for SettingsManager {
    fn default() -> Self {
        SettingsManager {
            default_parser: "rust".to_string(),
            default_encoder: "gstreamer".to_string(),
            enable_telemetry: true,
            telemetry_send_interval_minutes: 5,
            export_format: "mp4".to_string(),
            quality_preset: "high".to_string(),
            video_fps: 30,
            video_height: 1080,
            hardware_acceleration: true,
        }
    }
}

impl SettingsManager {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::json!({}))
    }

    pub fn update_from_json(&mut self, json: serde_json::Value) -> Result<()> {
        if let Some(parser) = json.get("default_parser").and_then(|v| v.as_str()) {
            self.default_parser = parser.to_string();
        }
        if let Some(encoder) = json.get("default_encoder").and_then(|v| v.as_str()) {
            self.default_encoder = encoder.to_string();
        }
        if let Some(telemetry) = json.get("enable_telemetry").and_then(|v| v.as_bool()) {
            self.enable_telemetry = telemetry;
        }
        if let Some(fps) = json.get("video_fps").and_then(|v| v.as_i64()) {
            self.video_fps = fps as i32;
        }
        if let Some(height) = json.get("video_height").and_then(|v| v.as_i64()) {
            self.video_height = height as i32;
        }
        if let Some(hw_accel) = json.get("hardware_acceleration").and_then(|v| v.as_bool()) {
            self.hardware_acceleration = hw_accel;
        }
        if let Some(quality) = json.get("quality_preset").and_then(|v| v.as_str()) {
            self.quality_preset = quality.to_string();
        }
        Ok(())
    }

    pub fn validate(&self) -> Result<()> {
        if self.video_fps < 1 || self.video_fps > 120 {
            return Err(anyhow::anyhow!("FPS must be between 1 and 120"));
        }
        if self.video_height < 480 || self.video_height > 4320 {
            return Err(anyhow::anyhow!("Height must be between 480 and 4320"));
        }
        match self.quality_preset.as_str() {
            "low" | "medium" | "high" | "ultra" => Ok(()),
            _ => Err(anyhow::anyhow!("Invalid quality preset")),
        }
    }
}
