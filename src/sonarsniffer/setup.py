#!/usr/bin/env python3
"""
Setup script for SonarSniffer - Professional Marine Survey Analysis Software
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
try:
    long_description = (this_directory / "docs" / "README.md").read_text(encoding='utf-8')
except UnicodeDecodeError:
    long_description = """
SonarSniffer - Professional Marine Survey Analysis Software

A comprehensive tool for analyzing marine sonar data with AI-enhanced target detection,
web-based visualization, and professional reporting capabilities.

Author: NautiDog Inc.
Contact: festeraeb@yahoo.com
"""

# Read requirements
requirements = []
try:
    with open("requirements.txt", "r") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    requirements = [
        "numpy>=1.21.0",
        "matplotlib>=3.5.0",
        "pillow>=8.0.0",
        "requests>=2.25.0",
        "sqlite3",
        "pathlib",
        "datetime",
    ]

setup(
    name="sonarsniffer",
    version="1.0.0-beta",
    author="NautiDog Inc.",
    author_email="festeraeb@yahoo.com",
    description="Professional marine survey analysis software with AI-enhanced target detection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/festeraeb/SonarSniffer",
    packages=find_packages(where="src", exclude=["*license_key_generator*"]),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: End Users/Desktop",
        "License :: Other/Proprietary License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    keywords="sonar marine survey analysis target detection bathymetry",
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ],
        "web": [
            "flask>=2.0",
            "flask-cors",
        ],
        "ai": [
            "tensorflow>=2.8",
            "scikit-learn>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "sonarsniffer=sonarsniffer.cli:main",
            "sonar-web=sonarsniffer.web.app:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)