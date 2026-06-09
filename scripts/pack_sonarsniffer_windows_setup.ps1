#Requires -Version 5.1
<#
.SYNOPSIS
  Pack Tauri desktop + CLI + install script into one SonarSniffer-Setup.exe.

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
$tauriDir = Join-Path $RepoRoot "desktop\src-tauri"
$bootstrapDir = Join-Path $RepoRoot "setup-bootstrap"
$installScript = Join-Path $RepoRoot "scripts\install_sonarsniffer_full.ps1"

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }

if (-not (Test-Path $installScript)) { throw "Missing $installScript" }

Write-Step "Collecting kit"
if (Test-Path $kit) { Remove-Item -Recurse -Force $kit }
New-Item -ItemType Directory -Force -Path $kit | Out-Null

Copy-Item $installScript (Join-Path $kit "install_sonarsniffer_full.ps1") -Force

foreach ($name in @("sonarsniffer-cli.exe", "parse_cli.exe")) {
    $src = Join-Path $RepoRoot "target\release\$name"
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $kit $name) -Force
        Write-Host "  + $name"
    } else {
        Write-Host "  WARN missing $src — run scripts/stage_tauri_sidecars.ps1" -ForegroundColor Yellow
    }
}

$msiDir = Join-Path $tauriDir "target\release\bundle\msi"
if (Test-Path $msiDir) {
    Get-ChildItem $msiDir -Filter "*.msi" | ForEach-Object {
        Copy-Item $_.FullName $kit -Force
        Write-Host "  + $($_.Name)"
    }
} else {
    Write-Host "  WARN no MSI — run scripts/build_sonarsniffer_desktop_msi_windows.ps1" -ForegroundColor Yellow
}

$nsisDir = Join-Path $tauriDir "target\release\bundle\nsis"
if (Test-Path $nsisDir) {
    $portable = Get-ChildItem $nsisDir -Recurse -Filter "SonarSniffer.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($portable) {
        Copy-Item $portable.FullName (Join-Path $kit "SonarSniffer.exe") -Force
        Write-Host "  + SonarSniffer.exe (from NSIS tree)"
    }
}

$ui = Join-Path $RepoRoot "desktop\ui"
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
