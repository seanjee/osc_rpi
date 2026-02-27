#!/bin/bash
# Start pigpio daemon for DMA access

echo "=========================================="
echo "Starting pigpiod Daemon"
echo "=========================================="
echo ""
echo "This enables DMA-based GPIO access"
echo "Required for high-speed sampling"
echo ""

# Check if running
if sudo systemctl is-active --quiet pigpiod; then
    echo "✓ pigpiod is already running"
    sudo systemctl status pigpiod --no-pager | head -10
else
    echo "Starting pigpiod..."
    sudo systemctl start pigpiod
    sudo systemctl enable pigpiod

    echo ""
    echo "✓ pigpiod started"
    echo "✓ Enabled for auto-start on boot"
    echo ""
    echo "Status:"
    sudo systemctl status pigpiod --no-pager
fi

echo ""
echo "=========================================="
echo "Testing pigpio connection"
echo "=========================================="

# Test with pigs command
if command -v pigs &> /dev/null; then
    echo ""
    echo "Testing 'pigs hwver'..."
    sudo pigs hwver
    echo "✓ pigpio daemon is working"
else
    echo "✗ 'pigs' command not found"
    echo "  But pigpiod should still work with Python"
fi

echo ""
echo "=========================================="
echo "Ready for DMA-based GPIO sampling"
echo "=========================================="
echo ""
echo "Now run: sudo python3 gpio_freq_dma.py"
