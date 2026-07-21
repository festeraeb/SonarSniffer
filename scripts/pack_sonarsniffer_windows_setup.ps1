#Requires -Version 5.1
<#
.SYNOPSIS
  Pack Tauri desktop + CLI + install script into one SonarSniffer-Setup.exe.

.DESCRIPTION
  Run on native Windows AFTER building with production flags (docs/BUILD_FLAGS.md):
    1. CLI:  cargo build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli
       (or tools/stage_tauri_sidecars.ps1)
    2. desktop MSI/NSIS: scripts/build_sonarsniffer_desktop_msi_windows.ps1

  Packs install_sonarsniffer_full.ps1 + SonarSniffer.Install.psm1 + optional
  SonarSniffer.InstallAssist.psm1 (ip / LLM self-heal when SONARSNIFFER_INSTALL_ASSIST=1).

  Output: dist/SonarSniffer-Setup.exe  (single file — double-click to install)

.EXAMPLE
  .\scripts\pack_sonarsniffer_windows_setup.ps1
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [switch]$SkipLauncherBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}

$dist = Join-Path $RepoRoot "dist"
$kit = Join-Path $dist "SonarSniffer-Setup-kit"
$payloadZip = Join-Path $dist "SonarSniffer-Setup-payload.zip"
$setupOut = Join-Path $dist "SonarSniffer-Setup.exe"

# Support both the old monorepo layout ($RepoRoot/sonarsniffer/...) and the
# standalone SonarSniffer repo layout ($RepoRoot/...).
$standaloneTauriDir = Join-Path $RepoRoot "desktop\src-tauri"
$monorepoTauriDir = Join-Path $RepoRoot "sonarsniffer\desktop\src-tauri"
$tauriDir = if (Test-Path $standaloneTauriDir) { $standaloneTauriDir } else { $monorepoTauriDir }

$standaloneRoot = if (Test-Path (Join-Path $RepoRoot "Cargo.toml")) { $RepoRoot } else { "" }
$monorepoRoot = Join-Path $RepoRoot "sonarsniffer"
$ssDir = if ($standaloneRoot) { $standaloneRoot } else { $monorepoRoot }

$standaloneBootstrapDir = Join-Path $RepoRoot "setup-bootstrap"
$monorepoBootstrapDir = Join-Path $RepoRoot "sonarsniffer\setup-bootstrap"
$bootstrapDir = if (Test-Path $standaloneBootstrapDir) { $standaloneBootstrapDir } else { $monorepoBootstrapDir }

$installScript = Join-Path $RepoRoot "scripts\install_sonarsniffer_full.ps1"

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }

if (-not (Test-Path $installScript)) { throw "Missing $installScript" }

Write-Step "Collecting kit"
if (Test-Path $kit) { Remove-Item -Recurse -Force $kit }
New-Item -ItemType Directory -Force -Path $kit | Out-Null

Copy-Item $installScript (Join-Path $kit "install_sonarsniffer_full.ps1") -Force
$moduleSrc = Join-Path $RepoRoot "scripts\lib\SonarSniffer.Install.psm1"
if (Test-Path $moduleSrc) {
    $libDir = Join-Path $kit "lib"
    New-Item -ItemType Directory -Force -Path $libDir | Out-Null
    Copy-Item $moduleSrc (Join-Path $libDir "SonarSniffer.Install.psm1") -Force
    Write-Host "  + lib\SonarSniffer.Install.psm1"
    $assistSrc = Join-Path $RepoRoot "scripts\lib\SonarSniffer.InstallAssist.psm1"
    if (Test-Path $assistSrc) {
        Copy-Item $assistSrc (Join-Path $libDir "SonarSniffer.InstallAssist.psm1") -Force
        Write-Host "  + lib\SonarSniffer.InstallAssist.psm1"
    }
} else {
    Write-Host "  WARN missing $moduleSrc" -ForegroundColor Yellow
}
$pathScript = Join-Path $RepoRoot "scripts\windows_add_gstreamer_path.ps1"
if (Test-Path $pathScript) {
    Copy-Item $pathScript (Join-Path $kit "windows_add_gstreamer_path.ps1") -Force
    Write-Host "  + windows_add_gstreamer_path.ps1"
}

