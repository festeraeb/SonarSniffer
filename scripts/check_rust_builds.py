"""Diagnostic script to check Rust extension availability and provide build guidance."""
import sys, os

print("Checking Rust-based parser & core modules...")

# Check rsd_parser_rust
sys.path.insert(0, os.path.abspath('src'))
try:
    import rsd_parser_rust
    print("rsd_parser_rust import: OK")
    print("  module:", getattr(rsd_parser_rust, '__file__', '<namespace>'))
except Exception as e:
    print("rsd_parser_rust import: FAILED")
    print("  Reason:", e)
    print()
    print("If you need the Rust-based parser for improved performance, build it with maturin:")
    print("  # Install maturin: pip install maturin")
    print("  # Build a wheel for your Python version and platform:")
    print("  maturin build -i python -b release -o dist/")
    print("  # Or install in-place for development:")
    print("  maturin develop --release")

# Check cesarops_core (drift analyzer)
try:
    import cesarops_core
    print("cesarops_core import: OK")
except Exception as e:
    print("cesarops_core import: FAILED")
    print("  Reason:", e)
    print("The Rust drift analyzer is built from the rust_core/ crate. Use maturin or cargo + pyo3/maturin to build and install.")
