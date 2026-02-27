#!/usr/bin/env python3
"""
GPIO Chip Mapping Test (Fixed)
Test all /dev/gpiochip* devices to find the correct one for GPIO5
"""

import gpiod
import time

print("=" * 60)
print("GPIO Chip Mapping Test")
print("=" * 60)
print("\nProblem: /dev/gpiochip512-569 don't exist")
print("Solution: Test /dev/gpiochip0-4 to find correct mapping")
print("=" * 60)

# Test all available gpiochip devices
available_chips = ["/dev/gpiochip0", "/dev/gpiochip1", "/dev/gpiochip2", "/dev/gpiochip3", "/dev/gpiochip4"]

print("\nScanning /dev/gpiochip devices...\n")

results = []

for chip_path in available_chips:
    try:
        chip = gpiod.Chip(chip_path)
        num_lines = chip.num_lines()  # Fixed: call the method

        print(f"\n{'='*60}")
        print(f"Testing: {chip_path}")
        print(f"{'='*60}")
        print(f"Number of lines: {num_lines}")

        # Test line 5 (GPIO5) on this chip
        if num_lines > 5:
            try:
                line = chip.get_line(5)
                line.request(consumer="test", type=gpiod.LINE_REQ_DIR_IN)

                # Read values multiple times
                values = []
                for i in range(10):
                    val = line.get_value()
                    values.append(val)
                    time.sleep(0.02)  # 20ms

                line.release()

                # Count changes
                changes = sum(1 for i in range(1, len(values)) if values[i] != values[i-1])
                highs = sum(values)
                lows = len(values) - highs

                print(f"\n  Line 5 (GPIO5) Test:")
                print(f"    Values: {values}")
                print(f"    Highs: {highs}, Lows: {lows}")
                print(f"    Changes: {changes}")

                if changes >= 3:
                    print(f"\n  ✓ SIGNAL DETECTED on {chip_path} line 5")
                    results.append((chip_path, 5, "GPIO5"))
                elif changes == 0:
                    print(f"\n  ✗ No signal (all {values[0]})")
                else:
                    print(f"\n  ⚠ Some changes (possible noise)")

            except Exception as e:
                print(f"\n  ✗ Error testing line 5: {e}")
        else:
            print(f"\n  ✗ Chip has only {num_lines} lines, cannot test line 5")

        # Also test line 17 (GPIO17) for reference
        if num_lines > 17:
            try:
                line = chip.get_line(17)
                line.request(consumer="test", type=gpiod.LINE_REQ_DIR_IN)

                values = []
                for i in range(10):
                    val = line.get_value()
                    values.append(val)
                    time.sleep(0.02)

                line.release()

                changes = sum(1 for i in range(1, len(values)) if values[i] != values[i-1])

                print(f"\n  Line 17 (GPIO17) Test:")
                print(f"    Values: {values}")
                print(f"    Changes: {changes}")

                if changes >= 3:
                    print(f"\n  ✓ SIGNAL DETECTED on {chip_path} line 17")
                    results.append((chip_path, 17, "GPIO17"))

            except Exception as e:
                print(f"\n  ✗ Error testing line 17: {e}")

        chip.close()

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Testing: {chip_path}")
        print(f"{'='*60}")
        print(f"\n  ✗ Error opening chip: {e}")

# Print summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

if results:
    print("\n✓ Signals detected on:")
    for chip, line, desc in results:
        print(f"  - {chip} line {line} ({desc})")

    print("\nConclusion:")
    if len(results) == 1:
        chip, line, desc = results[0]
        print(f"  Your signal is on: {chip} line {line}")
        print(f"  Update configuration to use this chip!")
    else:
        print(f"  Multiple signals detected, check which is your GPIO5")
else:
    print("\n✗ No signal detected on any chip")
    print("\nPossible reasons:")
    print("  1. Signal not connected to GPIO pins")
    print("  2. Wrong physical pin (check Pin 29)")
    print("  3. Signal frequency too high (need faster sampling)")
    print("  4. Signal amplitude too low (need >1.5V)")
    print("  5. Wrong chip/line mapping (RP1 uses different numbering)")

print("\n" + "=" * 60)
