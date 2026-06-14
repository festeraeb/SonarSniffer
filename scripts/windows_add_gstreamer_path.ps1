#Requires -Version 5.1
<#
.SYNOPSIS
  Add installed GStreamer MSVC runtime to the Windows user PATH (and related env vars).

.DESCRIPTION
  Finds GStreamer in standard install locations and updates the current session plus
  the persistent User environment so gst-launch-1.0 works in new terminals and apps.

.EXAMPLE
  .\scripts\windows_add_gstreamer_path.ps1
#>
[CmdletBinding()]
param(
    [ValidateSet('User', 'Machine')]
    [string]$Scope = 'User'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-GStreamerInstallRoot {
    $roots = @(
        $env:GSTREAMER_1_0_ROOT_MSVC_X86_64,
        (Join-Path $env:LOCALAPPDATA 'Programs\gstreamer\1.0\msvc_x86_64'),
        'C:\gstreamer\1.0\msvc_x86_64',
        'C:\Program Files\gstreamer\1.0\msvc_x86_64'
    ) | Where-Object { $_ -and (Test-Path $_) }

    foreach ($root in $roots) {
        if (Test-Path (Join-Path $root 'bin\gst-launch-1.0.exe')) {
            return $root
        }
    }
    return $null
}

function Add-GStreamerToWindowsPath {
    param(
        [ValidateSet('User', 'Machine')]
        [string]$Scope = 'User'
    )

    $root = Get-GStreamerInstallRoot
    if (-not $root) {
        throw 'GStreamer not found. Install MSVC x86_64 runtime first (winget install -e --id gstreamerproject.gstreamer).'
    }

    $bin = Join-Path $root 'bin'
    $plugins = Join-Path $root 'lib\gstreamer-1.0'

    $currentPath = [Environment]::GetEnvironmentVariable('Path', $Scope)
    if ($null -eq $currentPath) { $currentPath = '' }

    $changed = $false
    if ($currentPath -notlike "*$bin*") {
        $newPath = if ($currentPath) { "$bin;$currentPath" } else { $bin }
        [Environment]::SetEnvironmentVariable('Path', $newPath, $Scope)
        $changed = $true
    }

    $existingRoot = [Environment]::GetEnvironmentVariable('GSTREAMER_1_0_ROOT_MSVC_X86_64', $Scope)
    if ($existingRoot -ne $root) {
        [Environment]::SetEnvironmentVariable('GSTREAMER_1_0_ROOT_MSVC_X86_64', $root, $Scope)
        $changed = $true
    }

    if (Test-Path $plugins) {
        foreach ($name in @('GST_PLUGIN_PATH', 'GST_PLUGIN_SYSTEM_PATH')) {
            $existing = [Environment]::GetEnvironmentVariable($name, $Scope)
            if ($existing -ne $plugins) {
                [Environment]::SetEnvironmentVariable($name, $plugins, $Scope)
                $changed = $true
            }
        }
    }

    # Current PowerShell session (takes effect immediately without reboot)
    if ($env:Path -notlike "*$bin*") {
        $env:Path = "$bin;$env:Path"
    }
    $env:GSTREAMER_1_0_ROOT_MSVC_X86_64 = $root
    if (Test-Path $plugins) {
        $env:GST_PLUGIN_PATH = $plugins
        $env:GST_PLUGIN_SYSTEM_PATH = $plugins
    }

    [PSCustomObject]@{
        Root = $root
        Bin = $bin
        Scope = $Scope
        Changed = $changed
        GstLaunch = (Get-Command gst-launch-1.0 -ErrorAction SilentlyContinue).Source
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    $result = Add-GStreamerToWindowsPath -Scope $Scope
    if ($result.Changed) {
        Write-Host "OK: GStreamer added to $Scope PATH" -ForegroundColor Green
    } else {
        Write-Host "OK: GStreamer already on $Scope PATH" -ForegroundColor Green
    }
    Write-Host "  Root: $($result.Root)"
    Write-Host "  gst-launch: $($result.GstLaunch)"
}
