#!/usr/bin/env bash
# Push SonarSniffer master + wasm + ip and release tag (triggers .github/workflows/release.yml).
set -euo pipefail

SONAR_CLONE="${SONAR_CLONE:-/home/cesarops/repos/SonarSniffer}"
VERSION="${1:-0.8.20}"
TAG="v${VERSION}"
GITHUB_USER="${GITHUB_USER:-festeraeb}"
GITHUB_REPO="${GITHUB_REPO:-festeraeb/SonarSniffer}"

for f in "${HOME}/.ssh/credentials.ssh" "/home/cesarops/wreckhunter2000-1/scripts/credentials.sh"; do
  [[ -f "$f" ]] && set -a && source "$f" && set +a
done

[[ -n "${GITHUB_PAT:-}" ]] || { echo "FATAL: set GITHUB_PAT in ~/.ssh/credentials.ssh or scripts/credentials.sh" >&2; exit 1; }

"$SONAR_CLONE/tools/verify_standalone_repo.sh"

AUTH="https://${GITHUB_USER}:${GITHUB_PAT}@github.com/${GITHUB_REPO}.git"
git -C "$SONAR_CLONE" remote set-url origin "$AUTH"

echo "Pushing master, wasm, ip, and tag ${TAG}..."
git -C "$SONAR_CLONE" push origin master
git -C "$SONAR_CLONE" push -u origin wasm
git -C "$SONAR_CLONE" push -u origin ip
git -C "$SONAR_CLONE" push origin "$TAG"

echo ""
echo "Release CI: https://github.com/${GITHUB_REPO}/actions"
echo "Release:    https://github.com/${GITHUB_REPO}/releases/tag/${TAG}"
