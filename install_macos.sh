#!/bin/bash
# SonarSniffer macOS/Linux Installation Script
# Creates Python environment and installs SonarSniffer

echo "========================================"
echo "  SonarSniffer Professional Installation"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python 3.8+ from https://python.org"
    echo "Or use your system package manager:"
    echo "  macOS: brew install python3"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi

echo "Python 3 found. Checking version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Check if we're in a virtual environment
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "Already in virtual environment: $VIRTUAL_ENV"
    echo "Installing SonarSniffer..."
    pip install -e .
else
    # Check if conda is available
    if command -v conda &> /dev/null; then
        echo "Conda found. Creating conda environment..."
        conda create -n sonarsniffer python=3.11 -y
        echo "Activating conda environment..."
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate sonarsniffer
        echo "Installing SonarSniffer..."
        pip install -e .
    else
        # Use venv
        echo "Creating virtual environment with venv..."
        python3 -m venv sonarsniffer_env
        echo "Activating virtual environment..."
        source sonarsniffer_env/bin/activate
        echo "Upgrading pip..."
        python -m pip install --upgrade pip
        echo "Installing SonarSniffer..."
        pip install -e .
    fi
fi

if [ $? -eq 0 ]; then
    echo
    echo "========================================"
    echo "  Installation Complete!"
    echo "========================================"
    echo
    echo "SonarSniffer has been successfully installed."
    echo
    echo "To use SonarSniffer:"
    echo "  1. Activate the environment (if using conda/venv)"
    if command -v conda &> /dev/null; then
        echo "     conda activate sonarsniffer"
    else
        echo "     source sonarsniffer_env/bin/activate"
    fi
    echo "  2. Run: sonarsniffer --help"
    echo
    echo "For analysis: sonarsniffer analyze your_file.RSD"
    echo "For web interface: sonarsniffer web your_file.RSD"
    echo
    echo "Contact: festeraeb@yahoo.com for licensing information."
    echo
else
    echo
    echo "ERROR: Installation failed!"
    echo "Please check the error messages above."
    echo
    exit 1
fi