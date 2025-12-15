#!/usr/bin/env python3
"""
Setup script for SonarSniffer
Attempts to build Rust extension if possible, falls back to pure Python
"""

from setuptools import setup
try:
    from setuptools_rust import RustExtension, build_rust
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    build_rust = None

rust_extensions = []
cmdclass_dict = {}

if RUST_AVAILABLE:
    try:
        rust_extensions = [
            RustExtension(
                "rsd_parser_rust",
                "rsd_parser_rust/Cargo.toml",
            ),
        ]
        cmdclass_dict = dict(build_rust=build_rust)
    except Exception:
        # If Rust build fails, continue with pure Python
        pass

setup(
    name="rsd_parser_rust",
    version="0.1.0",
    author="SonarSniffer Contributors",
    license="MIT",
    description="High-performance RSD sonar file parser",
    long_description=open("rsd_parser_rust/README.md").read() if __import__("pathlib").Path("rsd_parser_rust/README.md").exists() else "",
    rust_extensions=rust_extensions,
    packages=["rsd_parser_rust"],
    cmdclass=cmdclass_dict,
    zip_safe=False,
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "matplotlib>=3.5.0",
        "pillow>=8.0.0",
        "requests>=2.25.0",
        "docopt>=0.6.2",
    ],
    extras_require={
        "dev": ["pytest"],
    },
)
