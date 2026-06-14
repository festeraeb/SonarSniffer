//! Double-click launcher: extract embedded kit → elevated PowerShell → full install.
#![cfg_attr(not(windows), allow(unused_imports))]

mod webview;

use std::fs::{self, File};
use std::io::copy;
use std::path::{Path, PathBuf};
use std::process::Command;

#[cfg(not(windows))]
fn main() {
    eprintln!("SonarSniffer-Setup.exe is Windows-only. Build with:");
    eprintln!("  SONARSNIFFER_SETUP_PAYLOAD=path/to/payload.zip cargo build --release");
    std::process::exit(1);
}

#[cfg(windows)]
fn main() {
    if let Err(e) = run() {
        eprintln!("SonarSniffer setup failed: {e}");
        pause_on_error();
        std::process::exit(1);
    }
}

#[cfg(windows)]
fn run() -> Result<(), Box<dyn std::error::Error>> {
    println!("SonarSniffer — preparing install...\n");

    let wv2 = webview::detect_webview2();
    if wv2.present {
        println!(
            "WebView2: detected ({}){}",
            wv2.method,
            wv2.version
                .as_ref()
                .map(|v| format!(" version {v}"))
                .unwrap_or_default()
        );
    } else {
        println!("WebView2: not detected — installer will attempt runtime install.");
    }

    let staging = extract_payload()?;
    let install_ps1 = staging.join("install_sonarsniffer_full.ps1");
    if !install_ps1.is_file() {
        return Err(format!(
            "missing install script in kit: {}",
            install_ps1.display()
        )
        .into());
    }

    println!("Launching PowerShell installer (Administrator)...\n");
    launch_powershell_elevated(&install_ps1, &staging)?;
    Ok(())
}

#[cfg(windows)]
fn extract_payload() -> Result<PathBuf, Box<dyn std::error::Error>> {
    let base = std::env::temp_dir().join(format!(
        "SonarSniffer-Setup-{}",
        std::process::id()
    ));
    fs::create_dir_all(&base)?;

    #[cfg(embed_payload)]
    {
        const PAYLOAD: &[u8] = include!(concat!(env!("OUT_DIR"), "/embedded_payload.rs"));
        extract_zip(PAYLOAD, &base)?;
        return Ok(base);
    }

    #[cfg(not(embed_payload))]
    {
        let exe_dir = std::env::current_exe()?
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_else(|| PathBuf::from("."));
        let sidecar = exe_dir.join("SonarSniffer-Setup-payload.zip");
        if sidecar.is_file() {
            let data = fs::read(&sidecar)?;
            extract_zip(&data, &base)?;
            return Ok(base);
        }
        Err(
            "No embedded payload. Build with SONARSNIFFER_SETUP_PAYLOAD or place SonarSniffer-Setup-payload.zip next to this exe.".into(),
        )
    }
}

fn extract_zip(data: &[u8], dest: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let cursor = std::io::Cursor::new(data);
    let mut archive = zip::ZipArchive::new(cursor)?;
    for i in 0..archive.len() {
        let mut file = archive.by_index(i)?;
        let name = file.name().replace('\\', "/");
        if name.ends_with('/') {
            fs::create_dir_all(dest.join(&name))?;
            continue;
        }
        let out_path = dest.join(&name);
        if let Some(parent) = out_path.parent() {
            fs::create_dir_all(parent)?;
        }
        if file.is_dir() {
            fs::create_dir_all(&out_path)?;
            continue;
        }
        let mut out = File::create(&out_path)?;
        copy(&mut file, &mut out)?;
    }
    Ok(())
}

#[cfg(windows)]
fn launch_powershell_elevated(
    script: &Path,
    workdir: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let ps = powershell_path();
    let wd = workdir.to_string_lossy().replace('\'', "''");
    let scr = script.to_string_lossy().replace('\'', "''");
    let elevate_cmd = format!(
        r#"$log = Join-Path $env:TEMP 'SonarSniffer-install.log'
function Log($m) {{ Add-Content -LiteralPath $log -Value "[$(Get-Date -Format s)] [bootstrap] $m" }}
$max = 3
$timeoutSec = 90
for ($attempt = 1; $attempt -le $max; $attempt++) {{
  Log "UAC elevation attempt $attempt of $max"
  Write-Host ''
  Write-Host 'Windows is waiting for Administrator approval.' -ForegroundColor Yellow
  Write-Host 'Look for a UAC prompt — it may be behind other windows.' -ForegroundColor Yellow
  Write-Host ''
  $p = Start-Process -FilePath '{ps}' -Verb RunAs -PassThru -ArgumentList @(
    '-NoProfile','-ExecutionPolicy','Bypass',
    '-WorkingDirectory','{wd}',
    '-File','{scr}','-StrictSilent'
  )
  if (-not $p) {{ throw 'Start-Process RunAs returned null' }}
  $done = $p.WaitForExit($timeoutSec * 1000)
  if ($done) {{
    if ($p.ExitCode -eq 0) {{ Log "Elevation succeeded"; exit 0 }}
    Log "Elevated installer exit $($p.ExitCode)"
    exit $p.ExitCode
  }}
  try {{ $p.Kill() }} catch {{}}
  Log "UAC attempt $attempt timed out after ${timeoutSec}s"
  if ($attempt -lt $max) {{
    $choice = Read-Host '[R] Retry elevation / [C] Cancel'
    if ($choice -match '^[Cc]') {{ exit 1 }}
  }}
}}
Write-Error "Elevation failed after $max attempts"
exit 1"#
    );
    let status = Command::new(&ps)
        .args(["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", &elevate_cmd])
        .status()?;
    if !status.success() {
        return Err(format!("elevated PowerShell launch failed: {status}").into());
    }
    Ok(())
}

#[cfg(windows)]
fn powershell_path() -> String {
    std::env::var("SystemRoot")
        .map(|w| format!("{w}\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"))
        .unwrap_or_else(|_| "powershell.exe".to_string())
}

#[cfg(windows)]
fn pause_on_error() {
    println!("\nPress Enter to close...");
    let mut buf = String::new();
    let _ = std::io::stdin().read_line(&mut buf);
}
