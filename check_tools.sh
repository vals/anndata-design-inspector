#!/usr/bin/env bash
# Check if HDF5 tools are installed, offer to install if not
# Usage: ./check_tools.sh [--install]

set -euo pipefail

check_tool() {
    if command -v "$1" &> /dev/null; then
        echo "✓ $1 is installed"
        "$1" --version 2>&1 | head -1
        return 0
    else
        echo "✗ $1 is NOT installed"
        return 1
    fi
}

install_tools() {
    echo "Installing HDF5 tools..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Detected macOS, using Homebrew..."
        brew install hdf5
    elif [[ -f /etc/debian_version ]]; then
        echo "Detected Debian/Ubuntu, using apt..."
        sudo apt-get update && sudo apt-get install -y hdf5-tools
    elif [[ -f /etc/redhat-release ]]; then
        echo "Detected RedHat/CentOS/Fedora, using yum..."
        sudo yum install -y hdf5
    else
        echo "Unknown OS. Please install hdf5 tools manually." >&2
        exit 1
    fi
}

# Check both tools
h5ls_ok=0
h5dump_ok=0

echo "Checking HDF5 tools..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_tool h5ls && h5ls_ok=1 || true
check_tool h5dump && h5dump_ok=1 || true

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# If both are installed, we're done
if [ $h5ls_ok -eq 1 ] && [ $h5dump_ok -eq 1 ]; then
    echo "✓ All required tools are installed!"
    exit 0
fi

# If --install flag is provided, install
if [ $# -eq 1 ] && [ "$1" = "--install" ]; then
    install_tools
    echo ""
    echo "Verifying installation..."
    check_tool h5ls
    check_tool h5dump
else
    echo ""
    echo "Run with --install flag to install missing tools:"
    echo "  $0 --install"
    exit 1
fi
