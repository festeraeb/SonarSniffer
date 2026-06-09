#Requires -Version 5.1
<#
.SYNOPSIS
  Install SonarSniffer mandatory Windows prerequisites (WebView2 + VC runtime).
.DESCRIPTION
  Video export uses the built-in AV1 encoder — GStreamer is not required.
.EXAMPLE
  .\install_sonarsniffer_prereqs_windows.ps1 -InstallMissing
#>
[CmdletBinding()]
param(
    [switch]$InstallMissing
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Pass($m)  { Write-Host "  OK  $m" -ForegroundColor Green }
function Fail($m)  { Write-Host "  !!  $m" -ForegroundColor Red }
function Info($m)  { Write-Host "  ..  $m" -ForegroundColor Gray }

function Test-WebView2 {
    return (Test-Path "C:\Program Files (x86)\Microsoft\EdgeWebView\Application") -or
           (Test-Path "C:\Program Files\Microsoft\EdgeWebView\Application")
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
Write-Host "WebView2: https://developer.microsoft.com/microsoft-edge/webview2/"
Write-Host ""

Write-Step "Visual C++ runtime"
if ($InstallMissing) { Install-Winget "Microsoft.VCRedist.2015+.x64" "Visual C++ Runtime" | Out-Null }
else { Info "Optional: winget install -e --id Microsoft.VCRedist.2015+.x64" }

Write-Step "WebView2"
if (Test-WebView2) { Pass "WebView2 present" }
else {
    Fail "WebView2 not found (required for desktop UI)"
    if ($InstallMissing) { Install-Winget "Microsoft.EdgeWebView2Runtime" "WebView2" | Out-Null } else {
        Info "Run: winget install -e --id Microsoft.EdgeWebView2Runtime"
    }
}

if (Test-WebView2) {
    Pass "Ready for SonarSniffer desktop (AV1 video built-in)"
    exit 0
}
Fail "Still missing WebView2 — restart terminal after install, then re-run this script"
exit 1
