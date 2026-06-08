#Requires -Version 5.1
<#
.SYNOPSIS
  Full SonarSniffer install: winget prereqs + MSI (or portable) + verify CLIs.
.DESCRIPTION
  Invoked by SonarSniffer-Setup.exe from its extracted staging folder ($PSScriptRoot).
  Video export uses built-in AV1 — GStreamer is not installed by this script.
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "",
    [switch]$PortableOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$KitRoot = $PSScriptRoot

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Pass($m)  { Write-Host "  OK  $m" -ForegroundColor Green }
function Fail($m)  { Write-Host "  !!  $m" -ForegroundColor Red; throw $m }
function Warn($m)  { Write-Host "  ..  $m" -ForegroundColor Yellow }

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-Winget([string]$Id, [string]$Label) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Warn "winget missing - install App Installer from Microsoft Store"
        return
    }
    Write-Host "  winget: $Label"
    & winget install -e --id $Id --accept-package-agreements --accept-source-agreements --disable-interactivity 2>&1 | Out-Host
}

function Find-KitFile([string[]]$Patterns) {
    foreach ($pat in $Patterns) {
        $hit = Get-ChildItem -Path $KitRoot -Recurse -Filter $pat -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

Clear-Host
Write-Host "SonarSniffer - full installer" -ForegroundColor Magenta
Write-Host "Kit: $KitRoot"
Write-Host ""

if (-not (Test-Admin)) {
    Fail "Run SonarSniffer-Setup.exe (it requests Administrator). Do not run this .ps1 directly unless elevated."
}

Write-Step "Prerequisites (winget)"
Install-Winget "Microsoft.VCRedist.2015+.x64" "Visual C++ Runtime"
Install-Winget "Microsoft.EdgeWebView2Runtime" "WebView2"

$msi = Find-KitFile @("SonarSniffer_*.msi", "*.msi")
$desktopExe = Find-KitFile @("SonarSniffer.exe", "tauri-appsonarsniffer.exe")
$cliProbe = Find-KitFile @("sonarsniffer-cli.exe", "sonarsniffer-cli-*.exe")
$cliParse = Find-KitFile @("parse_cli.exe", "parse_cli-*.exe")

if ($msi -and -not $PortableOnly) {
    Write-Step "Installing MSI"
    Write-Host "  $msi"
    $code = (Start-Process msiexec.exe -ArgumentList "/i", "`"$msi`"", "/passive", "/norestart" -Wait -PassThru).ExitCode
    if ($code -ne 0) { Fail "MSI failed with exit code $code" }
    Pass "Desktop app installed via MSI"
}
elseif ($desktopExe) {
    Write-Step "Portable install (no MSI in kit)"
    if (-not $InstallDir) {
        $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\SonarSniffer"
    }
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Copy-Item $desktopExe (Join-Path $InstallDir "SonarSniffer.exe") -Force
    if ($cliProbe) { Copy-Item $cliProbe (Join-Path $InstallDir "sonarsniffer-cli.exe") -Force }
    if ($cliParse) { Copy-Item $cliParse (Join-Path $InstallDir "parse_cli.exe") -Force }
    $uiSrc = Join-Path $KitRoot "ui"
    if (Test-Path $uiSrc) {
        Copy-Item $uiSrc (Join-Path $InstallDir "ui") -Recurse -Force
    }
    Pass "Copied to $InstallDir"
    $desktopExe = Join-Path $InstallDir "SonarSniffer.exe"
}
else {
    Fail "Kit missing MSI and desktop exe. Rebuild with scripts/pack_sonarsniffer_windows_setup.ps1"
}

Write-Step "CLI tools"
if ($cliProbe) { Pass "Probe: $cliProbe" } else { Warn "sonarsniffer-cli.exe not in kit" }
if ($cliParse) { Pass "Pipeline: $cliParse" } else { Warn "parse_cli.exe not in kit" }

Write-Step "Done"
Pass "SonarSniffer install finished"
Write-Host ""
Write-Host "Launch desktop app from Start Menu or run:" -ForegroundColor Gray
if ($desktopExe) { Write-Host "  $desktopExe" }

Read-Host "`nPress Enter to close"
