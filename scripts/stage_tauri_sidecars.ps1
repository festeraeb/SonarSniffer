#Requires -Version 5.1
<#
.SYNOPSIS
  Stage CLI + soundtiles binaries for Tauri externalBin.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$tauriDir = Join-Path $repoRoot "desktop\src-tauri"
$binDir = Join-Path $tauriDir "binaries"
$hostLine = (rustc -vV | Select-String "^host:").ToString() -replace "host:\s*", ""
$hostLine = $hostLine.Trim()

New-Item -ItemType Directory -Force -Path $binDir | Out-Null

Push-Location $repoRoot
try {
    cargo build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli
    if ($LASTEXITCODE -ne 0) { throw "CLI build failed" }
    cargo build --release -p soundtiles
    if ($LASTEXITCODE -ne 0) { throw "soundtiles build failed" }
} finally {
    Pop-Location
}

$ssTarget = Join-Path $repoRoot "target\release"
foreach ($pair in @(
        @("sonarsniffer-cli.exe", "sonarsniffer-cli"),
        @("parse_cli.exe", "parse_cli"),
        @("soundtiles.exe", "soundtiles")
    )) {
    $src = Join-Path $ssTarget $pair[0]
    if (-not (Test-Path $src)) { throw "Missing $src" }
    $dst = Join-Path $binDir ("{0}-{1}.exe" -f $pair[1], $hostLine)
    Copy-Item $src $dst -Force
    Write-Host "  + binaries\$([IO.Path]::GetFileName($dst))"
}
