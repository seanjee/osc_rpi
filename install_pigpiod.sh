#!/bin/bash
# pigpiod Installation Script for Raspberry Pi 5

set -e

echo "=========================================="
echo "Installing pigpiod for Raspberry Pi 5"
echo "=========================================="

# Step 1: Update package list
echo ""
echo "[Step 1/6] Updating package list..."
sudo apt update

# Step 2: Install pigpio
echo ""
echo "[Step 2/6] Installing pigpio package..."
sudo apt install -y pigpio

# Step 3: Start pigpiod service
echo ""
echo "[Step 3/6] Starting pigpiod service..."
sudo systemctl start pigpiod

# Step 4: Enable pigpiod on boot
echo ""
echo "[Step 4/6] Enabling pigpiod on boot..."
sudo systemctl enable pigpiod

# Step 5: Check service status
echo ""
echo "[Step 5/6] Checking service status..."
sudo systemctl status pigpiod --no-pager || true

# Step 6: Test pigpiod
echo ""
echo "[Step 6/6] Testing pigpiod..."
if command -v pigs &> /dev/null; then
    echo "Testing pigs command..."
    pigs hwver || echo "Warning: pigs test failed"
else
    echo "Warning: pigs command not found"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "To verify installation:"
echo "  sudo systemctl status pigpiod"
echo "  pigs hwver"
echo ""
echo "To run GPIO frequency test:"
echo "  cd /home/sean/osc_rpi"
echo "  sudo python3 gpio_frequency_test.py"
echo ""
