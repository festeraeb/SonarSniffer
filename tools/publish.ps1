# Pre-release gate: single crate layout, build, stage sidecars, regression.
param(
    [switch]$SkipRegression,
    [switch]$SkipDesktop,
    [switch]$Release,
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
$targetDir = Join-Path $env:LOCALAPPDATA "SonarSniffer-build\target"
$env:CARGO_TARGET_DIR = $targetDir
$profile = if ($Release) { "release" } else { "dev" }

function Invoke-Cargo {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & cargo @Args
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) { exit $code }
}

Write-Host "=== SonarSniffer publish gate ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host "Target: $targetDir"
Write-Host ""

Push-Location $RepoRoot
try {
    Write-Host "[1/5] Verify single library crate (no desktop mirror)..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "verify_no_mirror.ps1") -RepoRoot $RepoRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[2/5] cargo check (library + CLI)..." -ForegroundColor Yellow
    if ($Release) {
        Invoke-Cargo check --release -p sonarsniffer --bins
    } else {
        Invoke-Cargo check -p sonarsniffer --bins
    }

    Write-Host "[3/5] cargo test (library)..." -ForegroundColor Yellow
    Invoke-Cargo test -p sonarsniffer --lib

    if (-not $SkipDesktop) {
        Write-Host "[4/5] cargo check (desktop)..." -ForegroundColor Yellow
        if ($Release) {
            Invoke-Cargo check --release -p tauri-appsonarsniffer
        } else {
            Invoke-Cargo check -p tauri-appsonarsniffer
        }

        Write-Host "[5/5] Stage Tauri sidecars..." -ForegroundColor Yellow
        & (Join-Path $PSScriptRoot "stage_tauri_sidecars.ps1") -RepoRoot $RepoRoot -Profile $(if ($Release) { "release" } else { "dev" })
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "[4/5] Skipped desktop (--SkipDesktop)" -ForegroundColor DarkGray
        Write-Host "[5/5] Skipped sidecars (--SkipDesktop)" -ForegroundColor DarkGray
    }

    if (-not $SkipRegression) {
        Write-Host "[+] Regression smoke..." -ForegroundColor Yellow
        $regArgs = @{ RepoRoot = $RepoRoot }
        if ($Release) { $regArgs.SkipBuild = $false }
        & (Join-Path $PSScriptRoot "regression_smoke.ps1") @regArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host ""
    Write-Host "Publish gate PASSED." -ForegroundColor Green
    Write-Host "Tag and push v* to trigger GitHub release CI, or run:"
    Write-Host "  cd desktop\src-tauri; cargo tauri build --bundles nsis"
}
finally {
    Pop-Location
}
