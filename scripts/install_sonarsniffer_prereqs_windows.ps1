#Requires -Version 5.1
<#
.SYNOPSIS
  Install SonarSniffer mandatory Windows prerequisites (GStreamer + WebView2).
.DESCRIPTION
  Run BEFORE or AFTER MSI install on a test laptop. Uses winget when available.
  GStreamer is not bundled in the SonarSniffer installer — video export requires it.
.EXAMPLE
  .\install_sonarsniffer_prereqs_windows.ps1
.EXAMPLE
  .\install_sonarsniffer_prereqs_windows.ps1 -InstallMissing
#>
[CmdletBinding()]
param(
    [switch]$InstallMissing
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ModulePath = Join-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) "lib\SonarSniffer.Install.psm1"
if (-not (Test-Path -LiteralPath $ModulePath)) {
    throw "Missing install module: $ModulePath"
}
Import-Module $ModulePath -Force

function Write-Step($m) {
    Write-InstallLog $m
    Write-Host "`n=== $m ===" -ForegroundColor Cyan
}
function Pass($m)  { Write-InstallLog $m; Write-Host "  OK  $m" -ForegroundColor Green }
function Fail($m)  { Write-InstallLog $m -Level ERROR; Write-Host "  !!  $m" -ForegroundColor Red }
function Info($m)  { Write-InstallLog $m; Write-Host "  ..  $m" -ForegroundColor Gray }

function Test-GStreamer {
    $roots = @(
        $env:GSTREAMER_1_0_ROOT_MSVC_X86_64,
        (Join-Path $env:LOCALAPPDATA "Programs\gstreamer\1.0\msvc_x86_64"),
        "C:\gstreamer\1.0\msvc_x86_64",
        "C:\Program Files\gstreamer\1.0\msvc_x86_64"
    ) | Where-Object { $_ -and (Test-Path $_) }
    foreach ($r in $roots) {
        if (Test-Path (Join-Path $r "bin\gst-launch-1.0.exe")) { return $r }
    }
    if (Get-Command gst-launch-1.0 -ErrorAction SilentlyContinue) { return "PATH" }
    return $null
}

function Test-WebView2 {
    return (Test-WebView2Robust).Present
}

function Install-Winget([string]$Id, [string]$Label) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail "winget not found - install App Installer from Microsoft Store"
        return $false
    }
    Info "winget install $Id"
    & winget install -e --id $Id --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Fail "winget failed for $Label (exit $LASTEXITCODE). Try running PowerShell as Administrator."
        return $false
    }
    Pass "$Label installed via winget"
    return $true
}

Write-Host ""
Write-Host "SonarSniffer - Windows prerequisite check" -ForegroundColor Magenta
Write-Host "GStreamer: https://gstreamer.freedesktop.org/download/#windows"
Write-Host "WebView2:  https://developer.microsoft.com/microsoft-edge/webview2/"
Write-Host ""

Write-Step "GStreamer"
$gst = Test-GStreamer
if ($gst) { Pass "GStreamer found ($gst)" }
else {
    Fail "GStreamer not found (required for video export)"
    if ($InstallMissing) { Install-Winget "gstreamerproject.gstreamer" "GStreamer" } else {
        Info "Run: winget install -e --id gstreamerproject.gstreamer"
        Info "Or download MSVC x86_64 RUNTIME from gstreamer.freedesktop.org"
    }
}

Write-Step "WebView2"
$wv2Info = Test-WebView2Robust
if ($wv2Info.Present) {
    Pass "WebView2 present ($($wv2Info.Method) $($wv2Info.Version))"
} else {
    Fail "WebView2 not found (required for desktop UI)"
    if ($InstallMissing) { Install-Winget "Microsoft.EdgeWebView2Runtime" "WebView2" } else {
        Info "Run: winget install -e --id Microsoft.EdgeWebView2Runtime"
    }
}

Write-Step "GStreamer PATH (user env)"
$pathScript = Join-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) "windows_add_gstreamer_path.ps1"
if (Test-Path $pathScript) {
    try {
        . $pathScript
        $gstPath = Add-GStreamerToWindowsPath -Scope User
        Pass "GStreamer on PATH ($($gstPath.Root))"
    } catch {
        Info "GStreamer PATH skipped: $_"
    }
} else {
    Info "Missing $pathScript"
}

Write-Step "Re-check after PATH"
$gst2 = Test-GStreamer
$wv2 = (Test-WebView2Robust).Present
if ($gst2 -and $wv2) {
    Pass "Ready for SonarSniffer desktop + video"
    exit 0
}
Fail "Still missing components - restart terminal after install, then re-run this script"
exit 1
