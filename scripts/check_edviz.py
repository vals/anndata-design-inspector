#!/usr/bin/env python3
"""
Check for edviz package and auto-install from GitHub if missing.

This script ensures the edviz package is available for experimental design
visualization. If not found, it automatically installs from the GitHub repository.

Usage:
    python scripts/check_edviz.py

Exit codes:
    0: edviz is available (was already installed or just installed successfully)
    1: Failed to install edviz
"""

import subprocess
import sys


def check_package_installed(package_name):
    """Check if a Python package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def install_from_github(github_url):
    """Install package from GitHub using pip."""
    try:
        print(f"Installing edviz from GitHub: {github_url}", file=sys.stderr)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", github_url],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            print("✓ Successfully installed edviz", file=sys.stderr)
            return True
        else:
            print(f"✗ Failed to install edviz", file=sys.stderr)
            print(f"Error: {result.stderr}", file=sys.stderr)
            return False

    except Exception as e:
        print(f"✗ Error during installation: {e}", file=sys.stderr)
        return False


def main():
    """Main function to check and install edviz."""
    package_name = "edviz"
    github_url = "git+https://github.com/vals/edviz.git"

    # Check if already installed
    if check_package_installed(package_name):
        print(f"✓ {package_name} is already installed", file=sys.stderr)
        return 0

    # Not installed, attempt to install
    print(f"✗ {package_name} is not installed", file=sys.stderr)

    if install_from_github(github_url):
        # Verify installation succeeded
        if check_package_installed(package_name):
            return 0
        else:
            print(f"✗ Package installed but still cannot import {package_name}", file=sys.stderr)
            return 1
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
