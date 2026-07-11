# SonarSniffer.InstallAssist.psm1 — optional LOCAL install troubleshooting via Ollama.
# Enable with: $env:SONARSNIFFER_INSTALL_ASSIST = '1'
# Requires Ollama at http://127.0.0.1:11434 (default). No cloud calls, no remote script execution.
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

    $tail = Get-Content -LiteralPath $LogPath -Tail 80 -ErrorAction SilentlyContinue
    if (-not $tail) { return $null }

    $prompt = @"
You are helping troubleshoot SonarSniffer Windows installation (phase: $Phase).
Read the install log excerpt and suggest 1-3 concrete next steps for the user.
Do NOT suggest running arbitrary remote scripts. Only winget, manual downloads, or re-running the installer.
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
        Write-Warning "Install assist unavailable (is Ollama running at $($cfg.OllamaUrl)?): $_"
        return $null
    }
}

Export-ModuleMember -Function Get-InstallAssistConfig, Invoke-LocalInstallAssist
