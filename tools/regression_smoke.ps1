# SonarSniffer regression smoke — Millers, Holloway, Sonar010
param(
    [string]$Exe = "",
    [string]$OutRoot = "$env:LOCALAPPDATA\sonar-regression",
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$GoldenRoot = "",
    [switch]$SkipBuild,
    [switch]$Fast
)

$files = @(
    @{ Name = "Millers"; Path = Join-Path $RepoRoot "Copy of Millers Folley Cove.RSD"; ExpectLayout = "butterfly" },
    @{ Name = "Holloway"; Path = Join-Path $RepoRoot "Holloway.RSD"; ExpectLayout = "butterfly" },
    @{ Name = "Sonar010"; Path = Join-Path $RepoRoot "Sonar010.RSD"; ExpectLayout = "single_wing" }
)

if (-not $GoldenRoot) {
    $GoldenRoot = Join-Path $RepoRoot "testdata\golden"
}

$targetDir = if ($env:CARGO_TARGET_DIR) { $env:CARGO_TARGET_DIR } else { Join-Path $env:LOCALAPPDATA "SonarSniffer-build\target" }
$env:CARGO_TARGET_DIR = $targetDir

if (-not $Exe) {
    $Exe = Join-Path $targetDir "release\parse_cli.exe"
}

if (-not $SkipBuild -and -not (Test-Path $Exe)) {
    Write-Host "Building parse_cli..."
    Push-Location $RepoRoot
    cargo build --release --bin parse_cli
    Pop-Location
}

New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null
$summary = @()
$failed = 0

foreach ($f in $files) {
    if (-not (Test-Path $f.Path)) {
        $summary += [pscustomobject]@{ File = $f.Name; Status = "SKIP"; Note = "missing $($f.Path)" }
        continue
    }
    $out = Join-Path $OutRoot $f.Name
    if (Test-Path $out) { Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue }
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    Write-Host "=== $($f.Name) ==="
    $logPath = Join-Path $out "regression.log"
    $extraFlags = if ($Fast) { @("--fast") } else { @() }
    $cliArgs = @(
        $f.Path,
        "--no-video"
    ) + $extraFlags + @(
        "--output-dir", $out,
        "--summary"
    )
    & $Exe @cliArgs *> $logPath
    $jsonText = Get-Content $logPath -Raw
    $parsed = $null
    try {
        if ($jsonText -match '(?ms)^\{\s*"channels"\s*:') {
            $parsed = [regex]::Match($jsonText, '(?ms)^\{\s*"channels".*\z').Value | ConvertFrom-Json
        } elseif ($jsonText -match '\{') {
            $jsonStart = $jsonText.IndexOf("{`"channels`"")
            if ($jsonStart -lt 0) { $jsonStart = $jsonText.LastIndexOf("{") }
            if ($jsonStart -ge 0) {
                $parsed = $jsonText.Substring($jsonStart) | ConvertFrom-Json
            }
        }
    } catch { }

    $portCh = $null
    $starCh = $null
    $conf = $null
    $layout = "n/a"
    if ($parsed) {
        if ($parsed.resolvedSidescanPair) {
            $portCh = $parsed.resolvedSidescanPair[0]
            $starCh = $parsed.resolvedSidescanPair[1]
        }
        if ($parsed.stitchLayout) {
            $conf = $parsed.stitchLayout.autoConfidence
            $layout = $parsed.stitchLayout.recommendedId
        }
    }

    $stem = [System.IO.Path]::GetFileNameWithoutExtension($f.Path)
    $actualOut = $out
    if ($parsed -and $parsed.PSObject.Properties['outputs']) {
        $outObj = $parsed.outputs
        if ($outObj -and $outObj.PSObject.Properties['outputDir'] -and $outObj.outputDir) {
            $actualOut = $outObj.outputDir
        }
    }
    if (-not (Test-Path $actualOut)) {
        $stemDir = Get-ChildItem -Path $OutRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq $stem -or $_.Name -like "${stem}_*" } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($stemDir) { $actualOut = $stemDir.FullName }
    }

    $mosaic = Get-ChildItem -Path $actualOut -Recurse -Filter "mosaic_combined.png" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $mosaic) {
        $mosaic = Get-ChildItem -Path $OutRoot -Recurse -Filter "mosaic_combined.png" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match [regex]::Escape($stem) } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
    }
    $status = if ($mosaic) { "OK" } else { "FAIL"; $failed++ }

    $goldenNote = ""
    if ($mosaic -and (Test-Path $GoldenRoot)) {
        $golden = Join-Path $GoldenRoot "$($f.Name)\mosaic_combined.png"
        if (Test-Path $golden) {
            $a = (Get-FileHash $mosaic.FullName -Algorithm SHA256).Hash
            $b = (Get-FileHash $golden -Algorithm SHA256).Hash
            if ($a -ne $b) {
                $status = "FAIL"
                $failed++
                $goldenNote = "hash mismatch vs golden"
            } else {
                $goldenNote = "golden match"
            }
        }
    }

    $summary += [pscustomobject]@{
        File       = $f.Name
        Status     = $status
        Layout     = $layout
        Confidence = $conf
        Port       = $portCh
        Star       = $starCh
        Mosaic     = if ($mosaic) { $mosaic.FullName } else { "" }
        Golden     = $goldenNote
        Log        = $logPath
    }
}

$summary | Format-Table -AutoSize
$summaryPath = Join-Path $OutRoot "regression_summary.json"
$summary | ConvertTo-Json -Depth 5 | Set-Content $summaryPath
Write-Host "Summary: $summaryPath"

if ($failed -gt 0) {
    Write-Host "Regression FAILED ($failed case(s))." -ForegroundColor Red
    exit 1
}
Write-Host "Regression OK." -ForegroundColor Green
exit 0
