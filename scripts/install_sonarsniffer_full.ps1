#Requires -Version 5.1
<#
.SYNOPSIS
  Full SonarSniffer install: prereq probes + optional winget + MSI (or portable) + verify CLIs.
.DESCRIPTION
  Invoked by SonarSniffer-Setup.exe from its extracted staging folder ($PSScriptRoot).
  Registry/path probes run first; winget only when a component is missing (-SkipWinget to disable).
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "",
    [switch]$PortableOnly,
    [switch]$SkipWinget,
    [switch]$StrictSilent
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$KitRoot = $PSScriptRoot

$ModulePath = Join-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) "lib\SonarSniffer.Install.psm1"
if (-not (Test-Path -LiteralPath $ModulePath)) {
    $repoModule = Join-Path (Split-Path (Split-Path $KitRoot -Parent) -Parent) "scripts\lib\SonarSniffer.Install.psm1"
    if (Test-Path -LiteralPath $repoModule) { $ModulePath = $repoModule }
}
if (-not (Test-Path -LiteralPath $ModulePath)) {
    throw "Missing install module: SonarSniffer.Install.psm1 — rebuild kit with pack_sonarsniffer_windows_setup.ps1"
}
Import-Module $ModulePath -Force

$AssistModulePath = Join-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) "lib\SonarSniffer.InstallAssist.psm1"
if (Test-Path -LiteralPath $AssistModulePath) {
    Import-Module $AssistModulePath -Force
}

function Invoke-InstallAssistOnFailure {
    param([string]$Phase = 'install')
    if (Get-Command Invoke-LocalInstallAssist -ErrorAction SilentlyContinue) {
        Invoke-LocalInstallAssist -LogPath $Script:InstallLogPath -Phase $Phase | Out-Null
    }
}

function Write-Step($m) {
    Write-InstallLog $m
    Write-Host "`n=== $m ===" -ForegroundColor Cyan
}
function Pass($m)  { Write-InstallLog $m; Write-Host "  OK  $m" -ForegroundColor Green }
function Fail($m)  { Write-InstallLog $m -Level ERROR; Write-Host "  !!  $m" -ForegroundColor Red; throw $m }
function Warn($m)  { Write-InstallLog $m -Level WARN; Write-Host "  ..  $m" -ForegroundColor Yellow }
function Info($m)  { Write-InstallLog $m; Write-Host "  ..  $m" -ForegroundColor Gray }

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-Winget([string]$Id, [string]$Label) {
    if ($SkipWinget) {
        Warn "SkipWinget set — not installing $Label via winget"
        return
    }
    $timeout = if ($StrictSilent) { 90 } else { 120 }
    $ok = Install-WingetRobust -Id $Id -Label $Label -SkipIfInstalled -StrictSilent:$StrictSilent `
        -TimeoutSeconds $timeout
    if ($ok) { Pass "$Label ready" }
    else { Warn "$Label winget step failed or skipped — see install log" }
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

Write-Step "Prerequisites"
if ($SkipWinget) {
    Info "SkipWinget: registry/path probes only — no winget network calls"
}

$vc = Test-VCRedistRobust
if ($vc.Present) {
    Pass "Visual C++ Runtime present ($($vc.Method) $($vc.Version))"
} else {
    Write-InstallLog "VC++ missing — winget fallback"
    Install-Winget "Microsoft.VCRedist.2015+.x64" "Visual C++ Runtime"
}

$wv2 = Test-WebView2Robust
if ($wv2.Present) {
    Pass "WebView2 already present ($($wv2.Method) $($wv2.Version)) — skipping winget"
    Send-TelemetryIfConsented -Step 'webview2-detect' -Message "present $($wv2.Version)" | Out-Null
} else {
    Write-InstallLog "WebView2 missing — winget fallback"
    if (-not $SkipWinget) {
        Install-Winget "Microsoft.EdgeWebView2Runtime" "WebView2"
    } else {
        Write-NautivecsInstallError -ErrorCode 'webview2-missing' -Message 'WebView2 absent and SkipWinget set'
        Warn "WebView2 missing — install manually or re-run without -SkipWinget"
    }
}

$gstCheck = Test-GStreamerRobust
if ($gstCheck.Present) {
    Pass "GStreamer present ($($gstCheck.Method) $($gstCheck.Root))"
} else {
    Write-InstallLog "GStreamer missing — winget fallback"
    Install-Winget "gstreamerproject.gstreamer" "GStreamer"
}

Write-Step "GStreamer PATH (user env)"
$pathScript = Join-Path $KitRoot "windows_add_gstreamer_path.ps1"
if (-not (Test-Path $pathScript)) {
    $repoScripts = Join-Path (Split-Path (Split-Path $KitRoot -Parent) -Parent) "scripts\windows_add_gstreamer_path.ps1"
    if (Test-Path $repoScripts) { $pathScript = $repoScripts }
}
if (Test-Path $pathScript) {
    try {
        . $pathScript
        $gstPath = Add-GStreamerToWindowsPath -Scope User
        Pass "GStreamer on PATH ($($gstPath.Root))"
    } catch {
        Warn "GStreamer PATH not updated: $_"
    }
} else {
    Warn "windows_add_gstreamer_path.ps1 missing from kit"
}

$msi = Find-KitFile @("SonarSniffer_*.msi", "*.msi")
$desktopExe = Find-KitFile @("SonarSniffer.exe", "tauri-appsonarsniffer.exe")
$cliProbe = Find-KitFile @("sonarsniffer-cli.exe", "sonarsniffer-cli-*.exe")
$cliParse = Find-KitFile @("parse_cli.exe", "parse_cli-*.exe")

if ($msi -and -not $PortableOnly) {
    Write-Step "Installing MSI"
    Write-Host "  $msi"
    $code = (Start-Process msiexec.exe -ArgumentList "/i", "`"$msi`"", "/passive", "/norestart" -Wait -PassThru).ExitCode
    if ($code -ne 0) {
        Write-NautivecsInstallError -ErrorCode 'msi-failed' -Message "msiexec exit $code"
        Fail "MSI failed with exit code $code"
    }
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
    Write-NautivecsInstallError -ErrorCode 'kit-incomplete' -Message 'Missing MSI and desktop exe'
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

Invoke-InstallAssistOnFailure -Phase 'success'

Read-Host "`nPress Enter to close"
