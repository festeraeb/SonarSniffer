#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cd tools/gstreamer_encoder
cargo build --release
echo "Built: target/release/gst_encoder"
