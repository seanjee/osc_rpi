#!/bin/bash
# Compile multi-channel frequency test

echo "Compiling multi_channel_freq_test.cpp..."

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
$CXX $CXXFLAGS multi_channel_freq_test.cpp -o multi_channel_freq_test $GPIOD_LIB $LDFLAGS

if [ $? -eq 0 ]; then
    echo "✓ Compilation successful: multi_channel_freq_test"
    echo "Run with: sudo ./multi_channel_freq_test"
else
    echo "✗ Compilation failed"
    exit 1
fi
