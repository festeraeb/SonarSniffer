# Golden mosaic baselines (optional)

Place reference PNGs here to enable hash comparison in `tools/regression_smoke.ps1`:

```
testdata/golden/Millers/mosaic_combined.png
testdata/golden/Holloway/mosaic_combined.png
testdata/golden/Sonar010/mosaic_combined.png
```

Generate baselines after a known-good run:

```powershell
$src = "$env:LOCALAPPDATA\sonar-regression"
$dst = "testdata\golden"
foreach ($name in "Millers","Holloway","Sonar010") {
  $png = Get-ChildItem "$src\$name" -Recurse -Filter mosaic_combined.png | Select-Object -First 1
  if ($png) {
    New-Item -Force -ItemType Directory (Join-Path $dst $name) | Out-Null
    Copy-Item $png.FullName (Join-Path $dst $name "mosaic_combined.png")
  }
}
```
