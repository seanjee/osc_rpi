#!/usr/bin/env python3
"""
Test PIGPIO connection modes
Check if we can connect without pigpiod daemon
"""

import pigpio
import sys

print("=" * 60)
print("PIGPIO Connection Mode Test")
print("=" * 60)

# Try to connect to pigpio daemon
print("\nAttempting to connect to pigpio daemon...")
print("This requires pigpiod to be running")

try:
    pi = pigpio.pi()

    if not pi.connected:
        print("\n✗ Cannot connect to pigpio daemon")
        print("\nPossible reasons:")
        print("  1. pigpiod is not running")
        print("  2. pigpiod is not installed on Ubuntu")
        print("  3. Using wrong host/port")

        print("\nChecking pigpiod installation...")
        import subprocess
        result = subprocess.run(['systemctl', 'list-units', 'pigpiod*'],
                            capture_output=True, text=True)
        print(f"  Systemd units: {result.stdout.strip()}")

        result = subprocess.run(['which', 'pigpiod'],
                            capture_output=True, text=True)
        print(f"  pigpiod binary: {result.stdout.strip() or 'NOT FOUND'}")

        print("\n" + "=" * 60)
        print("SOLUTION: Install full pigpio from source")
        print("=" * 60)
        print("\nUbuntu 24.04 pigpio package does NOT include pigpiod")
        print("You need to install from source:")
        print("\n  cd /tmp")
        print("  wget https://github.com/joan2937/pigpio/archive/refs/tags/V79.tar.gz")
        print("  tar -xzf V79.tar.gz")
        print("  cd pigpio-79")
        print("  make")
        print("  sudo make install")
        print("\nThen start:")
        print("  sudo pigpiod")
        print("  # or")
        print("  sudo systemctl start pigpiod")

    else:
        print("\n✓ Successfully connected to pigpio daemon")
        print(f"  Hardware version: {pi.hardware_ver()}")
        print(f"  Pigpio version: {pi.get_pigpio_version()}")

        # Test GPIO read
        GPIO_PIN = 5
        pi.set_mode(GPIO_PIN, pigpio.INPUT)

        # Read 10 times
        print(f"\nReading GPIO {GPIO_PIN}...")
        values = [pi.read(GPIO_PIN) for _ in range(10)]
        print(f"  Values: {values}")
        print(f"  Highs: {sum(values)}, Lows: {10 - sum(values)}")

        pi.stop()
        print("\n✓ PIGPIO daemon working correctly!")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
