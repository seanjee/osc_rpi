#!/bin/bash
# Compile high-speed GPIO frequency measurement using libgpiod C++ API

echo "============================================================="
echo "Compiling freq_measure_cpp.cpp"
echo "============================================================="
echo ""

# Check if libgpiodcxx is installed
if [ ! -f "/usr/lib/aarch64-linux-gnu/libgpiodcxx.so" ]; then
    echo "⚠ libgpiodcxx not found in standard location"
    echo "  Searching for alternative locations..."
    find /usr -name "*libgpiodcxx*" 2>/dev/null || true
fi

# Compile with C++
echo "Compiling with g++..."
g++ -o freq_measure_cpp freq_measure_cpp.cpp -lgpiodcxx -lgpiod -Wall -O3 -std=c++11

if [ $? -ne 0 ]; then
    echo "✗ Compilation failed"
    echo ""
    echo "Trying alternative linking method..."
    g++ -o freq_measure_cpp freq_measure_cpp.cpp -Wall -O3 -std=c++11 \
        -I/usr/include \
        /usr/lib/aarch64-linux-gnu/libgpiodcxx.so \
        /usr/lib/aarch64-linux-gnu/libgpiod.so
    if [ $? -ne 0 ]; then
        echo "✗ Alternative compilation also failed"
        exit 1
    fi
fi

echo "✓ Compilation successful"
echo ""
echo "Run with:"
echo "  sudo ./freq_measure_cpp"
echo ""
