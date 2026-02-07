# PowerShell equivalent for convenience
$branch = 'feat/pipeline-exporters'
$msg = 'feat(pipeline): add canonical Scan, rsd adapter, waterfall/video exporters, pipeline CLI; telemetry/patching support (local only)'

if (git rev-parse --verify $branch -ErrorAction SilentlyContinue) {
    git checkout $branch
} else {
    git checkout -b $branch
}

git add -A
try {
    git commit -m $msg
    Write-Host "Committed changes on $branch"
} catch {
    Write-Host "Nothing to commit"
}

Write-Host "HEAD: $(git rev-parse --short HEAD)"
