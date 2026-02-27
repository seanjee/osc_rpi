#!/bin/bash
# Compile latency test

echo "Compiling latency_test.cpp..."

# Try common library paths
LIB_PATHS=(
    "/usr/lib"
    "/usr/local/lib"
    "/usr/lib/aarch64-linux-gnu"
    "/usr/lib/arm-linux-gnueabihf"
)

CXX=g++
CXXFLAGS="-std=c++17 -O2 -pthread"
LDFLAGS="-lgpiodcxx -lgpiod -pthread"

# Find libgpiod
GPIOD_LIB=""
for path in "${LIB_PATHS[@]}"; do
    if [ -f "$path/libgpiod.so" ] || [ -f "$path/libgpiod.so.1" ]; then
        GPIOD_LIB="-L$path"
        echo "Found libgpiod in $path"
        break
    fi
done

if [ -z "$GPIOD_LIB" ]; then
    echo "Error: libgpiod not found"
    echo "Install with: sudo apt install libgpiod-dev"
    exit 1
fi

# Compile
$CXX $CXXFLAGS latency_test.cpp -o latency_test $GPIOD_LIB $LDFLAGS

if [ $? -eq 0 ]; then
    echo "✓ Compilation successful: latency_test"
    echo "Run with: sudo ./latency_test"
else
    echo "✗ Compilation failed"
    exit 1
fi
