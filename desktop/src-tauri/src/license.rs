//! License gating — 30-day trial from first install + permanent 20-digit unlock code.
//!
//! Unlock format: 20 digits total. Valid when the first ten digit positions match the
//! embedded prefix (any characters/spaces/dashes between digits are ignored).
//! The prefix is not shown in the UI.

use std::path::PathBuf;

use chrono::{NaiveDate, Utc};
use serde::{Deserialize, Serialize};

const TRIAL_DAYS: i64 = 30;
const DEFAULT_CONTACT_EMAIL: &str = "nautik9@cesarops.com";
const UNLOCK_LEN: usize = 20;
const PREFIX_LEN: usize = 10;

// Digit values for the required 10-digit prefix (not stored as a plain string).
const PREFIX_DIGITS: [u8; PREFIX_LEN] = [8, 1, 0, 6, 9, 4, 0, 5, 3, 9];

#[derive(Debug, Serialize, Deserialize)]
struct LicenseFile {
    /// ISO date (YYYY-MM-DD) of the very first launch / install.
    trial_start_utc: String,
    /// Set to true once a valid permanent key has been entered.
    unlocked: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct LicenseStatus {
    /// `"trial"` | `"expired"` | `"unlocked"`
    pub state: String,
    /// Days left in trial; -1 when state is `"unlocked"`.
    pub days_remaining: i64,
    /// Email address shown to users for obtaining a permanent key.
    pub contact_email: String,
    /// Public builds require a key after the trial expires.
    pub key_required: bool,
    /// Private builds bypass licensing entirely.
    pub private_build: bool,
    /// First-install date (YYYY-MM-DD) once the app has been run.
    pub first_installed: Option<String>,
}

pub fn check_license(app_data_dir: PathBuf) -> LicenseStatus {
    if is_private_build() {
        return LicenseStatus {
            state: "unlocked".to_string(),
            days_remaining: -1,
            contact_email: contact_email(),
            key_required: false,
            private_build: true,
            first_installed: None,
        };
    }

    let path = license_path(&app_data_dir);

    let lf: LicenseFile = if path.exists() {
        std::fs::read_to_string(&path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_else(new_trial_file)
    } else {
        let f = new_trial_file();
        let _ = std::fs::create_dir_all(&app_data_dir);
        let _ = std::fs::write(&path, serde_json::to_string_pretty(&f).unwrap_or_default());
        f
    };

    let first_installed = Some(lf.trial_start_utc.clone());

    if lf.unlocked {
        return LicenseStatus {
            state: "unlocked".to_string(),
            days_remaining: -1,
            contact_email: contact_email(),
            key_required: false,
            private_build: false,
            first_installed,
        };
    }

    let today = Utc::now().date_naive();
    let remaining = days_remaining(&lf.trial_start_utc, today);

    if remaining > 0 {
        LicenseStatus {
            state: "trial".to_string(),
            days_remaining: remaining,
            contact_email: contact_email(),
            key_required: false,
            private_build: false,
            first_installed,
        }
    } else {
        LicenseStatus {
            state: "expired".to_string(),
            days_remaining: 0,
            contact_email: contact_email(),
            key_required: true,
            private_build: false,
            first_installed,
        }
    }
}

/// Returns an error if the license is not active (trial expired and not unlocked).
pub fn ensure_licensed(app_data_dir: PathBuf) -> Result<(), String> {
    let status = check_license(app_data_dir);
    if status.private_build || status.state == "unlocked" || status.state == "trial" {
        return Ok(());
    }
    Err(format!(
        "Trial expired. Enter a valid 20-digit license code or contact {} for a key.",
        status.contact_email
    ))
}

pub fn activate_license(key: String, app_data_dir: PathBuf) -> Result<(), String> {
    if is_private_build() {
        return Ok(());
    }

    if !is_valid_unlock_key(&key) {
        return Err(format!(
            "Invalid license code. Contact {} to obtain a key.",
            contact_email()
        ));
    }

    let path = license_path(&app_data_dir);

    let mut lf: LicenseFile = if path.exists() {
        std::fs::read_to_string(&path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_else(new_trial_file)
    } else {
        new_trial_file()
    };

    // Preserve original first-install date; only flip the permanent unlock flag.
    lf.unlocked = true;
    let _ = std::fs::create_dir_all(&app_data_dir);
    std::fs::write(&path, serde_json::to_string_pretty(&lf).unwrap_or_default())
        .map_err(|e| format!("Could not save license: {e}"))?;

    Ok(())
}

/// Whether this machine has been run before (license file exists).
pub fn has_been_installed(app_data_dir: PathBuf) -> bool {
    license_path(&app_data_dir).exists()
}

fn is_valid_unlock_key(key: &str) -> bool {
    let digits: Vec<u8> = key
        .chars()
        .filter(|c| c.is_ascii_digit())
        .filter_map(|c| c.to_digit(10).map(|d| d as u8))
        .collect();

    if digits.len() != UNLOCK_LEN {
        return false;
    }

    digits[..PREFIX_LEN] == PREFIX_DIGITS
}

fn is_private_build() -> bool {
    matches!(
        option_env!("SONARSNIFFER_PRIVATE_BUILD"),
        Some("1") | Some("true") | Some("TRUE") | Some("yes") | Some("YES")
    )
}

fn contact_email() -> String {
    option_env!("SONARSNIFFER_LICENSE_EMAIL")
        .unwrap_or(DEFAULT_CONTACT_EMAIL)
        .to_string()
}

fn license_path(app_data_dir: &PathBuf) -> PathBuf {
    app_data_dir.join("license.json")
}

fn new_trial_file() -> LicenseFile {
    LicenseFile {
        trial_start_utc: Utc::now().date_naive().to_string(),
        unlocked: false,
    }
}

fn days_remaining(trial_start: &str, today: NaiveDate) -> i64 {
    let start = NaiveDate::parse_from_str(trial_start, "%Y-%m-%d").unwrap_or(today);
    let elapsed = (today - start).num_days();
    (TRIAL_DAYS - elapsed).max(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn prefix_string() -> String {
        PREFIX_DIGITS
            .iter()
            .map(|d| char::from(b'0' + *d))
            .collect()
    }

    fn valid_unlock_key() -> String {
        format!("{}1234567890", prefix_string())
    }

    #[test]
    fn accepts_twenty_digit_code_with_matching_prefix() {
        let key = valid_unlock_key();
        assert!(is_valid_unlock_key(&key));
        assert!(is_valid_unlock_key(&format!(
            "{}-1234-5678-90",
            &key[..10]
        )));
        assert!(is_valid_unlock_key(&format!(
            "{} {} {} {}",
            &key[0..4],
            &key[4..8],
            &key[8..12],
            &key[12..]
        )));
    }

    #[test]
    fn rejects_wrong_prefix_or_length() {
        assert!(!is_valid_unlock_key(&prefix_string()));
        assert!(!is_valid_unlock_key("12345678901234567890"));
        assert!(!is_valid_unlock_key(&format!("{}123456789", prefix_string())));
    }

    #[test]
    fn any_ten_digit_suffix_unlocks_when_prefix_matches() {
        assert!(is_valid_unlock_key(&format!("{}0000000000", prefix_string())));
        assert!(is_valid_unlock_key(&format!("{}9999999999", prefix_string())));
    }
}
