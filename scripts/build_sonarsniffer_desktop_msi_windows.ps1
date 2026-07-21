#Requires -Version 5.1
<#
.SYNOPSIS
  Build SonarSniffer desktop MSI/NSIS on native Windows.

.DESCRIPTION
  Production flags (docs/BUILD_FLAGS.md):
    cargo build --release --no-default-features  (CLI sidecars)
    cargo tauri build                            (desktop; default features empty)

  GStreamer / video-gstreamer is OFF by default (AV1 via rav1e). Pass -LegacyGStreamer
  only for a legacy H.264 SKU.

.EXAMPLE
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
    [switch]$LegacyGStreamer,
    # Deprecated alias — prefer omitting -LegacyGStreamer for production.
    [switch]$NoVideoFeature
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Pass($m) { Write-Host "OK: $m" -ForegroundColor Green }
function Fail($m) { Write-Host "FATAL: $m" -ForegroundColor Red; exit 1 }

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$standaloneTauri = Join-Path $repoRoot "desktop\src-tauri"
$monorepoTauri = Join-Path $repoRoot "sonarsniffer\desktop\src-tauri"
$tauriDir = if (Test-Path (Join-Path $standaloneTauri "tauri.conf.json")) { $standaloneTauri } else { $monorepoTauri }
$ssRoot = if (Test-Path (Join-Path $repoRoot "Cargo.toml")) { $repoRoot } else { Join-Path $repoRoot "sonarsniffer" }
$prereqScript = Join-Path $repoRoot "scripts\install_sonarsniffer_prereqs_windows.ps1"

if (-not (Test-Path (Join-Path $tauriDir "tauri.conf.json"))) {
    Fail "Tauri project not found under desktop\src-tauri (sync standalone repo first)"
}

if ($InstallPrereqs) {
    if (-not (Test-Path $prereqScript)) { Fail "Missing $prereqScript" }
    Write-Step "Installing prerequisites (WebView2; GStreamer only if needed)"
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

# Prefer shared sidecar staging (production --no-default-features)
$stageScript = Join-Path $repoRoot "tools\stage_tauri_sidecars.ps1"
if (Test-Path $stageScript) {
    Write-Step "Staging CLI sidecars (release --no-default-features)"
    & $stageScript -RepoRoot $ssRoot -BuildProfile "release"
    if ($LASTEXITCODE -ne 0) { Fail "sidecar staging failed" }
} else {
    Write-Step "Building CLI sidecars (fallback)"
    Push-Location $ssRoot
    try {
        cargo build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli
        if ($LASTEXITCODE -ne 0) { Fail "CLI build failed" }
    } finally { Pop-Location }
}

Set-Location $tauriDir
$bundles = if ($Bundle -eq "both") { "msi,nsis" } else { $Bundle }

# Production: no Cargo features. LegacyGStreamer opts into video-gstreamer.
$useGst = $LegacyGStreamer -and -not $NoVideoFeature
$featureArg = ""
if ($useGst) {
    $featureArg = "--features video-gstreamer"
    Pass "Building with video-gstreamer (legacy H.264 SKU)"
} else {
    Pass "Production build: no-default-features / empty Tauri features (AV1 rav1e)"
}

Write-Step "cargo tauri build (bundles: $bundles)"
if ($featureArg) {
    Invoke-Expression "cargo tauri build $featureArg --bundles $bundles"
} else {
    cargo tauri build --bundles $bundles
}
if ($LASTEXITCODE -ne 0) { Fail "Tauri bundle build failed" }

$bundleRoot = Join-Path $tauriDir "target\release\bundle"
$workspaceBundle = Join-Path $ssRoot "target\release\bundle"
if (-not (Test-Path $bundleRoot) -and (Test-Path $workspaceBundle)) { $bundleRoot = $workspaceBundle }
Write-Host ""
Pass "Artifacts under: $bundleRoot"
Get-ChildItem -Path $bundleRoot -Recurse -Include *.msi,*.exe -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Host "  $($_.FullName)" }
