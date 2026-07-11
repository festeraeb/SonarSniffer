# SonarSniffer.Install.psm1 — shared install helpers (WebView2, logging, UAC, telemetry)
Set-StrictMode -Version Latest

$tempRoot = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
$localRoot = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $HOME '.local/share' }
$Script:InstallLogPath = Join-Path $tempRoot 'SonarSniffer-install.log'
$Script:WebView2ClientGuid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
$Script:TelemetryConsentPath = Join-Path $localRoot 'SonarSniffer\telemetry_consent.json'
# Optional telemetry — only sent when user has consented (see Get-TelemetryConsent).
$Script:DefaultTelemetryUrl = if ($env:SONARSNIFFER_TELEMETRY_URL) { $env:SONARSNIFFER_TELEMETRY_URL } else { '' }
# Optional fleet error ingest — disabled unless SONARSNIFFER_ERROR_REPORT_URL is set.
$Script:DefaultNautivecsUrl = $env:SONARSNIFFER_ERROR_REPORT_URL

# Common install failure codes (logged locally; optional remote report if URL configured)
$Script:InstallErrorCatalog = @{
    'winget-missing'       = 'winget not on PATH — install App Installer from Microsoft Store'
    'winget-timeout'       = 'winget job exceeded timeout (often store/agreement/network stall)'
    'winget-upgrade-stall' = 'winget hung checking upgrades for already-installed package'
    'webview2-missing'     = 'WebView2 runtime not detected after full cascade'
    'vcredist-missing'     = 'Visual C++ 2015-2022 x64 runtime not detected'
    'gstreamer-missing'    = 'GStreamer MSVC x86_64 runtime not on PATH or standard roots'
    'uac-timeout'          = 'Administrator elevation timed out — UAC prompt may be hidden'
    'module-missing'       = 'SonarSniffer.Install.psm1 not bundled in setup kit'
}

function Write-InstallLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Message,
        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Level = 'INFO'
    )

    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] [$Level] $Message"
    try {
        Add-Content -LiteralPath $Script:InstallLogPath -Value $line -Encoding UTF8
    } catch {
        # Best-effort logging — never block install on log I/O.
    }
    switch ($Level) {
        'ERROR' { Write-Host $line -ForegroundColor Red }
        'WARN'  { Write-Host $line -ForegroundColor Yellow }
        default { Write-Host $line -ForegroundColor Gray }
    }
}

function Get-WebView2ExeCandidates {
    $roots = @(
        'C:\Program Files (x86)\Microsoft\EdgeWebView\Application',
        'C:\Program Files\Microsoft\EdgeWebView\Application'
    )
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $exe = Get-ChildItem -LiteralPath $root -Filter 'msedgewebview2.exe' -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($exe) { return $exe.FullName }
    }
    return $null
}

function Test-WebView2Robust {
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param()

    $result = [ordered]@{
        Present = $false
        Version = $null
        Method  = 'none'
        Path    = $null
    }

    $regPaths = @(
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$Script:WebView2ClientGuid",
        "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$Script:WebView2ClientGuid"
    )
    foreach ($regPath in $regPaths) {
        if (-not (Test-Path -LiteralPath $regPath)) { continue }
        $pv = (Get-ItemProperty -LiteralPath $regPath -ErrorAction SilentlyContinue).pv
        if ($pv) {
            $result.Present = $true
            $result.Version = [string]$pv
            $result.Method = 'registry'
            Write-InstallLog "WebView2 detected via registry ($regPath) version=$pv"
            return [pscustomobject]$result
        }
    }

    $exe = Get-WebView2ExeCandidates
    if ($exe) {
        try {
            $verOut = & $exe --version 2>&1
            $ver = ($verOut | Select-Object -First 1).ToString().Trim()
            if ($ver) {
                $result.Present = $true
                $result.Version = $ver
                $result.Method = 'exe-version'
                $result.Path = $exe
                Write-InstallLog "WebView2 detected via msedgewebview2.exe version=$ver"
                return [pscustomobject]$result
            }
        } catch {
            Write-InstallLog "WebView2 exe probe failed: $_" -Level WARN
        }
    }

    $folderRoots = @(
        'C:\Program Files (x86)\Microsoft\EdgeWebView\Application',
        'C:\Program Files\Microsoft\EdgeWebView\Application'
    )
    foreach ($folder in $folderRoots) {
        if (Test-Path -LiteralPath $folder) {
            $result.Present = $true
            $result.Method = 'folder-fallback'
            $result.Path = $folder
            Write-InstallLog "WebView2 folder present (fallback) at $folder" -Level WARN
            return [pscustomobject]$result
        }
    }

    Write-InstallLog 'WebView2 not detected'
    return [pscustomobject]$result
}

