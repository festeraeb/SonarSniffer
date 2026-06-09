#Requires -Version 5.1
<#
.SYNOPSIS
  Build SonarSniffer desktop MSI/NSIS on native Windows.

.DESCRIPTION
  Video export uses the built-in pure-Rust AV1 encoder (no GStreamer required).
  Pass -VideoGstreamer only for legacy H.264 via optional GStreamer feature.

.EXAMPLE
  .\scripts\build_sonarsniffer_desktop_msi_windows.ps1
#>
[CmdletBinding()]
param(
    [ValidateSet("msi", "nsis", "both")]
    [string]$Bundle = "both",
    [switch]$InstallPrereqs,
    [switch]$InstallTauriCli,
    [switch]$VideoGstreamer
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Pass($m) { Write-Host "OK: $m" -ForegroundColor Green }
function Fail($m) { Write-Host "FATAL: $m" -ForegroundColor Red; exit 1 }

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$tauriDir = Join-Path $repoRoot "desktop\src-tauri"
$prereqScript = Join-Path $repoRoot "scripts\install_sonarsniffer_prereqs_windows.ps1"

if (-not (Test-Path (Join-Path $tauriDir "tauri.conf.json"))) {
    Fail "Tauri project not found: $tauriDir"
}

if ($InstallPrereqs) {
    if (-not (Test-Path $prereqScript)) { Fail "Missing $prereqScript" }
    Write-Step "Installing prerequisites (WebView2)"
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

Write-Step "Staging sidecars"
& (Join-Path $repoRoot "scripts\stage_tauri_sidecars.ps1")
if ($LASTEXITCODE -ne 0) { Fail "Sidecar staging failed" }

Set-Location $tauriDir
$bundles = if ($Bundle -eq "both") { "msi,nsis" } else { $Bundle }

$features = @()
if ($VideoGstreamer) {
    $features += "video-gstreamer"
    Pass "Building with optional video-gstreamer (legacy H.264)"
} else {
    Pass "Building with built-in AV1 encoder (no GStreamer)"
}

Write-Step "cargo tauri build (bundles: $bundles)"
$featureArg = if ($features.Count -gt 0) { "--features " + ($features -join ",") } else { "" }
Invoke-Expression "cargo tauri build $featureArg --bundles $bundles"
if ($LASTEXITCODE -ne 0) { Fail "Tauri bundle build failed" }

$bundleRoot = Join-Path $tauriDir "target\release\bundle"
Write-Host ""
Pass "Artifacts under: $bundleRoot"
Get-ChildItem -Path $bundleRoot -Recurse -Include *.msi,*.exe,*.dmg | ForEach-Object { Write-Host "  $($_.FullName)" }
