// Runtime dependency preflight — GStreamer is mandatory (not bundled in the installer).

use serde::{Deserialize, Serialize};
use std::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DependencyItem {
    pub id: String,
    pub name: String,
    pub required: bool,
    pub satisfied: bool,
    pub version: Option<String>,
    pub message: String,
    pub download_url: Option<String>,
    pub install_hint: Option<String>,
    pub can_auto_install: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreflightReport {
    pub platform: String,
    /// All required items satisfied — app may run full pipeline including video.
    pub ready: bool,
    pub gstreamer_required: bool,
    pub items: Vec<DependencyItem>,
    pub summary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DependencyStatus {
    pub gstreamer_available: bool,
    pub gstreamer_version: Option<String>,
    pub message: String,
}

pub fn platform_id() -> &'static str {
    if cfg!(target_os = "windows") {
        "windows"
    } else if cfg!(target_os = "macos") {
        "macos"
    } else if cfg!(target_os = "linux") {
        "linux"
    } else {
        "unknown"
    }
}

fn parse_gst_launch_output(output: &std::process::Output) -> Option<String> {
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&output.stdout);
    Some(
        text.lines()
            .find(|l| !l.trim().is_empty())
            .unwrap_or("GStreamer")
            .trim()
            .to_string(),
    )
}

fn gst_launch_version_at(launcher: &std::path::Path) -> Option<String> {
    let output = Command::new(launcher).arg("--version").output().ok()?;
    parse_gst_launch_output(&output)
}

fn gst_launch_version() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        let name = "gst-launch-1.0.exe";
        if let Ok(path) = std::env::var("PATH") {
            for dir in std::env::split_paths(&path) {
                let candidate = dir.join(name);
                if candidate.is_file() {
                    if let Some(v) = gst_launch_version_at(&candidate) {
                        return Some(v);
                    }
                }
            }
        }
        return None;
    }
    #[cfg(not(target_os = "windows"))]
    {
        let output = Command::new("gst-launch-1.0").arg("--version").output().ok()?;
        parse_gst_launch_output(&output)
    }
}

#[cfg(target_os = "windows")]
fn windows_gstreamer_roots() -> Vec<std::path::PathBuf> {
    let mut roots = Vec::new();
    if let Ok(env) = std::env::var("GSTREAMER_1_0_ROOT_MSVC_X86_64") {
        if !env.is_empty() {
            roots.push(std::path::PathBuf::from(env));
        }
    }
    if let Ok(local) = std::env::var("LOCALAPPDATA") {
        roots.push(
            std::path::PathBuf::from(local)
                .join("Programs")
                .join("gstreamer")
                .join("1.0")
                .join("msvc_x86_64"),
        );
    }
    roots.push(std::path::PathBuf::from(r"C:\gstreamer\1.0\msvc_x86_64"));
    roots.push(std::path::PathBuf::from(
        r"C:\Program Files\gstreamer\1.0\msvc_x86_64",
    ));
    roots
}

#[cfg(target_os = "windows")]
fn windows_gstreamer_on_disk() -> Option<std::path::PathBuf> {
    for root in windows_gstreamer_roots() {
        if root.join("bin").join("gst-launch-1.0.exe").exists() {
            return Some(root);
        }
    }
    None
}

#[cfg(target_os = "windows")]
fn apply_windows_gstreamer_process_env(root: &std::path::Path) {
    let bin = root.join("bin");
    if !bin.exists() {
        return;
    }
    if let Ok(path) = std::env::var("PATH") {
        let prefix = bin.display().to_string();
        if !path.contains(&prefix) {
            std::env::set_var("PATH", format!("{prefix};{path}"));
        }
    }
    std::env::set_var(
        "GSTREAMER_1_0_ROOT_MSVC_X86_64",
        root.display().to_string(),
    );
    let plugin = root.join("lib").join("gstreamer-1.0");
    if plugin.exists() {
        let pd = plugin.display().to_string();
        std::env::set_var("GST_PLUGIN_PATH", &pd);
        std::env::set_var("GST_PLUGIN_SYSTEM_PATH", &pd);
    }
}

