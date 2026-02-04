#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
Push-Location (Join-Path $PSScriptRoot '..' 'tools' 'gstreamer_encoder')
cargo build --release
Write-Host "Built: target\release\gst_encoder.exe"
Pop-Location
