#Requires -Version 5.1
<#
.SYNOPSIS
  Build SonarSniffer desktop MSI/NSIS on native Windows (physical laptop — not a VM).

.DESCRIPTION
  GStreamer is NOT bundled into the installer. Install runtime via winget or
  scripts/install_sonarsniffer_prereqs_windows.ps1; the app preflight gate handles the rest.

  Run from an elevated or normal PowerShell on the Windows test machine after syncing
  the repo (git clone, USB, or copy from c2).

.EXAMPLE
  cd C:\path\to\SonarSniffer
  .\scripts\build_sonarsniffer_desktop_msi_windows.ps1

.EXAMPLE
  .\scripts\build_sonarsniffer_desktop_msi_windows.ps1 -InstallPrereqs -InstallTauriCli
#>
[CmdletBinding()]
param(
    [ValidateSet("msi", "nsis", "both")]
    [string]$Bundle = "both",
    [switch]$InstallPrereqs,
    [switch]$InstallTauriCli,
    [switch]$NoVideoFeature
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Pass($m) { Write-Host "OK: $m" -ForegroundColor Green }
function Fail($m) { Write-Host "FATAL: $m" -ForegroundColor Red; exit 1 }

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$tauriDir = Join-Path $repoRoot "sonarsniffer\desktop\src-tauri"
$prereqScript = Join-Path $repoRoot "scripts\install_sonarsniffer_prereqs_windows.ps1"

if (-not (Test-Path (Join-Path $tauriDir "tauri.conf.json"))) {
    Fail "Tauri project not found: $tauriDir (sync repo first)"
}

if ($InstallPrereqs) {
    if (-not (Test-Path $prereqScript)) { Fail "Missing $prereqScript" }
    Write-Step "Installing prerequisites (GStreamer + WebView2)"
    & $prereqScript -InstallMissing
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo not on PATH — install Rust from https://rustup.rs"
}

$tauriOk = $false
try {
    $null = cargo tauri --version 2>$null
    if ($LASTEXITCODE -eq 0) { $tauriOk = $true }
} catch { }

if (-not $tauriOk) {
    if (-not $InstallTauriCli) {
        Fail "cargo tauri missing. Re-run with -InstallTauriCli or: cargo install tauri-cli --version '^2.0'"
    }
    Write-Step "Installing tauri-cli"
    cargo install tauri-cli --version '^2.0'
    if ($LASTEXITCODE -ne 0) { Fail "tauri-cli install failed" }
}
Pass (cargo tauri --version)

# Stage CLI + soundtiles sidecars for Tauri bundle (same folder as desktop app)
$hostLine = (rustc -vV | Select-String "^host:").ToString() -replace "host:\s*", ""
$hostLine = $hostLine.Trim()
$binDir = Join-Path $tauriDir "binaries"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
$ssTarget = Join-Path $repoRoot "sonarsniffer\target\release"
foreach ($pair in @(
        @("sonarsniffer-cli.exe", "sonarsniffer-cli"),
        @("parse_cli.exe", "parse_cli")
    )) {
    $src = Join-Path $ssTarget $pair[0]
    if (Test-Path $src) {
        $dst = Join-Path $binDir ("{0}-{1}.exe" -f $pair[1], $hostLine)
        Copy-Item $src $dst -Force
        Pass "Sidecar: binaries\$([IO.Path]::GetFileName($dst))"
    } else {
        Write-Host "  WARN missing $src — cd sonarsniffer; cargo build --release" -ForegroundColor Yellow
    }
}

# Optional: build soundtiles sidecar if present in workspace
$soundtilesSrc = Join-Path $repoRoot "sonarsniffer\soundtiles"
if (Test-Path (Join-Path $soundtilesSrc "Cargo.toml")) {
    Write-Step "Building soundtiles sidecar"
    Push-Location $soundtilesSrc
    try {
        cargo build --release
        if ($LASTEXITCODE -ne 0) { Fail "soundtiles build failed" }
        $hostLine = (rustc -vV | Select-String "^host:").ToString() -replace "host:\s*", ""
        $hostLine = $hostLine.Trim()
        $binDir = Join-Path $tauriDir "binaries"
        New-Item -ItemType Directory -Force -Path $binDir | Out-Null
        $sidecarName = "soundtiles-$hostLine.exe"
        Copy-Item (Join-Path $soundtilesSrc "target\release\soundtiles.exe") (Join-Path $binDir $sidecarName) -Force
        Pass "Sidecar: binaries\$sidecarName"
    } finally {
        Pop-Location
    }
}

Set-Location $tauriDir
$bundles = if ($Bundle -eq "both") { "msi,nsis" } else { $Bundle }

$features = @()
if (-not $NoVideoFeature) {
    $features += "video-gstreamer"
    Pass "Building with video-gstreamer (requires GStreamer MSVC on this machine at runtime)"
} else {
    Write-Host "WARN: NoVideoFeature — MP4 export disabled in this build" -ForegroundColor Yellow
}

Write-Step "cargo tauri build (bundles: $bundles)"
$featureArg = if ($features.Count -gt 0) { "--features " + ($features -join ",") } else { "" }
Invoke-Expression "cargo tauri build $featureArg --bundles $bundles"
if ($LASTEXITCODE -ne 0) { Fail "Tauri bundle build failed" }

$bundleRoot = Join-Path $tauriDir "target\release\bundle"
Write-Host ""
Pass "Artifacts under: $bundleRoot"
Get-ChildItem -Path $bundleRoot -Recurse -Include *.msi,*.exe | ForEach-Object { Write-Host "  $($_.FullName)" }
