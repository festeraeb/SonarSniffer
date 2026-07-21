# WASM build (experimental)

Browser build of SonarSniffer core. **Same repo scope** as `master` — no monorepo files.

Production flags (see [BUILD_FLAGS.md](BUILD_FLAGS.md)):

```bash
./tools/verify_standalone_repo.sh
./scripts/build_wasm.sh
# → wasm-pack build --target web --release --no-default-features
```

| Flag | Role |
|------|------|
| `--release` | Optimized wasm (not debug) |
| `--no-default-features` | No GStreamer/OpenCV; matches native product surface |
| `--target web` | Browser bindings |

Optional experimental (not used by default):

```bash
export RUSTFLAGS='--cfg getrandom_backend="wasm_js"'
./scripts/build_wasm.sh
```

Artifacts land in `dist/wasm/pkg/`. Serve `dist/wasm/` with any static file server.

Native desktop installers are built from `master` only.