#[cfg(target_os = "windows")]
fn prepend_windows_gstreamer_path() {
    if let Some(root) = windows_gstreamer_on_disk() {
        apply_windows_gstreamer_process_env(&root);
    }
}

/// Add GStreamer bin dir to the persistent User PATH (idempotent). No admin required.
#[cfg(target_os = "windows")]
pub fn persist_windows_gstreamer_user_env() {
    let Some(root) = windows_gstreamer_on_disk() else {
        return;
    };
    let bin = root.join("bin");
    if !bin.exists() {
        return;
    }
    let root_s = root.display().to_string().replace('\'', "''");
    let bin_s = bin.display().to_string().replace('\'', "''");
    let plugin = root.join("lib").join("gstreamer-1.0");
    let plugin_block = if plugin.exists() {
        let plugin_s = plugin.display().to_string().replace('\'', "''");
        format!(
            "[Environment]::SetEnvironmentVariable('GST_PLUGIN_PATH','{plugin_s}','User'); \
             [Environment]::SetEnvironmentVariable('GST_PLUGIN_SYSTEM_PATH','{plugin_s}','User');"
        )
    } else {
        String::new()
    };
    let ps = format!(
        "$bin='{bin_s}'; $root='{root_s}'; \
         $u=[Environment]::GetEnvironmentVariable('Path','User'); \
         if ($null -eq $u) {{ $u='' }}; \
         if ($u -notlike \"*$bin*\") {{ \
           [Environment]::SetEnvironmentVariable('Path',\"$bin;$u\",'User'); \
           [Environment]::SetEnvironmentVariable('GSTREAMER_1_0_ROOT_MSVC_X86_64',$root,'User'); \
           {plugin_block} \
         }}"
    );
    let _ = Command::new("powershell")
        .args([
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-Command",
            &ps,
        ])
        .spawn();
}

/// Process PATH + plugin vars now; also queue User PATH update for new terminals.
#[cfg(target_os = "windows")]
pub fn ensure_windows_gstreamer_environment() {
    prepend_windows_gstreamer_path();
    persist_windows_gstreamer_user_env();
}

pub fn check_gstreamer() -> DependencyStatus {
    #[cfg(target_os = "windows")]
    ensure_windows_gstreamer_environment();

    #[cfg(target_os = "windows")]
    if let Some(root) = windows_gstreamer_on_disk() {
        let launcher = root.join("bin").join("gst-launch-1.0.exe");
        if let Some(version) = gst_launch_version_at(&launcher) {
            return DependencyStatus {
                gstreamer_available: true,
                gstreamer_version: Some(version.clone()),
                message: format!("GStreamer ready: {version}"),
            };
        }
    }

    if let Some(version) = gst_launch_version() {
        return DependencyStatus {
            gstreamer_available: true,
            gstreamer_version: Some(version.clone()),
            message: format!("GStreamer ready: {version}"),
        };
    }

    #[cfg(target_os = "windows")]
    if let Some(root) = windows_gstreamer_on_disk() {
        return DependencyStatus {
            gstreamer_available: false,
            gstreamer_version: None,
            message: format!(
                "GStreamer files found at {} but gst-launch-1.0 could not run. Reinstall GStreamer MSVC x86_64 runtime.",
                root.display()
            ),
        };
    }

    DependencyStatus {
        gstreamer_available: false,
        gstreamer_version: None,
        message: "GStreamer is required for SonarSniffer (video export). Install the MSVC x86_64 runtime.".into(),
    }
}

