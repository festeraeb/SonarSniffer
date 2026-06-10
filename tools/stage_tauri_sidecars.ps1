# Stage CLI sidecars for Tauri bundling (Windows).
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$Profile = "release"
)

$ErrorActionPreference = "Stop"
$targetDir = if ($env:CARGO_TARGET_DIR) { $env:CARGO_TARGET_DIR } else { Join-Path $env:LOCALAPPDATA "SonarSniffer-build\target" }
$env:CARGO_TARGET_DIR = $targetDir

function Invoke-CargoBuild {
    param([string[]]$BuildArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & cargo @BuildArgs
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) { throw "cargo build failed ($code)" }
}

Push-Location $RepoRoot
try {
    Write-Host "Building CLI sidecars..."
    if ($Profile -eq "release") {
        Invoke-CargoBuild build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli
    } else {
        Invoke-CargoBuild build --no-default-features --bin sonarsniffer-cli --bin parse_cli
    }

    $binDir = Join-Path $RepoRoot "desktop\src-tauri\binaries"
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null

    $suffix = if ($IsWindows -or $env:OS -match "Windows") { ".exe" } else { "" }
    $outProfile = if ($Profile -eq "release") { "release" } else { "debug" }
    $cliSrc = Join-Path $targetDir "$outProfile\sonarsniffer-cli$suffix"
    $parseSrc = Join-Path $targetDir "$outProfile\parse_cli$suffix"

    foreach ($pair in @(
            @{ Src = $cliSrc; Dst = Join-Path $binDir "sonarsniffer-cli$suffix" },
            @{ Src = $parseSrc; Dst = Join-Path $binDir "parse_cli$suffix" }
        )) {
        if (-not (Test-Path $pair.Src)) {
            throw "Missing build output: $($pair.Src)"
        }
        Copy-Item -Force $pair.Src $pair.Dst
        Write-Host "  staged $($pair.Dst)"
    }

    # soundtiles is optional; stage if built
    $tilesSrc = Join-Path $targetDir "$outProfile\soundtiles$suffix"
    if (Test-Path $tilesSrc) {
        Copy-Item -Force $tilesSrc (Join-Path $binDir "soundtiles$suffix")
        Write-Host "  staged soundtiles"
    }
}
finally {
    Pop-Location
}

Write-Host "Sidecars ready in desktop/src-tauri/binaries/"
