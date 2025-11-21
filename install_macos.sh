#!/bin/bash
################################################################################
# SonarSniffer macOS Installer
# Installs Python environment, dependencies, and SonarSniffer
################################################################################

set -e

echo ""
echo "================================================================================"
echo "SonarSniffer macOS Installer"
echo "================================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}ERROR: This installer is for macOS only${NC}"
    exit 1
fi

# Check for Homebrew
echo "Checking for Homebrew..."
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
echo -e "${GREEN}✓${NC} Homebrew is available"

# Install system dependencies via Homebrew
echo ""
echo "Installing system dependencies via Homebrew..."
echo "This includes: Python 3, FFmpeg, and required libraries"

brew install python@3.11 ffmpeg

echo -e "${GREEN}✓${NC} System dependencies installed"

# Set Python to the Homebrew version
echo ""
echo "Configuring Python..."
PYTHON_BIN="/usr/local/bin/python3"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(which python3)
fi

PYTHON_VERSION=$($PYTHON_BIN --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Using Python $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON_BIN -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
python3 -m pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo -e "${GREEN}✓${NC} pip upgraded"

# Install Python requirements
echo ""
echo "Installing Python dependencies (this may take a few minutes)..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${RED}ERROR: requirements.txt not found${NC}"
    echo "Make sure you're in the SonarSniffer directory"
    exit 1
fi

# Install additional macOS-specific packages
echo ""
echo "Installing macOS-specific packages..."
pip3 install py2app > /dev/null 2>&1
echo -e "${GREEN}✓${NC} macOS packages installed"

# Create trial license
echo ""
echo "Setting up trial license..."
python3 license_manager.py create-trial
echo -e "${GREEN}✓${NC} Trial license created (30 days)"

# Create an App bundle (optional)
echo ""
read -p "Create macOS application bundle? [Y/n]: " -r CREATE_APP
CREATE_APP=${CREATE_APP:-Y}

if [[ $CREATE_APP =~ ^[Yy]$ ]]; then
    echo "Creating application bundle..."
    
    # Create setup.py for py2app
    cat > setup.py << 'EOF'
from setuptools import setup

APP = ['sonar_gui.py']
OPTIONS = {
    'argv_emulation': True,
    'packages': ['numpy', 'cv2', 'tkinter'],
    'iconfile': None,
    'plist': {
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
    },
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
EOF
    
    python3 setup.py py2app 2>/dev/null || echo -e "${YELLOW}Warning: Could not create full app bundle, but installation is complete${NC}"
    
    if [ -d "dist/SonarSniffer.app" ]; then
        echo -e "${GREEN}✓${NC} Application bundle created: dist/SonarSniffer.app"
    fi
fi

# Create launch script
echo ""
cat > run_sonarsniffer.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python3 sonar_gui.py
EOF

chmod +x run_sonarsniffer.sh
echo -e "${GREEN}✓${NC} Created run_sonarsniffer.sh"

# Test installation
echo ""
echo "Testing installation..."
python3 << EOF
try:
    import numpy
    import cv2
    import tkinter
    print('✓ All core packages loaded successfully')
except ImportError as e:
    print(f'✗ Package import failed: {e}')
    exit(1)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Installation test failed${NC}"
    exit 1
fi

# Success message
echo ""
echo "================================================================================"
echo -e "${GREEN}✓ SonarSniffer Installation Complete!${NC}"
echo "================================================================================"
echo ""
echo "You can now run SonarSniffer with:"
echo "  source venv/bin/activate"
echo "  python3 sonar_gui.py"
echo ""
echo "Or use the run script:"
echo "  ./run_sonarsniffer.sh"
echo ""
if [ -d "dist/SonarSniffer.app" ]; then
    echo "Or launch the app bundle:"
    echo "  open dist/SonarSniffer.app"
    echo ""
fi
echo "Next steps:"
echo "  1. Review the LICENSE file for terms and conditions"
echo "  2. Register your license key (if you have one)"
echo "  3. Start SonarSniffer and begin processing RSD files"
echo ""
echo "Troubleshooting:"
echo "  - If packages fail to install, try: pip3 install --upgrade pip"
echo "  - Ensure you have internet connection for dependency downloads"
echo "  - Check Python version: python3 --version (should be 3.11+)"
echo "  - For M1/M2 Macs, some packages may need: arch -arm64 brew install ..."
echo ""
echo "For support, visit: https://github.com/festeraeb/SonarSniffer"
echo ""
echo "Installation finished!"
echo ""
