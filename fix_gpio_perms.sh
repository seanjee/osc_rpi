#!/bin/bash
# Quick GPIO permission fix for Ubuntu 24.04

echo "=========================================="
echo "GPIO Permission Fix"
echo "=========================================="
echo ""
echo "Current GPIO device permissions:"
ls -la /dev/gpiochip0 2>/dev/null || echo "  /dev/gpiochip0 not found"

echo ""
echo "=========================================="
echo "Choose a solution:"
echo "=========================================="
echo "1. Quick fix (temporary): Change permissions for current session"
echo "2. Permanent fix: Add user to gpio group"
echo "3. Just run with sudo (easiest, no configuration needed)"
echo ""

read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Changing /dev/gpiochip0 permissions (requires sudo)..."
        sudo chmod 666 /dev/gpiochip0
        echo "✓ Permissions changed"
        echo "  Note: This change will be lost after reboot"
        echo ""
        echo "You can now run: python3 gpio_frequency_test.py"
        ;;
    2)
        echo ""
        echo "Adding user to gpio group (requires sudo)..."
        sudo usermod -a -G gpio $USER
        echo "✓ User added to gpio group"
        echo ""
        echo "To apply changes, run:"
        echo "  newgrp gpio"
        echo "  or log out and log back in"
        echo "  or reboot"
        echo ""
        echo "After applying, you can run: python3 gpio_frequency_test.py"
        ;;
    3)
        echo ""
        echo "To run the test with sudo:"
        echo ""
        echo "  cd /home/sean/osc_rpi"
        echo "  sudo python3 gpio_frequency_test.py"
        echo ""
        echo "This is the recommended method for Ubuntu."
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
