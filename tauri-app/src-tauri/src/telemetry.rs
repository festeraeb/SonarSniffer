use serde::{Deserialize, Serialize};
use chrono::Utc;
use crate::db::ErrorReport;

#[derive(Debug)]
pub struct TelemetryManager {
    enabled: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TelemetryEvent {
    pub event_type: String,
    pub timestamp: String,
    pub data: serde_json::Value,
}

impl TelemetryManager {
    pub fn new(enabled: bool) -> Self {
        TelemetryManager { enabled }
    }

    pub fn is_enabled(&self) -> bool {
        self.enabled
    }

    pub fn set_enabled(&mut self, enabled: bool) {
        self.enabled = enabled;
    }

    pub fn create_error_report(
        &self,
        error_type: &str,
        error_message: &str,
        component: &str,
        severity: &str,
        details: Option<serde_json::Value>,
    ) -> ErrorReport {
        ErrorReport {
            timestamp: Utc::now().to_rfc3339(),
            error_type: error_type.to_string(),
            error_message: error_message.to_string(),
            component: component.to_string(),
            platform: std::env::consts::OS.to_string(),
            severity: severity.to_string(),
            details,
        }
    }

    pub fn should_report(&self) -> bool {
        self.enabled
    }
}
