#!/bin/bash

# RK3568 Remote Rover System - Installation Script
# This script installs all dependencies and configures the system

set -e

echo "=========================================="
echo "RK3568 Remote Rover System - Installation"
echo "=========================================="

# Check if running on RK3568
echo "[*] Checking system..."
if ! grep -q "RK3568\|rk3568" /proc/cpuinfo 2>/dev/null; then
    echo "[!] Warning: This system may not be RK3568"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "[*] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "[*] Installing system dependencies..."
sudo apt-get install -y \
    python3.11 \
    python3-pip \
    python3-dev \
    git \
    build-essential \
    libopencv-dev \
    python3-opencv \
    portaudio19-dev \
    libportaudio2 \
    libffi-dev \
    libssl-dev \
    alsa-utils \
    pulseaudio \
    ffmpeg \
    v4l-utils

# Install Python dependencies
echo "[*] Installing Python dependencies..."
cd "$(dirname "$0")/.."
pip3 install --upgrade pip setuptools wheel
pip3 install -r requirements.txt

# Configure RKMPP (if available)
echo "[*] Checking RKMPP support..."
if [ -e /dev/mpp_service ] && [ -e /dev/rga ]; then
    echo "[+] RKMPP support detected"
    
    # Configure device permissions
    echo "[*] Configuring RKMPP device permissions..."
    sudo tee /etc/udev/rules.d/99-rk-device-permissions.rules > /dev/null <<EOF
KERNEL=="mpp_service", MODE="0660", GROUP="video"
KERNEL=="rga", MODE="0660", GROUP="video"
KERNEL=="system", MODE="0666", GROUP="video"
KERNEL=="system-dma32", MODE="0666", GROUP="video"
KERNEL=="system-uncached", MODE="0666", GROUP="video"
KERNEL=="system-uncached-dma32", MODE="0666", GROUP="video"
RUN+="/usr/bin/chmod a+rw /dev/dma_heap"
EOF
    
    # Reload udev rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger
else
    echo "[!] RKMPP not detected - hardware acceleration will not be available"
fi

# Configure audio
echo "[*] Configuring audio system..."
sudo usermod -aG audio $USER
sudo systemctl restart pulseaudio || true

# Create log directory
echo "[*] Creating log directory..."
sudo mkdir -p /var/log/rover
sudo chown $USER:$USER /var/log/rover

# Create systemd service (optional)
echo "[*] Creating systemd service..."
sudo tee /etc/systemd/system/rover.service > /dev/null <<EOF
[Unit]
Description=RK3568 Remote Rover System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)/src
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Test camera access
echo "[*] Testing camera access..."
if [ -e /dev/video0 ]; then
    echo "[+] Camera device /dev/video0 found"
else
    echo "[!] Camera device /dev/video0 not found"
fi

if [ -e /dev/video1 ]; then
    echo "[+] Camera device /dev/video1 found"
else
    echo "[!] Camera device /dev/video1 not found"
fi

# Test serial port
echo "[*] Checking serial ports..."
if [ -e /dev/ttyUSB0 ]; then
    echo "[+] Serial port /dev/ttyUSB0 found"
else
    echo "[!] Serial port /dev/ttyUSB0 not found (motor driver may not be connected)"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit config/config.yaml with your settings"
echo "2. Connect cameras and motor driver"
echo "3. Run: python3 src/main.py"
echo ""
echo "Or use systemd service:"
echo "  sudo systemctl start rover"
echo "  sudo systemctl enable rover"
echo ""