function Test-VCRedistRobust {
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param()

    $result = [ordered]@{
        Present = $false
        Version = $null
        Method  = 'none'
    }

    # VC++ 2015-2022 x64 — uninstall registry + known DLL probe
    $uninstallRoots = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($root in $uninstallRoots) {
        $hit = Get-ItemProperty $root -ErrorAction SilentlyContinue |
            Where-Object {
                $_.DisplayName -match 'Microsoft Visual C\+\+.*2015.*2022.*x64' -or
                $_.DisplayName -match 'Microsoft Visual C\+\+.*2015-2022.*\(x64\)'
            } |
            Select-Object -First 1
        if ($hit) {
            $result.Present = $true
            $result.Version = [string]$hit.DisplayVersion
            $result.Method = 'uninstall-registry'
            Write-InstallLog "VC++ 2015-2022 x64 detected ($($hit.DisplayName) $($hit.DisplayVersion))"
            return [pscustomobject]$result
        }
    }

    $dllRoots = @(
        'C:\Windows\System32\vcruntime140.dll',
        'C:\Windows\System32\msvcp140.dll'
    )
    if (($dllRoots | Where-Object { Test-Path -LiteralPath $_ }).Count -ge 2) {
        $result.Present = $true
        $result.Method = 'dll-probe'
        Write-InstallLog 'VC++ runtime inferred via vcruntime140.dll + msvcp140.dll'
        return [pscustomobject]$result
    }

    Write-InstallLog 'VC++ 2015-2022 x64 not detected'
    return [pscustomobject]$result
}

function Test-GStreamerRobust {
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param()

    $result = [ordered]@{
        Present = $false
        Root    = $null
        Method  = 'none'
    }

    $roots = @(
        $env:GSTREAMER_1_0_ROOT_MSVC_X86_64,
        (Join-Path $env:LOCALAPPDATA 'Programs\gstreamer\1.0\msvc_x86_64'),
        'C:\gstreamer\1.0\msvc_x86_64',
        'C:\Program Files\gstreamer\1.0\msvc_x86_64'
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

    foreach ($r in $roots) {
        if (Test-Path (Join-Path $r 'bin\gst-launch-1.0.exe')) {
            $result.Present = $true
            $result.Root = $r
            $result.Method = 'root-probe'
            Write-InstallLog "GStreamer detected at $r"
            return [pscustomobject]$result
        }
    }

    if (Get-Command gst-launch-1.0 -ErrorAction SilentlyContinue) {
        $result.Present = $true
        $result.Root = 'PATH'
        $result.Method = 'path'
        Write-InstallLog 'GStreamer detected on PATH'
        return [pscustomobject]$result
    }

    Write-InstallLog 'GStreamer not detected'
    return [pscustomobject]$result
}

function Test-WingetPackageInstalled {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Id
    )

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { return $false }

    try {
        $list = & winget list -e --id $Id --disable-interactivity 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { return $false }
        # winget list prints header + row when installed; "No installed package found" when absent
        if ($list -match 'No installed package found') { return $false }
        return ($list -match [regex]::Escape($Id))
    } catch {
        Write-InstallLog "winget list failed for ${Id}: $_" -Level WARN
        return $false
    }
}

