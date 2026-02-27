#!/bin/bash
# Start PIGPIOD daemon

echo "Starting PIGPIOD daemon..."
# -s option requires a value (1, 2, 4, 5, 8, or 10 microseconds)
# Using default 5us sample rate
sudo pigpiod -s 5

if [ $? -eq 0 ]; then
    echo "✓ PIGPIOD started successfully"

    # Test connection
    sleep 1
    result=$(pigs hwver)
    if [ $? -eq 0 ]; then
        echo "✓ PIGPIOD is working"
        echo "  Hardware version: $result"
    else
        echo "✗ PIGPIOD test failed"
    fi
else
    echo "✗ Failed to start PIGPIOD"
fi
