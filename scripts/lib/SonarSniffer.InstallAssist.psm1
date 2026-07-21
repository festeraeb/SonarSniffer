# SonarSniffer.InstallAssist.psm1 — packed local install self-healing (ip branch).
# Enable with: $env:SONARSNIFFER_INSTALL_ASSIST = '1'
# Uses deterministic heal hints always; optional Ollama narrative when available.
# No cloud calls, no remote script execution.
Set-StrictMode -Version Latest

function Get-InstallAssistConfig {
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param()

    $enabled = $env:SONARSNIFFER_INSTALL_ASSIST -match '^(1|true|yes)$'
    $ollama = if ($env:SONARSNIFFER_OLLAMA_URL) { $env:SONARSNIFFER_OLLAMA_URL } else { 'http://127.0.0.1:11434' }
    $model = if ($env:SONARSNIFFER_OLLAMA_MODEL) { $env:SONARSNIFFER_OLLAMA_MODEL } else { 'tinyllama' }

    [pscustomobject]@{
        Enabled   = $enabled
        OllamaUrl = $ollama.TrimEnd('/')
        Model     = $model
    }
}

function Get-DeterministicHealHints {
    [CmdletBinding()]
    [OutputType([string[]])]
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$LogLines,
        [string]$Phase = 'install'
    )

    $text = ($LogLines -join "`n")
    $hints = New-Object System.Collections.Generic.List[string]

    if ($text -match 'webview2|WebView2') {
        $hints.Add('Install Microsoft Edge WebView2 Runtime (winget: Microsoft.EdgeWebView2Runtime), then re-run SonarSniffer-Setup.exe as Administrator.')
    }
    if ($text -match 'VC\+\+|VCRedist|vcruntime|MSVCP') {
        $hints.Add('Install Visual C++ 2015-2022 x64 Redistributable (winget: Microsoft.VCRedist.2015+.x64), then re-run the installer.')
    }
    if ($text -match 'GStreamer|gstreamer') {
        $hints.Add('GStreamer is optional for AV1 builds. If you need legacy H.264, install GStreamer MSVC runtime and re-open a new Admin PowerShell before retrying.')
    }
    if ($text -match 'winget|0x8A15000|App Installer') {
        $hints.Add('Update App Installer from the Microsoft Store, or re-run with -SkipWinget after installing WebView2/VC++ manually.')
    }
    if ($text -match 'Access is denied|0x80070005|Administrator|elevat') {
        $hints.Add('Right-click SonarSniffer-Setup.exe → Run as administrator. Approve the UAC prompt (check behind other windows).')
    }
    if ($text -match 'MSI|msiexec|1603|1618') {
        $hints.Add('Close any running SonarSniffer/msiexec processes, reboot if another install is stuck, then re-run the Setup exe.')
    }
    if ($hints.Count -eq 0) {
        $hints.Add("Re-run SonarSniffer-Setup.exe as Administrator (phase: $Phase). If it fails again, capture %TEMP%\SonarSniffer-install*.log and retry with -SkipWinget after manual WebView2 install.")
    }

    return $hints.ToArray()
}

function Write-HealHints {
    param([string[]]$Hints, [string]$Title = 'Local install self-heal')
    if (-not $Hints -or $Hints.Count -eq 0) { return }
    Write-Host ''
    Write-Host "--- $Title ---" -ForegroundColor Cyan
    $i = 1
    foreach ($h in $Hints) {
        Write-Host ("{0}. {1}" -f $i, $h)
        $i++
    }
    Write-Host ('-' * ($Title.Length + 8)) -ForegroundColor Cyan
}

function Invoke-LocalInstallAssist {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [string]$Phase = 'install'
    )

    $cfg = Get-InstallAssistConfig
    if (-not $cfg.Enabled) { return $null }

    if (-not (Test-Path -LiteralPath $LogPath)) {
        Write-Warning "Install assist: log not found at $LogPath"
        return $null
    }

    $tail = @(Get-Content -LiteralPath $LogPath -Tail 80 -ErrorAction SilentlyContinue)
    if (-not $tail) { return $null }

    $hints = Get-DeterministicHealHints -LogLines $tail -Phase $Phase
    Write-HealHints -Hints $hints -Title 'Local install self-heal (deterministic)'

    $prompt = @"
You are helping troubleshoot SonarSniffer Windows installation (phase: $Phase).
Read the install log excerpt and suggest 1-3 concrete next steps for the user.
Do NOT suggest running arbitrary remote scripts. Only winget, manual downloads, or re-running the installer.
Prefer these known fixes when they match the log: WebView2, VC++ redist, Admin/UAC, winget App Installer, msiexec conflicts.
Log excerpt:
$($tail -join "`n")
"@

    $body = @{
        model  = $cfg.Model
        prompt = $prompt
        stream = $false
    } | ConvertTo-Json -Compress

    try {
        $resp = Invoke-RestMethod -Method Post -Uri "$($cfg.OllamaUrl)/api/generate" `
            -Body $body -ContentType 'application/json' -TimeoutSec 45
        $text = [string]$resp.response
        if ($text) {
            Write-Host ''
            Write-Host '--- Local install assist (Ollama) ---' -ForegroundColor Cyan
            Write-Host $text
            Write-Host '-----------------------------------' -ForegroundColor Cyan
        }
        return $text
    } catch {
        Write-Warning "Ollama assist unavailable at $($cfg.OllamaUrl) — deterministic heal hints above still apply: $_"
        return ($hints -join "`n")
    }
}

Export-ModuleMember -Function Get-InstallAssistConfig, Get-DeterministicHealHints, Invoke-LocalInstallAssist
