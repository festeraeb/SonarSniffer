#!/bin/bash
################################################################################
# SonarSniffer Linux Installer
# Installs Python environment, dependencies, and SonarSniffer
################################################################################

set -e

echo ""
echo "================================================================================"
echo "SonarSniffer Linux Installer"
echo "================================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    DISTRO="unknown"
fi

echo "Detected Linux distribution: $DISTRO"
echo ""

# Check Python installation
echo "Checking for Python 3.10+..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is required but not found${NC}"
    echo ""
    echo "Install Python with:"
    case $DISTRO in
        ubuntu|debian)
            echo "  sudo apt-get update"
            echo "  sudo apt-get install python3.10 python3.10-venv python3-pip"
            ;;
        fedora|rhel|centos)
            echo "  sudo dnf install python3.10"
            ;;
        arch)
            echo "  sudo pacman -S python"
            ;;
        opensuse*)
            echo "  sudo zypper install python3"
            ;;
        *)
            echo "  Please install Python 3.10 or later"
            ;;
    esac
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Found Python $PYTHON_VERSION"

# Check pip
echo ""
echo "Checking for pip..."
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}Installing pip...${NC}"
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get install -y python3-pip
            ;;
        fedora|rhel|centos)
            sudo dnf install -y python3-pip
            ;;
        arch)
            sudo pacman -S -u python-pip
            ;;
        opensuse*)
            sudo zypper install -y python3-pip
            ;;
    esac
fi
echo -e "${GREEN}✓${NC} pip is available"

# Install system dependencies
echo ""
echo "Installing system dependencies..."

case $DISTRO in
    ubuntu|debian)
        echo "Running: sudo apt-get update && sudo apt-get install -y ..."
        sudo apt-get update
        sudo apt-get install -y \
            build-essential \
            python3-dev \
            libgl1-mesa-glx \
            libsm6 \
            libxext6 \
            libxrender-dev \
            libgomp1 \
            ffmpeg
        ;;
    fedora|rhel|centos)
        echo "Running: sudo dnf install -y ..."
        sudo dnf install -y \
            gcc \
            gcc-c++ \
            python3-devel \
            mesa-libGL \
            libSM \
            libX11 \
            libXext \
            libXrender \
            libgomp \
            ffmpeg
        ;;
    arch)
        echo "Running: sudo pacman -S ..."
        sudo pacman -S --noconfirm \
            base-devel \
            mesa \
            libsm \
            libxext \
            libxrender \
            ffmpeg
        ;;
    opensuse*)
        echo "Running: sudo zypper install ..."
        sudo zypper install -y \
            gcc \
            gcc-c++ \
            python3-devel \
            Mesa \
            libSM6 \
            libXext6 \
            libXrender1 \
            libgomp1 \
            ffmpeg
        ;;
    *)
        echo -e "${YELLOW}WARNING: Unknown Linux distribution. You may need to install dependencies manually.${NC}"
        echo "Required packages: gcc, python3-dev, libgl1-mesa-glx, libsm6, libxext6, ffmpeg"
        ;;
esac

echo -e "${GREEN}✓${NC} System dependencies installed"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
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

# Create trial license
echo ""
echo "Setting up trial license..."
python3 license_manager.py create-trial
echo -e "${GREEN}✓${NC} Trial license created (30 days)"

# Create desktop entry
echo ""
read -p "Create desktop menu entry? [Y/n]: " -r CREATE_DESKTOP
CREATE_DESKTOP=${CREATE_DESKTOP:-Y}

if [[ $CREATE_DESKTOP =~ ^[Yy]$ ]]; then
    DESKTOP_DIR="$HOME/.local/share/applications"
    mkdir -p "$DESKTOP_DIR"
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    cat > "$DESKTOP_DIR/sonarsniffer.desktop" << EOF
[Desktop Entry]
Type=Application
Name=SonarSniffer
Comment=Sonar data processing and visualization
Exec=$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/sonar_gui.py
Path=$SCRIPT_DIR
Icon=application-x-python
Terminal=false
Categories=Science;Utility;
EOF
    
    echo -e "${GREEN}✓${NC} Desktop entry created"
fi

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
echo "Next steps:"
echo "  1. Review the LICENSE file for terms and conditions"
echo "  2. Register your license key (if you have one)"
echo "  3. Start SonarSniffer and begin processing RSD files"
echo ""
echo "Troubleshooting:"
echo "  - If packages fail to install, try: pip3 install --upgrade pip"
echo "  - Ensure you have internet connection for dependency downloads"
echo "  - Check Python version: python3 --version (should be 3.10+)"
echo ""
echo "For support, visit: https://github.com/festeraeb/SonarSniffer"
echo ""

# Create run script
cat > run_sonarsniffer.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python3 sonar_gui.py
EOF

chmod +x run_sonarsniffer.sh
echo "Created run_sonarsniffer.sh"

echo ""
echo "Installation finished!"
echo ""
