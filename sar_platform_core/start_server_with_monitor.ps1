# SAR Platform Server Startup with Monitoring
# This script starts the API server and monitor together

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SAR Platform API Server + Monitor" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if ($isAdmin) {
    Write-Host "Running as Administrator" -ForegroundColor Green
    Write-Host "Both port 8000 and port 80 will be available" -ForegroundColor Green
    Write-Host ""
}
else {
    Write-Host "NOT running as Administrator" -ForegroundColor Yellow
    Write-Host "Only port 8000 will work (port 80 requires admin)" -ForegroundColor Yellow
    Write-Host ""
}

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiFile = Join-Path $scriptDir "intake_api.py"
$monitorFile = Join-Path $scriptDir "monitor_server.py"

Write-Host "Starting SAR Platform Server..." -ForegroundColor Cyan
Write-Host "API File: $apiFile" -ForegroundColor Gray
Write-Host "Monitor File: $monitorFile" -ForegroundColor Gray
Write-Host ""

# Start the API server in a background job
Write-Host "Launching API Server in background..." -ForegroundColor Cyan
$serverJob = Start-Job -ScriptBlock {
    param($dir, $apiFile)
    Set-Location $dir
    conda run -p C:\Users\feste\Miniconda3 python $apiFile
} -ArgumentList $scriptDir, $apiFile

Write-Host "Server job started (ID: $($serverJob.Id))" -ForegroundColor Green
Write-Host ""

# Wait a moment for server to start
Start-Sleep -Seconds 3

# Start the monitor in the current terminal
Write-Host "Starting Monitor in current terminal..." -ForegroundColor Cyan
Write-Host "Monitor will show survey submissions in real-time" -ForegroundColor Cyan
Write-Host ""

# Run monitor
conda run -p C:\Users\feste\Miniconda3 python $monitorFile

# If user closes monitor, ask about the server
Write-Host ""
Write-Host "Monitor stopped." -ForegroundColor Yellow
$keepServer = Read-Host "Keep API server running? (y/n)"

if ($keepServer -eq 'n' -or $keepServer -eq 'no') {
    Write-Host ""
    Write-Host "Stopping API server..." -ForegroundColor Yellow
    Stop-Job -Job $serverJob -Force
    Remove-Job -Job $serverJob
    Write-Host "Server stopped." -ForegroundColor Gray
}
else {
    Write-Host ""
    Write-Host "Server is still running in background" -ForegroundColor Green
    Write-Host "Job ID: $($serverJob.Id)" -ForegroundColor Green
    Write-Host ""
    Write-Host "To stop it later, use: Stop-Job -Id $($serverJob.Id)" -ForegroundColor Gray
}

Write-Host ""
