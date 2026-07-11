#!/usr/bin/env bash
# Build SonarSniffer WASM package (browser). Requires wasm-pack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${OUT:-$ROOT/dist/wasm}"

if ! command -v wasm-pack >/dev/null 2>&1; then
  echo "wasm-pack not found. Install: cargo install wasm-pack" >&2
  exit 1
fi

"$ROOT/tools/verify_standalone_repo.sh"

mkdir -p "$OUT"
cd "$ROOT"

echo "=== Building sonarsniffer WASM (no default features) ==="
wasm-pack build --target web --out-dir "$OUT/pkg" --no-default-features

if [[ -f "$ROOT/index.html" ]]; then
  cp "$ROOT/index.html" "$OUT/"
fi

echo ""
echo "WASM artifacts: $OUT/pkg/"
echo "Serve locally:  python3 -m http.server -d $OUT 8080"
