#!/usr/bin/env bash
# Run this in the repository root to create a local branch and commit the pending pipeline work.
BRANCH=feat/pipeline-exporters
MSG='feat(pipeline): add canonical Scan, rsd adapter, waterfall/video exporters, pipeline CLI; telemetry/patching support (local only)'

if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH"
fi

git add -A
if git diff --staged --quiet; then
  echo "Nothing to commit"
else
  git commit -m "$MSG"
  echo "Committed changes on $BRANCH"
fi

echo "HEAD: $(git rev-parse --short HEAD)"
