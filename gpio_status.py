#!/usr/bin/env python3
"""
Simple GPIO Status and Test Script
"""

import sys

print("=" * 60)
print("Raspberry Pi 5 GPIO Status Check")
print("=" * 60)

# Check 1: Hardware info
print("\n[1] Hardware Info:")
try:
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if 'Model' in line or 'Revision' in line:
                print(f"  {line.strip()}")
except:
    print("  Cannot read CPU info")

# Check 2: CPU Frequency
print("\n[2] CPU Frequency:")
try:
    with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 'r') as f:
        freq = int(f.read().strip())
        print(f"  Current: {freq/1000:.2f} GHz")
except:
    print("  Cannot read CPU frequency")

# Check 3: GPIO chips
print("\n[3] Available GPIO Chips:")
import os
for chip in sorted(os.listdir('/sys/class/gpio/')):
    if chip.startswith('gpiochip'):
        try:
            ngpio_path = f'/sys/class/gpio/{chip}/ngpio'
            label_path = f'/sys/class/gpio/{chip}/label'
            with open(ngpio_path, 'r') as f:
                ngpio = f.read().strip()
            with open(label_path, 'r') as f:
                label = f.read().strip()
            print(f"  {chip}: {ngpio} pins ({label})")
        except:
            pass

# Check 4: Test RPi.GPIO library
print("\n[4] RPi.GPIO Library:")
try:
    import RPi.GPIO as GPIO
    print(f"  ✓ RPi.GPIO installed: {GPIO.VERSION}")
except ImportError:
    print("  ✗ RPi.GPIO not installed")
    print("    Install: sudo apt install python3-rpi.gpio")

# Check 5: Test gpiozero library
print("\n[5] gpiozero Library:")
try:
    import gpiozero
    print(f"  ✓ gpiozero installed")
except ImportError:
    print("  ✗ gpiozero not installed")
    print("    Install: sudo apt install python3-gpiozero")

print("\n" + "=" * 60)
print("SAMPLING FREQUENCY LIMITS:")
print("=" * 60)
print("""
Pure Python Methods:
  - sysfs file operations:      ~1-5 kHz    (not recommended)
  - RPi.GPIO polling:          ~50-150 kHz
  - RPi.GPIO edge detection:   ~100-300 kHz

Advanced Methods:
  - Pigpio (Python):           ~200-500 kHz
  - Pigpio DMA (Python):       ~1-2 MHz
  - C/C++ direct memory:       ~1-5 MHz
  - Kernel space (custom):     10-50+ MHz

Hardware Limit (Raspberry Pi 5):
  - GPIO switching speed:      ~100 MHz (theoretical)
  - Practical limit (Python): ~300 kHz
  - Practical limit (C/DMA):   ~5-10 MHz

Recommended for Oscilloscope:
  - Low speed (<100 kHz):      Use RPi.GPIO
  - Medium speed (100-500 kHz): Use Pigpio
  - High speed (>500 kHz):     Use C/C++ with DMA

Example commands to install:
  sudo apt update
  sudo apt install python3-rpi.gpio python3-gpiozero pigpio
""")

print("=" * 60)
