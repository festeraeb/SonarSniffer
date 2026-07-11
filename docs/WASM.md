# WASM build (experimental)

Browser build of SonarSniffer core. **Same repo scope** as `master` — no monorepo files.

```bash
./tools/verify_standalone_repo.sh
./scripts/build_wasm.sh
```

Artifacts land in `dist/wasm/pkg/`. Serve `dist/wasm/` with any static file server.

Native desktop installers are built from `master` only.
