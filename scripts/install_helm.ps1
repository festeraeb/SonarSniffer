# Download and install Helm locally for current session
param(
  [string]$Version = "v3.12.0"
)
$os = "windows"
$arch = "amd64"
$zip = "helm-$Version-$os-$arch.zip"
$uri = "https://get.helm.sh/$zip"
$target = Join-Path -Path $PSScriptRoot -ChildPath "..\.tools\helm"
New-Item -ItemType Directory -Force -Path $target | Out-Null
$download = Join-Path $env:TEMP $zip
Invoke-WebRequest -Uri $uri -OutFile $download
Expand-Archive -Path $download -DestinationPath $target -Force
$helmExe = Join-Path $target "helm.exe"
if (Test-Path $helmExe) {
  Write-Output "Helm installed to $helmExe. Add to PATH for the session with: $env:PATH = '$target;' + $env:PATH"
} else {
  Write-Error "Helm download or extraction failed."
}