fn gstreamer_item() -> DependencyItem {
    let gst = check_gstreamer();
    let (download_url, install_hint, can_auto_install) = match platform_id() {
        "windows" => (
            Some("https://gstreamer.freedesktop.org/download/#windows".into()),
            Some(
                "winget install -e --id gstreamerproject.gstreamer --accept-package-agreements --accept-source-agreements"
                    .into(),
            ),
            Command::new("winget")
                .arg("--version")
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false),
        ),
        "macos" => (
            Some("https://gstreamer.freedesktop.org/download/#macos".into()),
            Some("brew install gstreamer gst-plugins-base gst-plugins-good".into()),
            Command::new("brew")
                .arg("--version")
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false),
        ),
        "linux" => (
            Some("https://gstreamer.freedesktop.org/download/".into()),
            Some(
                "sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-libav"
                    .into(),
            ),
            true,
        ),
        _ => (None, None, false),
    };

    DependencyItem {
        id: "gstreamer".into(),
        name: "GStreamer 1.x (MSVC x86_64 on Windows)".into(),
        required: true,
        satisfied: gst.gstreamer_available,
        version: gst.gstreamer_version,
        message: gst.message,
        download_url,
        install_hint,
        can_auto_install,
    }
}

#[cfg(target_os = "windows")]
fn webview2_item() -> DependencyItem {
    let satisfied = std::path::Path::new(r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application")
        .exists()
        || std::path::Path::new(r"C:\Program Files\Microsoft\EdgeWebView\Application").exists();
    DependencyItem {
        id: "webview2".into(),
        name: "Microsoft Edge WebView2 Runtime".into(),
        required: true,
        satisfied,
        version: None,
        message: if satisfied {
            "WebView2 runtime present (required for the desktop UI).".into()
        } else {
            "WebView2 is required for the SonarSniffer window.".into()
        },
        download_url: Some(
            "https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section".into(),
        ),
        install_hint: Some(
            "winget install -e --id Microsoft.EdgeWebView2Runtime --accept-package-agreements --accept-source-agreements"
                .into(),
        ),
        can_auto_install: Command::new("winget")
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false),
    }
}

#[cfg(not(target_os = "windows"))]
fn webview2_item() -> DependencyItem {
    DependencyItem {
        id: "webview2".into(),
        name: "WebView / WKWebView".into(),
        required: false,
        satisfied: true,
        version: None,
        message: "Not applicable on this platform.".into(),
        download_url: None,
        install_hint: None,
        can_auto_install: false,
    }
}

pub fn preflight_report() -> PreflightReport {
    let items = vec![gstreamer_item(), webview2_item()];
    let ready = items.iter().filter(|i| i.required).all(|i| i.satisfied);
    let summary = if ready {
        "All required dependencies are installed.".into()
    } else {
        let missing: Vec<_> = items
            .iter()
            .filter(|i| i.required && !i.satisfied)
            .map(|i| i.name.as_str())
            .collect();
        format!(
            "Install required components before running SonarSniffer: {}",
            missing.join(", ")
        )
    };
    PreflightReport {
        platform: platform_id().into(),
        ready,
        gstreamer_required: true,
        items,
        summary,
    }
}

pub fn item_by_id<'a>(report: &'a PreflightReport, id: &str) -> Option<&'a DependencyItem> {
    report.items.iter().find(|i| i.id == id)
}

pub fn open_dependency_url(id: &str) -> Result<String, String> {
    let report = preflight_report();
    let item = item_by_id(&report, id).ok_or_else(|| format!("Unknown dependency: {id}"))?;
    let url = item
        .download_url
        .as_ref()
        .ok_or_else(|| format!("No download URL for {id}"))?;
    open_url(url)
}

pub fn open_url(url: &str) -> Result<String, String> {
    #[cfg(target_os = "windows")]
    {
        Command::new("cmd")
            .args(["/C", "start", "", url])
            .spawn()
            .map_err(|e| format!("Failed to open browser: {e}"))?;
        return Ok(format!("Opened {url}"));
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(url)
            .spawn()
            .map_err(|e| format!("Failed to open browser: {e}"))?;
        return Ok(format!("Opened {url}"));
    }
    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(url)
            .spawn()
            .map_err(|e| format!("Failed to open browser: {e}"))?;
        return Ok(format!("Opened {url}"));
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    {
        let _ = url;
        Err("Open URL not supported on this platform".into())
    }
}

