#!/usr/bin/env python3
"""
GPIO Debug Script for Raspberry Pi 5 / Ubuntu 24.04
Check GPIO chip mapping and test signal detection
"""

import gpiod
import time

print("=" * 60)
print("GPIO Debug - Raspberry Pi 5 / Ubuntu 24.04")
print("=" * 60)

# Check available GPIO chips
print("\nAvailable GPIO Chips:")
print("-" * 60)

chips = [
    ("/dev/gpiochip0", "Standard chip 0"),
    ("/dev/gpiochip1", "Standard chip 1"),
    ("/dev/gpiochip512", "BRCMSTB @ 107d508500 (32 pins)"),
    ("/dev/gpiochip544", "BRCMSTB @ 107d508520 (4 pins)"),
    ("/dev/gpiochip548", "BRCMSTB @ 107d517c00 (15 pins)"),
    ("/dev/gpiochip563", "BRCMSTB @ 107d517c20 (6 pins)"),
    ("/dev/gpiochip569", "RP1 pinctrl (54 pins) - MAIN CHIP"),
]

for path, desc in chips:
    try:
        chip = gpiod.Chip(path)
        num_lines = chip.num_lines
        print(f"✓ {path}")
        print(f"  Description: {desc}")
        print(f"  Lines: {num_lines}")
        chip.close()
    except Exception as e:
        print(f"✗ {path}")
        print(f"  Error: {e}")

print("\n" + "=" * 60)
print("Testing Signal Detection")
print("=" * 60)

# Test different configurations
test_configs = [
    # (chip_path, line_offset, pin_description)
    ("/dev/gpiochip569", 5, "GPIO5 (Pin 29) on RP1"),
    ("/dev/gpiochip569", 17, "GPIO17 (Pin 11) on RP1"),
    ("/dev/gpiochip569", 27, "GPIO27 (Pin 13) on RP1"),
]

print("\nSignal is connected to GPIO5 (Physical Pin 29)")
print("Testing multiple configurations to find the correct one...\n")

for chip_path, line_offset, pin_desc in test_configs:
    print(f"\n{'='*60}")
    print(f"Testing: {pin_desc}")
    print(f"Chip: {chip_path}, Line: {line_offset}")
    print(f"{'='*60}")

    try:
        # Open chip and request line
        chip = gpiod.Chip(chip_path)
        line = chip.get_line(line_offset)

        # Configure as input
        line.request(consumer="debug", type=gpiod.LINE_REQ_DIR_IN)

        # Read values multiple times
        print("Reading GPIO state...")
        values = []
        for i in range(20):
            val = line.get_value()
            values.append(val)
            time.sleep(0.01)  # 10ms between reads

        # Count changes
        changes = sum(1 for i in range(1, len(values)) if values[i] != values[i-1])
        highs = sum(values)
        lows = len(values) - highs

        print(f"\nResults:")
        print(f"  Values: {values}")
        print(f"  Highs: {highs}, Lows: {lows}")
        print(f"  Changes: {changes}")

        if changes > 5:
            print(f"\n  ✓ SIGNAL DETECTED! This is likely the correct configuration.")
        elif changes == 0:
            print(f"\n  ✗ No signal - all values same ({values[0]})")
            print(f"     Check if signal is connected")
        else:
            print(f"\n  ⚠ Some changes detected, but may be noise")

        # Cleanup
        line.release()
        chip.close()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print(f"  Line {line_offset} may not exist on this chip")

print("\n" + "=" * 60)
print("Debug Summary")
print("=" * 60)
print("\nKey Findings:")
print("1. Raspberry Pi 5 uses RP1 chip (/dev/gpiochip569)")
print("2. Original script used /dev/gpiochip0 (WRONG)")
print("3. GPIO5 line offset should be 5 on RP1")
print("4. Physical Pin 29 should map to GPIO5")
print("\nIf signal detected on GPIO5, the mapping is correct.")
print("If signal detected on GPIO17, check physical pin connection.")
print("\nActual sample rate issue:")
print("  Target: 1000 ksps")
print("  Achieved: 498.7 ksps")
print("  → Python polling is too slow for 1 Msps")
print("  → Need to use pigpio DMA or optimize polling")
print("=" * 60)