# CLI (release)
foreach ($name in @("sonarsniffer-cli.exe", "parse_cli.exe")) {
    $src = Join-Path $ssDir "target\release\$name"
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $kit $name) -Force
        Write-Host "  + $name"
    } else {
        Write-Host "  WARN missing $src — run: cargo build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli" -ForegroundColor Yellow
    }
}

# MSI from Tauri bundle
$workspaceMsiDir = Join-Path $RepoRoot "target\release\bundle\msi"
$tauriMsiDir = Join-Path $tauriDir "target\release\bundle\msi"
$msiDir = if (Test-Path $workspaceMsiDir) { $workspaceMsiDir } else { $tauriMsiDir }
if (Test-Path $msiDir) {
    Get-ChildItem $msiDir -Filter "*.msi" | ForEach-Object {
        Copy-Item $_.FullName $kit -Force
        Write-Host "  + $($_.Name)"
    }
} else {
    Write-Host "  WARN no MSI — run scripts/build_sonarsniffer_desktop_msi_windows.ps1" -ForegroundColor Yellow
}

# Portable desktop exe (if built without MSI)
# Tauri 2 defaults to crate name tauri-appsonarsniffer.exe unless mainBinaryName=SonarSniffer.
$workspaceNsisDir = Join-Path $RepoRoot "target\release\bundle\nsis"
$tauriNsisDir = Join-Path $tauriDir "target\release\bundle\nsis"
$nsisDir = if (Test-Path $workspaceNsisDir) { $workspaceNsisDir } else { $tauriNsisDir }
$workspaceReleaseDir = Join-Path $RepoRoot "target\release"
$tauriReleaseDir = Join-Path $tauriDir "target\release"
$portable = $null
foreach ($root in @($nsisDir, $workspaceReleaseDir, $tauriReleaseDir)) {
    if (-not (Test-Path $root)) { continue }
    foreach ($name in @("SonarSniffer.exe", "tauri-appsonarsniffer.exe")) {
        $hit = Get-ChildItem $root -Recurse -Filter $name -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) { $portable = $hit; break }
    }
    if ($portable) { break }
}
if ($portable) {
    Copy-Item $portable.FullName (Join-Path $kit "SonarSniffer.exe") -Force
    Write-Host "  + SonarSniffer.exe (from $($portable.FullName))"
}

# UI assets (optional, for portable)
$standaloneUi = Join-Path $RepoRoot "desktop\ui"
$monorepoUi = Join-Path $RepoRoot "sonarsniffer\desktop\ui"
$ui = if (Test-Path $standaloneUi) { $standaloneUi } else { $monorepoUi }
if (Test-Path $ui) {
    Copy-Item $ui (Join-Path $kit "ui") -Recurse -Force
    Write-Host "  + ui/"
}

Write-Step "Creating payload zip"
if (Test-Path $payloadZip) { Remove-Item -Force $payloadZip }
Compress-Archive -Path (Join-Path $kit "*") -DestinationPath $payloadZip -Force
Write-Host "  $payloadZip ($([math]::Round((Get-Item $payloadZip).Length / 1MB, 1)) MB)"

if (-not $SkipLauncherBuild) {
    Write-Step "Building SonarSniffer-Setup.exe launcher"
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        throw "cargo not on PATH"
    }
    $env:SONARSNIFFER_SETUP_PAYLOAD = $payloadZip
    Push-Location $bootstrapDir
    try {
        cargo build --release
        if ($LASTEXITCODE -ne 0) { throw "setup-bootstrap build failed" }
    } finally {
        Pop-Location
        Remove-Item Env:SONARSNIFFER_SETUP_PAYLOAD -ErrorAction SilentlyContinue
    }
    $built = Join-Path $bootstrapDir "target\release\SonarSniffer-Setup.exe"
    if (-not (Test-Path $built)) { throw "Expected $built" }
    New-Item -ItemType Directory -Force -Path $dist | Out-Null
    Copy-Item $built $setupOut -Force
}

Write-Host ""
Write-Host "READY — one file to copy/run:" -ForegroundColor Green
Write-Host "  $setupOut"
Write-Host ""
Write-Host "Double-click SonarSniffer-Setup.exe → PowerShell (Admin) → prereqs + MSI + CLIs"
