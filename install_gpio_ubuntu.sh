#!/bin/bash
# GPIO Installation Script for Ubuntu 24.04 (Noble) on Raspberry Pi 5

set -e

echo "=========================================="
echo "GPIO Library Installation for Ubuntu 24.04"
echo "=========================================="

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "Detected OS: $PRETTY_NAME"
fi

echo ""
echo "Ubuntu 24.04 does not have 'pigpio' package."
echo "Installing alternative GPIO libraries..."
echo ""

# Step 1: Install libgpiod (recommended for Ubuntu)
echo "[Step 1/5] Installing libgpiod (Linux GPIO library)..."
sudo apt update
sudo apt install -y python3-libgpiod libgpiod-dev gpiod

# Step 2: Install python3-gpiozero (if available)
echo ""
echo "[Step 2/5] Installing gpiozero..."
sudo apt install -y python3-gpiozero || echo "gpiozero not available, skipping..."

# Step 3: Check if RPi.GPIO is available
echo ""
echo "[Step 3/5] Checking for RPi.GPIO..."
if apt-cache show python3-rpi.gpio &> /dev/null; then
    sudo apt install -y python3-rpi.gpio
else
    echo "RPi.GPIO not available on Ubuntu (only for Raspberry Pi OS)"
fi

# Step 4: Install pigpio from source (optional but recommended for performance)
echo ""
echo "[Step 4/5] Installing pigpio from source..."
echo "This may take a few minutes..."

# Check if pigpio is already installed
if [ -f /usr/local/lib/libpigpio.so ] || [ -f /usr/lib/libpigpio.so ]; then
    echo "pigpio already installed, skipping compilation..."
else
    # Install build dependencies
    sudo apt install -y python3-dev python3-setuptools build-essential

    # Download and compile pigpio
    cd /tmp
    if [ ! -d "pigpio-79" ]; then
        wget -q https://github.com/joan2937/pigpio/archive/refs/tags/V79.tar.gz
        tar -xzf V79.tar.gz
    fi

    cd pigpio-79

    # Compile
    make -j$(nproc)
    sudo make install

    # Install Python bindings
    cd Python
    sudo python3 setup.py install

    # Start pigpiod
    cd /tmp
    sudo systemctl start pigpiod 2>/dev/null || true
    sudo systemctl enable pigpiod 2>/dev/null || true

    echo "✓ pigpio compiled and installed"
fi

# Step 5: Verify installations
echo ""
echo "[Step 5/5] Verifying installations..."

# Check libgpiod
if python3 -c "import gpiod; print('✓ libgpiod OK')" 2>/dev/null; then
    echo "  ✓ libgpiod available"
else
    echo "  ✗ libgpiod not available"
fi

# Check gpiozero
if python3 -c "import gpiozero; print('✓ gpiozero OK')" 2>/dev/null; then
    echo "  ✓ gpiozero available"
else
    echo "  ✗ gpiozero not available"
fi

# Check RPi.GPIO
if python3 -c "import RPi.GPIO as GPIO; print('✓ RPi.GPIO OK')" 2>/dev/null; then
    echo "  ✓ RPi.GPIO available"
else
    echo "  ✗ RPi.GPIO not available"
fi

# Check pigpio
if python3 -c "import pigpio; print('✓ pigpio OK')" 2>/dev/null; then
    echo "  ✓ pigpio available"
    if command -v pigs &> /dev/null; then
        echo "  ✓ pigpiod service running"
        pigs hwver 2>/dev/null || true
    fi
else
    echo "  ✗ pigpio not available (may need manual setup)"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "For Ubuntu 24.04 on Raspberry Pi 5:"
echo "  - libgpiod: Recommended, works well"
echo "  - pigpio: Compiled from source, should work"
echo ""
echo "To run GPIO frequency test:"
echo "  cd /home/sean/osc_rpi"
echo "  sudo python3 gpio_frequency_test.py"
echo ""
echo "If pigpio doesn't work, the script will"
echo "automatically fall back to libgpiod or RPi.GPIO"
echo ""