pub fn install_dependency(id: &str) -> Result<String, String> {
    let report = preflight_report();
    let item = item_by_id(&report, id).ok_or_else(|| format!("Unknown dependency: {id}"))?;
    if item.satisfied {
        return Ok(format!("{} is already installed.", item.name));
    }
    if !item.can_auto_install {
        return Err(format!(
            "Automatic install is not available. Use Download page or run:\n{}",
            item.install_hint.as_deref().unwrap_or("see download URL")
        ));
    }

    match (platform_id(), id) {
        ("windows", "gstreamer") => windows_winget("gstreamerproject.gstreamer", "GStreamer"),
        ("windows", "webview2") => {
            windows_winget("Microsoft.EdgeWebView2Runtime", "WebView2")
        }
        ("macos", "gstreamer") => macos_brew(&["gstreamer", "gst-plugins-base", "gst-plugins-good"]),
        ("linux", "gstreamer") => linux_apt(&[
            "gstreamer1.0-tools",
            "gstreamer1.0-plugins-base",
            "gstreamer1.0-plugins-good",
            "gstreamer1.0-libav",
        ]),
        _ => Err(format!(
            "No auto-installer for {} on {}. Open the download page instead.",
            item.name,
            report.platform
        )),
    }
}

pub fn install_all_required() -> Result<String, String> {
    let report = preflight_report();
    let mut logs = Vec::new();
    for item in report.items.iter().filter(|i| i.required && !i.satisfied) {
        match install_dependency(&item.id) {
            Ok(msg) => logs.push(msg),
            Err(e) => logs.push(format!("{}: {e}", item.id)),
        }
    }
    let after = preflight_report();
    if after.ready {
        Ok(format!(
            "All required dependencies installed.\n{}",
            logs.join("\n")
        ))
    } else {
        Err(format!(
            "Some dependencies are still missing.\n{}\n\nRe-check after closing installers.",
            logs.join("\n")
        ))
    }
}

/// Legacy entry — prefer `preflight_report()`.
pub fn install_gstreamer_runtime() -> Result<String, String> {
    install_dependency("gstreamer")
}

#[cfg(target_os = "windows")]
fn windows_winget(winget_id: &str, label: &str) -> Result<String, String> {
    let output = Command::new("winget")
        .args([
            "install",
            "-e",
            "--id",
            winget_id,
            "--accept-package-agreements",
            "--accept-source-agreements",
        ])
        .output()
        .map_err(|e| format!("Failed to run winget for {label}: {e}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    if output.status.success() {
        Ok(format!(
            "winget installed {label}. Restart SonarSniffer if GStreamer is not detected yet.\n{stdout}"
        ))
    } else {
        Err(format!(
            "winget install {label} failed (exit {:?}). Try running SonarSniffer as Administrator or use Download page.\n{stdout}\n{stderr}",
            output.status.code()
        ))
    }
}

#[cfg(target_os = "macos")]
fn macos_brew(packages: &[&str]) -> Result<String, String> {
    let mut cmd = Command::new("brew");
    cmd.arg("install");
    for p in packages {
        cmd.arg(p);
    }
    let output = cmd
        .output()
        .map_err(|e| format!("Failed to run brew: {e}"))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

#[cfg(target_os = "linux")]
fn linux_apt(packages: &[&str]) -> Result<String, String> {
    let mut cmd = Command::new("sudo");
    cmd.arg("apt").arg("install").arg("-y");
    for p in packages {
        cmd.arg(p);
    }
    let output = cmd
        .output()
        .map_err(|e| format!("Failed to run apt (try install_hint manually): {e}"))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

#[cfg(not(target_os = "windows"))]
fn windows_winget(_id: &str, _label: &str) -> Result<String, String> {
    Err("winget only on Windows".into())
}

#[cfg(not(target_os = "macos"))]
fn macos_brew(_packages: &[&str]) -> Result<String, String> {
    Err("brew only on macOS".into())
}

#[cfg(not(target_os = "linux"))]
fn linux_apt(_packages: &[&str]) -> Result<String, String> {
    Err("apt only on Linux".into())
}
