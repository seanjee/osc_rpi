#!/bin/bash
# Run the C++ frequency measurement program

echo "============================================================="
echo "Running libgpiod C++ High-Speed Sampling Test"
echo "============================================================="
echo ""
echo "This test measures 10 kHz square wave frequency"
echo "Using edge event detection for high accuracy"
echo ""
echo "Note: Requires root/sudo privileges for GPIO access"
echo ""

# Run the measurement
sudo ./freq_measure_cpp

# Capture exit code
exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "============================================================="
    echo "✓ Test completed successfully"
    echo "============================================================="
else
    echo "============================================================="
    echo "✗ Test failed with exit code: $exit_code"
    echo "============================================================="
fi

exit $exit_code
