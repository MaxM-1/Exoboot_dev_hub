#!/bin/bash
# Installation script for Raspberry Pi 5 (Ubuntu 25) / Linux
# Run with: bash scripts/install_linux.sh

set -e  # Exit on any error

echo "=== Exoboot Perception Experiment - Linux Installation ==="
echo "Installing for Raspberry Pi 5 with Ubuntu 25..."
echo

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

echo "✓ Python version check passed: $python_version"

# Update system packages
echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    python3-tk \
    build-essential \
    libusb-1.0-0-dev \
    git \
    curl

# Install udev rules for device access (if needed)
echo "Setting up device permissions..."
sudo usermod -a -G dialout $USER

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install FlexSEA package
echo "Installing FlexSEA package..."
if [ -d "Actuator-Package-develop" ]; then
    pip install -e ./Actuator-Package-develop
else
    echo "Warning: FlexSEA package not found in Actuator-Package-develop/"
    echo "Please ensure the FlexSEA package is available and install it manually:"
    echo "  pip install -e ./Actuator-Package-develop"
fi

# Install project dependencies
echo "Installing project dependencies..."
pip install -r requirements.txt

# Install development dependencies (optional)
if [ "$1" == "dev" ]; then
    echo "Installing development dependencies..."
    pip install -r requirements-dev.txt
    
    # Install pre-commit hooks
    pre-commit install
fi

# Install the project in editable mode
echo "Installing exoboot-perception-experiment package..."
pip install -e .

# Create necessary directories
echo "Creating data directories..."
mkdir -p data results settings logs

# Set permissions for data directories
chmod 755 data results settings logs

echo
echo "=== Installation Complete! ==="
echo
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo
echo "To run the experiment:"
echo "  python -m exoboot_perception.gui"
echo "  # OR"
echo "  exoboot-experiment"
echo
echo "To deactivate the environment:"
echo "  deactivate"
echo
echo "Note: You may need to log out and back in for device permissions to take effect."