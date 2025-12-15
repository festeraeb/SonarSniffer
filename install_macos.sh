#!/bin/bash
# SonarSniffer macOS Installation Script
# Dynamically fetches latest Python release and installs SonarSniffer
# Handles Homebrew, Rust, Xcode tools, and all dependencies

set -e  # Exit on any error

echo ""
echo "========================================"
echo "  SonarSniffer Professional Installation"
echo "  macOS Version"
echo "========================================"
echo ""

# Detect macOS version
MACOS_VERSION=$(sw_vers -productVersion)
echo "✓ Detected macOS $MACOS_VERSION"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    HOMEBREW_PREFIX="/opt/homebrew"
else
    HOMEBREW_PREFIX="/usr/local"
fi
echo "✓ Detected architecture: $ARCH ($HOMEBREW_PREFIX)"

# Check if Homebrew is installed
echo ""
if ! command -v brew &> /dev/null; then
    echo "⚠ Homebrew is not installed"
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH
    eval "$($HOMEBREW_PREFIX/bin/brew shellenv)"
    echo "✓ Homebrew installed"
else
    BREW_VERSION=$(brew --version | head -n1)
    echo "✓ Homebrew already installed: $BREW_VERSION"
fi

# Check for Xcode Command Line Tools
echo ""
echo "[1/5] Checking Xcode Command Line Tools..."
if ! xcode-select -p &> /dev/null; then
    echo "⚠ Xcode Command Line Tools are not installed"
    echo "Installing Xcode Command Line Tools..."
    xcode-select --install
    
    # Wait for installation to complete
    echo "Waiting for Xcode installation (this may take 10+ minutes)..."
    while ! xcode-select -p &> /dev/null; do
        sleep 10
    done
    echo "✓ Xcode Command Line Tools installed"
else
    echo "✓ Xcode Command Line Tools already installed"
fi

# Check if Rust is installed
echo ""
echo "[2/5] Checking Rust toolchain..."
if ! command -v rustc &> /dev/null; then
    echo "⚠ Rust is not installed"
    echo "Installing Rust (this is required for compiling RSD parser)..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
    echo "✓ Rust installed"
else
    RUST_VERSION=$(rustc --version)
    echo "✓ Rust already installed: $RUST_VERSION"
fi

# Get latest Python version dynamically
echo ""
echo "[3/5] Detecting latest Python version..."

get_latest_python_version() {
    local version
    
    # Try python.org official releases
    version=$(curl -s "https://www.python.org/downloads/" 2>/dev/null | \
        grep -oP 'Python\s+\K\d+\.\d+\.\d+' | \
        head -1) && [ ! -z "$version" ] && echo "$version" && return 0
    
    # Fallback to known current version
    echo "3.14.2"
}

PYTHON_VERSION=$(get_latest_python_version)
echo "✓ Latest Python version: $PYTHON_VERSION"

# Check if Python is installed
echo ""
echo "[4/5] Checking Python installation..."
PYTHON_FOUND=false
if command -v python3 &> /dev/null; then
    CURRENT_PYTHON=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✓ Python already installed: $CURRENT_PYTHON"
    PYTHON_FOUND=true
fi

# Install Python via Homebrew if needed
if [ "$PYTHON_FOUND" = false ]; then
    echo "⚠ Python is not installed"
    echo "Installing Python $PYTHON_VERSION via Homebrew..."
    brew install python3
    
    CURRENT_PYTHON=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✓ Python $CURRENT_PYTHON installed"
fi

# Create virtual environment
echo ""
echo "[5/5] Setting up SonarSniffer environment..."

VENV_NAME="sonarsniffer_env"

if [ ! -d "$VENV_NAME" ]; then
    echo "Creating virtual environment: $VENV_NAME"
    python3 -m venv "$VENV_NAME"
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_NAME/bin/activate"
echo "✓ Virtual environment activated"

# Upgrade pip and build tools
echo "Upgrading pip and build tools..."
python -m pip install --upgrade pip setuptools wheel --quiet
echo "✓ Pip and build tools updated"

# Install build dependencies for Rust
echo "Installing Rust build support..."
pip install setuptools-rust --quiet
echo "✓ Rust build support installed"

# Install SonarSniffer
echo "Building and installing SonarSniffer..."
if pip install -e . --quiet; then
    echo "✓ SonarSniffer installed successfully!"
else
    echo "✗ SonarSniffer installation failed"
    echo "Check the error output above for details"
    exit 1
fi

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "To use SonarSniffer:"
echo ""
echo "  1. Activate the environment:"
echo "     source $VENV_NAME/bin/activate"
echo ""
echo "  2. Run SonarSniffer commands:"
echo "     sonarsniffer --help"
echo "     sonarsniffer analyze <file.rsd>"
echo "     sonarsniffer web <file.rsd>"
echo ""
echo "  3. Deactivate when done:"
echo "     deactivate"
echo ""
echo "For more information:"
echo "  - Documentation: See Garmin_RSD_Format_White_Paper.md"
echo "  - License info: sonarsniffer license --generate"
echo ""