function Write-NautivecsInstallError {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ErrorCode,
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [string]$Phase = 'install',
        [string]$NautivecsUrl = $Script:DefaultNautivecsUrl
    )

    $catalogHint = $Script:InstallErrorCatalog[$ErrorCode]
    $fullText = @(
        "SonarSniffer install error: $ErrorCode"
        "message: $Message"
        if ($catalogHint) { "hint: $catalogHint" }
        "phase: $Phase"
        "host: $env:COMPUTERNAME"
        "os: $([Environment]::OSVersion.VersionString)"
        "log: $Script:InstallLogPath"
    ) -join "`n"

    Write-InstallLog "install error ($ErrorCode): $Message" -Level ERROR

    if (-not $NautivecsUrl) {
        Write-InstallLog 'remote error report disabled (set SONARSNIFFER_ERROR_REPORT_URL to enable)'
        return $false
    }

    try {
        $body = @{
            text      = $fullText
            tags      = "sonarsniffer,install,error,$ErrorCode,windows"
            file_path = $Script:InstallLogPath
            source    = 'sonarsniffer_installer'
        } | ConvertTo-Json -Compress

        Invoke-RestMethod -Method Post -Uri "$NautivecsUrl/add" -Body $body `
            -ContentType 'application/json' -TimeoutSec 8 | Out-Null
        Write-InstallLog "error report sent ($ErrorCode)"
        return $true
    } catch {
        Write-InstallLog "error report failed (offline?): $_" -Level WARN
        return $false
    }
}

function Install-WingetRobust {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Id,
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [switch]$SkipIfInstalled,
        [switch]$StrictSilent,
        [int]$TimeoutSeconds = 120
    )

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-NautivecsInstallError -ErrorCode 'winget-missing' -Message "winget unavailable for $Label"
        Write-InstallLog "winget missing — skip $Label" -Level WARN
        return $false
    }

    if ($SkipIfInstalled -and (Test-WingetPackageInstalled -Id $Id)) {
        Write-InstallLog "winget skip $Label — already installed ($Id)"
        return $true
    }

    # Registry / robust probes should have caught these before calling winget
    Write-InstallLog "winget install $Id ($Label) timeout=${TimeoutSeconds}s silent=$StrictSilent"
    Write-Host "  winget: $Label"

    $wingetArgs = @(
        'install', '-e', '--id', $Id,
        '--accept-package-agreements', '--accept-source-agreements',
        '--disable-interactivity'
    )
    if ($StrictSilent) {
        $wingetArgs += @('--silent', '--force')
    }

    $job = Start-Job -ScriptBlock {
        param($Args)
        & winget @Args 2>&1
        return $LASTEXITCODE
    } -ArgumentList (,$wingetArgs)

    $done = Wait-Job -Job $job -Timeout $TimeoutSeconds
    if (-not $done) {
        Stop-Job -Job $job -Force -ErrorAction SilentlyContinue
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
        Write-NautivecsInstallError -ErrorCode 'winget-timeout' -Message "$Label ($Id) timed out after ${TimeoutSeconds}s"
        Write-InstallLog "winget timed out for $Label after ${TimeoutSeconds}s" -Level WARN
        return $false
    }

    $exitCode = Receive-Job -Job $job
    Remove-Job -Job $job -Force

    if ($exitCode -ne 0) {
        Write-NautivecsInstallError -ErrorCode 'winget-upgrade-stall' -Message "$Label exit=$exitCode"
        Write-InstallLog "winget failed for $Label (exit $exitCode)" -Level WARN
        return $false
    }

    Write-InstallLog "winget OK $Label"
    return $true
}

function Invoke-ElevationWithReprompt {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$ScriptBlock,
        [string[]]$ArgumentList = @(),
        [int]$TimeoutSeconds = 90,
        [int]$MaxAttempts = 3
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        Write-InstallLog "Elevation attempt $attempt of $MaxAttempts (timeout ${TimeoutSeconds}s)"
        Write-Host ''
        Write-Host 'Windows is waiting for Administrator approval.' -ForegroundColor Yellow
        Write-Host 'Look for a UAC prompt — it may be behind other windows.' -ForegroundColor Yellow
        Write-Host ''

        $job = Start-Job -ScriptBlock $ScriptBlock -ArgumentList $ArgumentList
        $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds
        if ($completed) {
            $output = Receive-Job -Job $job
            Remove-Job -Job $job -Force
            if ($job.State -eq 'Completed') {
                Write-InstallLog "Elevation attempt $attempt succeeded"
                return $output
            }
            Write-InstallLog "Elevation job failed: $output" -Level ERROR
        } else {
            Stop-Job -Job $job -Force -ErrorAction SilentlyContinue
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
            Write-InstallLog "Elevation attempt $attempt timed out after ${TimeoutSeconds}s" -Level WARN
        }

        if ($attempt -lt $MaxAttempts) {
            $choice = Read-Host '[R] Retry elevation / [C] Cancel'
            if ($choice -match '^[Cc]') {
                throw 'User cancelled elevation'
            }
        }
    }

    throw "Elevation failed after $MaxAttempts attempts"
}

function Get-TelemetryConsent {
    if (-not (Test-Path -LiteralPath $Script:TelemetryConsentPath)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $Script:TelemetryConsentPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
    } catch {
        Write-InstallLog "Invalid telemetry consent file: $_" -Level WARN
        return $null
    }
}

function Send-TelemetryIfConsented {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Step,
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Level = 'INFO',
        [string]$InstallPhase = 'install',
        [string]$TelemetryUrl = $Script:DefaultTelemetryUrl
    )

    $consent = Get-TelemetryConsent
    if (-not $consent -or -not $consent.consented) {
        Write-InstallLog "Telemetry skipped (no consent): $Step — $Message"
        return $false
    }

    $uri = if ($consent.endpoint) { [string]$consent.endpoint } elseif ($TelemetryUrl) { $TelemetryUrl } else { '' }
    if (-not $uri) {
        Write-InstallLog "Telemetry skipped (no endpoint configured): $Step"
        return $false
    }

    $payload = [ordered]@{
        session_id      = $consent.session_id
        step            = $Step
        level           = $Level
        message         = $Message
        os_build        = [Environment]::OSVersion.VersionString
        webview_version = (Test-WebView2Robust).Version
        install_phase   = $InstallPhase
        ts              = (Get-Date).ToUniversalTime().ToString('o')
    }

    try {
        Invoke-RestMethod -Method Post -Uri $uri -Body ($payload | ConvertTo-Json -Compress) `
            -ContentType 'application/json' -TimeoutSec 15 | Out-Null
        Write-InstallLog "Telemetry sent: $Step"
        return $true
    } catch {
        Write-InstallLog "Telemetry send failed: $_" -Level WARN
        return $false
    }
}

Export-ModuleMember -Function Test-WebView2Robust, Test-VCRedistRobust, Test-GStreamerRobust, `
    Test-WingetPackageInstalled, Install-WingetRobust, Write-InstallLog, `
    Invoke-ElevationWithReprompt, Send-TelemetryIfConsented, Write-NautivecsInstallError
