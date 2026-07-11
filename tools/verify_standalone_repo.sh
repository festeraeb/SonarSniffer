#!/usr/bin/env bash
# Fail if the repo contains monorepo pollution or unexpected top-level trees.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ALLOWED_TOP=(
  .cursor .git .gitattributes .github .gitignore .vscode
  AGENTS.md CHANGELOG.md Cargo.lock Cargo.toml README.md build.rs index.html
  desktop docs nauticuvs scripts setup-bootstrap soundtiles src testdata tools
)

errors=()

for entry in * .[!.]* ..?*; do
  [[ -e "$entry" ]] || continue
  [[ "$entry" == ".git" ]] && continue
  ok=0
  for a in "${ALLOWED_TOP[@]}"; do
    if [[ "$entry" == "$a" ]]; then ok=1; break; fi
  done
  if [[ "$ok" -eq 0 ]]; then
    errors+=("Unexpected top-level path: $entry")
  fi
done

# Workspace must be SonarSniffer + soundtiles + desktop only
if ! grep -q 'members = \[".", "soundtiles", "desktop/src-tauri"\]' Cargo.toml; then
  errors+=("Cargo.toml workspace must be [\".\", \"soundtiles\", \"desktop/src-tauri\"] only")
fi

# No monorepo path references in installers
if grep -rE 'wreckhunter|cesarops_repo|var/missions|wrecks_api|home_forge_tunnel' \
    scripts setup-bootstrap 2>/dev/null | grep -v 'REPO_SCOPE\|verify_standalone\|wreckhunter2000'; then
  errors+=("Installer references monorepo or cloud-tunnel paths (see grep above)")
fi

# setup-bootstrap must not ship remote fix execution
if [[ -f setup-bootstrap/src/home_forge_tunnel.rs ]]; then
  errors+=("Remove setup-bootstrap/src/home_forge_tunnel.rs — not part of SonarSniffer product")
fi

if [[ ${#errors[@]} -gt 0 ]]; then
  echo "STANDALONE REPO CHECK FAILED" >&2
  printf ' - %s\n' "${errors[@]}" >&2
  exit 1
fi

echo "OK: SonarSniffer standalone layout (core + soundtiles + desktop + installers)."
exit 0
