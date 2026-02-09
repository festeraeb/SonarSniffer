#!/usr/bin/env bash
# SonarSniffer Cross-Platform Build Script
# Automates building for Windows, macOS, and Linux
# Usage: ./build.sh [target] [--release] [--help]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VERSION="0.1.0"
BUILD_DIR="build"
RELEASE_MODE="--release"

# Functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

show_help() {
    cat << EOF
SonarSniffer Build Script v${VERSION}

Usage: ./build.sh [target] [options]

Targets:
  all       Build all platforms (default)
  windows   Build Windows (.msi installer)
  macos     Build macOS (.dmg bundle)
  linux     Build Linux (AppImage)
  dev       Development build (Tauri dev mode)

Options:
  --release Build optimized release (default)
  --debug   Build debug version
  --clean   Clean build artifacts first
  --help    Show this help message

Examples:
  ./build.sh all                    # Build all platforms (release)
  ./build.sh windows --release      # Build Windows installer
  ./build.sh dev                    # Start development environment
  ./build.sh all --clean            # Clean and rebuild all

Environment:
  Set SKIP_DOWNLOAD=1 to skip downloading prebuilt binaries

EOF
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js not installed. Please install Node.js 18+ from https://nodejs.org"
        exit 1
    fi
    print_success "Node.js $(node --version)"
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm not installed"
        exit 1
    fi
    print_success "npm $(npm --version)"
    
    # Check Rust
    if ! command -v rustc &> /dev/null; then
        print_error "Rust not installed. Please install Rust from https://rustup.rs"
        exit 1
    fi
    print_success "rustc $(rustc --version)"
    
    # Check Cargo
    if ! command -v cargo &> /dev/null; then
        print_error "Cargo not installed"
        exit 1
    fi
    print_success "cargo version: $(cargo --version)"
    
    # Platform-specific checks
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_info "Linux detected - checking system dependencies..."
        if ! pkg-config --exists gtk+-3.0 2>/dev/null; then
            print_warning "GTK3 development files not found"
            print_info "Install with: sudo apt-get install libgtk-3-dev"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "macOS detected"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        print_info "Windows detected"
    fi
}

install_dependencies() {
    print_header "Installing Dependencies"
    
    if [ -d "node_modules" ]; then
        print_info "node_modules exists, skipping npm install"
    else
        print_info "Installing Node.js dependencies..."
        npm install
        print_success "Node.js dependencies installed"
    fi
    
    print_info "Installing Rust dependencies..."
    cd src-tauri
    cargo fetch
    cd ..
    print_success "Rust dependencies fetched"
}

build_frontend() {
    print_header "Building Frontend (React + TypeScript)"
    
    npm run build:ui
    print_success "Frontend built: dist/"
}

build_windows() {
    print_header "Building Windows (.msi Installer)"
    
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "cygwin" && "$OSTYPE" != "win32" ]]; then
        print_warning "Not on Windows - cross-compilation not fully supported"
        print_info "Consider building on Windows for best results"
    fi
    
    npm run build:windows
    
    # Try to create MSI (may fail if NSIS not installed)
    if npm run build:msi 2>/dev/null; then
        print_success "Windows MSI installer created"
    else
        print_warning "MSI creation skipped (NSIS may not be installed)"
        print_info "You can manually run: npm run build:msi"
    fi
    
    if [ -f "src-tauri/target/x86_64-pc-windows-msvc/release/SonarSniffer.exe" ]; then
        print_success "Windows executable: src-tauri/target/x86_64-pc-windows-msvc/release/SonarSniffer.exe"
    fi
}

build_macos() {
    print_header "Building macOS (.dmg Bundle)"
    
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_warning "Not on macOS - cannot build for macOS"
        print_info "macOS builds must be performed on macOS"
        return
    fi
    
    # Build for Intel
    print_info "Building for Intel (x86_64)..."
    cargo build --release --target x86_64-apple-darwin
    
    # Build for Apple Silicon
    if command -v arch &> /dev/null && arch -arm64 echo >/dev/null 2>&1; then
        print_info "Building for Apple Silicon (aarch64)..."
        cargo build --release --target aarch64-apple-darwin
    fi
    
    npm run tauri -- build
    
    if [ -d "src-tauri/target/release/bundle/dmg" ]; then
        print_success "macOS DMG bundles created in src-tauri/target/release/bundle/dmg"
    fi
}

build_linux() {
    print_header "Building Linux (AppImage)"
    
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        print_warning "Not on Linux - cannot build AppImage natively"
        print_info "Linux builds must be performed on Linux"
        return
    fi
    
    npm run tauri -- build --target x86_64-unknown-linux-gnu
    
    if [ -d "src-tauri/target/release/bundle/appimage" ]; then
        print_success "Linux AppImage created in src-tauri/target/release/bundle/appimage"
    fi
}

build_dev() {
    print_header "Starting Development Environment"
    
    print_info "Starting Tauri dev server..."
    print_info "Frontend: http://localhost:5173"
    print_info "App window will open automatically"
    print_info ""
    
    npm run dev
}

build_all() {
    print_header "Building All Platforms"
    
    # Frontend is common to all
    build_frontend
    
    # Build all platforms (some may be skipped on non-matching OS)
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        build_windows
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        build_macos
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        build_linux
    fi
    
    # Note: For true cross-platform CI builds, use GitHub Actions (see .github/workflows/)
    print_warning "Cross-platform builds are best done in CI/CD pipeline"
    print_info "See .github/workflows/build-release.yml for full multi-platform builds"
}

clean_build() {
    print_header "Cleaning Build Artifacts"
    
    print_info "Removing dist/"
    rm -rf dist
    
    print_info "Cleaning Cargo build..."
    cd src-tauri
    cargo clean --release
    cd ..
    
    print_info "Removing build directory..."
    rm -rf build
    
    print_success "Build artifacts cleaned"
}

# Main script
main() {
    local target="${1:-all}"
    local clean_first=0
    
    # Parse options
    for arg in "$@"; do
        case $arg in
            --clean)
                clean_first=1
                ;;
            --debug)
                RELEASE_MODE=""
                ;;
            --help)
                show_help
                exit 0
                ;;
        esac
    done
    
    # Clean if requested
    if [ $clean_first -eq 1 ]; then
        clean_build
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Install dependencies
    install_dependencies
    
    # Build based on target
    case $target in
        all)
            build_all
            ;;
        windows)
            build_frontend
            build_windows
            ;;
        macos)
            build_frontend
            build_macos
            ;;
        linux)
            build_frontend
            build_linux
            ;;
        dev)
            build_dev
            ;;
        clean)
            clean_build
            ;;
        *)
            print_error "Unknown target: $target"
            show_help
            exit 1
            ;;
    esac
    
    print_header "Build Complete"
    print_success "Build successful!"
    print_info "Artifacts ready for distribution"
}

# Run main
main "$@"
