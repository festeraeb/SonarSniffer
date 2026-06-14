//! WebView2 runtime detection (registry + version probe + folder fallback).

#[cfg(windows)]
use std::path::PathBuf;
#[cfg(windows)]
use std::process::Command;

const WEBVIEW2_CLIENT_GUID: &str = r"{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}";

#[derive(Debug, Clone)]
pub struct WebView2Status {
    pub present: bool,
    pub version: Option<String>,
    pub method: &'static str,
}

#[cfg(windows)]
pub fn detect_webview2() -> WebView2Status {
    if let Some(ver) = read_registry_version() {
        return WebView2Status {
            present: true,
            version: Some(ver),
            method: "registry",
        };
    }
    if let Some((ver, _path)) = probe_exe_version() {
        return WebView2Status {
            present: true,
            version: Some(ver),
            method: "exe-version",
        };
    }
    if folder_fallback_present() {
        return WebView2Status {
            present: true,
            version: None,
            method: "folder-fallback",
        };
    }
    WebView2Status {
        present: false,
        version: None,
        method: "none",
    }
}

#[cfg(not(windows))]
pub fn detect_webview2() -> WebView2Status {
    WebView2Status {
        present: false,
        version: None,
        method: "none",
    }
}

#[cfg(windows)]
fn read_registry_version() -> Option<String> {
    use winreg::enums::*;
    use winreg::RegKey;

    let paths = [
        (
            HKEY_LOCAL_MACHINE,
            format!(
                r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{}",
                WEBVIEW2_CLIENT_GUID
            ),
        ),
        (
            HKEY_LOCAL_MACHINE,
            format!(r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{}", WEBVIEW2_CLIENT_GUID),
        ),
    ];
    for (hive, subkey) in paths {
        let root = RegKey::predef(hive);
        if let Ok(key) = root.open_subkey(subkey) {
            if let Ok(pv) = key.get_value::<String, _>("pv") {
                if !pv.is_empty() {
                    return Some(pv);
                }
            }
        }
    }
    None
}

#[cfg(windows)]
fn webview_roots() -> [PathBuf; 2] {
    [
        PathBuf::from(r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application"),
        PathBuf::from(r"C:\Program Files\Microsoft\EdgeWebView\Application"),
    ]
}

#[cfg(windows)]
fn find_webview_exe() -> Option<PathBuf> {
    for root in webview_roots() {
        if !root.is_dir() {
            continue;
        }
        if let Ok(read) = std::fs::read_dir(&root) {
            for entry in read.flatten() {
                let candidate = entry.path().join("msedgewebview2.exe");
                if candidate.is_file() {
                    return Some(candidate);
                }
            }
        }
    }
    None
}

#[cfg(windows)]
fn probe_exe_version() -> Option<(String, PathBuf)> {
    let exe = find_webview_exe()?;
    let output = Command::new(&exe).arg("--version").output().ok()?;
    let text = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if text.is_empty() {
        return None;
    }
    Some((text, exe))
}

#[cfg(windows)]
fn folder_fallback_present() -> bool {
    webview_roots().iter().any(|p| p.is_dir())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detect_returns_struct() {
        let s = detect_webview2();
        assert!(matches!(
            s.method,
            "registry" | "exe-version" | "folder-fallback" | "none"
        ));
    }
}
