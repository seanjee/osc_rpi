#!/bin/bash
# Compile high-speed GPIO frequency measurement using libgpiod

echo "============================================================="
echo "Compiling freq_measure_c.c"
echo "============================================================="
echo ""

# Check if libgpiod-dev is installed
if ! dpkg -l | grep -q libgpiod-dev; then
    echo "Installing libgpiod-dev..."
    sudo apt update
    sudo apt install -y libgpiod-dev
    if [ $? -ne 0 ]; then
        echo "✗ Failed to install libgpiod-dev"
        exit 1
    fi
    echo "✓ libgpiod-dev installed"
fi

# Compile
echo "Compiling..."
gcc -o freq_measure_c freq_measure_c.c -lgpiod -Wall -O3

if [ $? -ne 0 ]; then
    echo "✗ Compilation failed"
    exit 1
fi

echo "✓ Compilation successful"
echo ""
echo "Run with:"
echo "  sudo ./freq_measure_c"
echo ""
