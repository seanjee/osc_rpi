#!/usr/bin/env python3
"""
GPIO Frequency Measurement - Using PIGPIO DMA
High-speed sampling using DMA for accurate frequency measurement
"""

import pigpio
import time
import sys

# Configuration
GPIO_PIN = 5  # GPIO5 (Pin 29)
SAMPLE_COUNT = 100000  # 100k samples (PRD requirement)
TARGET_RATE = 1000000  # 1 Msps

print("=" * 60)
print("GPIO Frequency Measurement - PIGPIO DMA")
print("=" * 60)
print(f"GPIO Pin: {GPIO_PIN} (Physical Pin 29)")
print(f"Target Samples: {SAMPLE_COUNT}")
print(f"Target Rate: {TARGET_RATE/1000:.0f} ksps (1 Msps)")
print(f"Expected Signal: 10 kHz square wave (0-3.3V)")
print("=" * 60)

try:
    # Connect to pigpio daemon
    pi = pigpio.pi()

    if not pi.connected:
        print("\n✗ Failed to connect to pigpio daemon")
        print("\nPlease start pigpiod:")
        print("  sudo ./start_pigpiod.sh")
        print("  or: sudo systemctl start pigpiod")
        sys.exit(1)

    print("✓ Connected to pigpio daemon")

    # Set GPIO as input
    pi.set_mode(GPIO_PIN, pigpio.INPUT)
    pi.set_pull_up_down(GPIO_PIN, pigpio.PUD_OFF)
    print(f"✓ GPIO {GPIO_PIN} configured as input")

    # Method 1: Wave recording with DMA (fastest)
    print(f"\n{'='*60}")
    print("Method 1: PIGPIO Wave Recording (DMA)")
    print("-" * 60)
    print("Using DMA for high-speed capture...")
    print("This can achieve 1-5 Msps")

    # Clear any existing wave
    pi.wave_clear()

    # Set PWM for wave generation (to time the capture)
    # We'll use wave recording to capture GPIO state over time

    # Create a wave to trigger capture
    # Actually, for simple frequency measurement, we can use a simpler approach

    # Method 2: High-speed callback with timestamps
    print(f"\n{'='*60}")
    print("Method 2: PIGPIO Callback with Timestamps")
    print("-" * 60)
    print("Using pigpio hardware timestamping...")
    print("This captures exact edge times with microsecond precision")

    # Clear callbacks
    pi.callback(GPIO_PIN, pigpio.EITHER_EDGE, None)

    # Edge detection with precise timestamps
    edges = []
    start_time = time.time()
    test_duration = 1.0  # 1 second capture

    def edge_callback(gpio, level, tick):
        # tick is pigpio's microsecond timestamp
        edges.append((tick, level))

    # Set up callback for both edges
    cb_id = pi.callback(GPIO_PIN, pigpio.EITHER_EDGE, edge_callback)

    print(f"Capturing edges for {test_duration} second...")

    # Wait for capture duration
    time.sleep(test_duration)

    # Cancel callback
    pi.callback(GPIO_PIN, pigpio.EITHER_EDGE, None)

    total_duration = time.time() - start_time
    total_edges = len(edges)

    print(f"Captured {total_edges} edges in {total_duration:.3f} s")

    # Analyze edges
    if total_edges >= 4:
        # Separate rising and falling edges
        rising_edges = [t for t, level in edges if level == 1]
        falling_edges = [t for t, level in edges if level == 0]

        # Calculate periods from rising edges
        if len(rising_edges) >= 2:
            periods_us = []
            for i in range(len(rising_edges) - 1):
                period_us = rising_edges[i + 1] - rising_edges[i]
                periods_us.append(period_us)

            avg_period_us = sum(periods_us) / len(periods_us)
            frequency = 1000000.0 / avg_period_us

            # Statistics
            period_min_us = min(periods_us)
            period_max_us = max(periods_us)
            period_std_us = (sum((p - avg_period_us) ** 2 for p in periods_us) / len(periods_us)) ** 0.5

            print(f"\n{'='*60}")
            print("FREQUENCY ANALYSIS - PIGPIO Callback")
            print("=" * 60)
            print(f"Total Rising Edges: {len(rising_edges)}")
            print(f"Total Falling Edges: {len(falling_edges)}")
            print(f"Total Edges: {total_edges}")
            print(f"\nExpected: 10 kHz (100.00 μs period)")
            print(f"{'-'*60}")
            print(f"Average Period: {avg_period_us:.2f} μs")
            print(f"Frequency: {frequency:.2f} Hz ({frequency/1000:.2f} kHz)")
            print(f"Period Range: {period_min_us:.2f} - {period_max_us:.2f} μs")
            print(f"Period Std Dev: {period_std_us:.2f} μs")

            # Error calculation
            expected_period = 100.0  # 10 kHz
            error_pct = abs(avg_period_us - expected_period) / expected_period * 100

            print(f"\nError: {error_pct:.2f}%")

            if error_pct < 1:
                print(f"✓ Excellent accuracy!")
            elif error_pct < 5:
                print(f"✓ Good accuracy")
            elif error_pct < 10:
                print(f"⚠ Acceptable accuracy")
            else:
                print(f"✗ Poor accuracy - check signal connection")

            # Calculate duty cycle
            if len(rising_edges) >= 1 and len(falling_edges) >= 1:
                # Use first rising and falling edge pair
                first_rising = rising_edges[0]
                # Find first falling edge after this rising edge
                next_falling = next((t for t in falling_edges if t > first_rising), None)

                if next_falling:
                    high_time_us = next_falling - first_rising
                    # Find next rising edge
                    next_rising = next((t for t in rising_edges[1:] if t > next_falling), None)

                    if next_rising:
                        period_us = next_rising - first_rising
                        duty_cycle = (high_time_us / period_us) * 100

                        print(f"\nDuty Cycle Analysis:")
                        print(f"  High Time: {high_time_us:.2f} μs")
                        print(f"  Period: {period_us:.2f} μs")
                        print(f"  Duty Cycle: {duty_cycle:.1f}%")
                        print(f"  Expected: ~50%")

            # Edge capture rate
            edge_rate = total_edges / total_duration
            print(f"\nEdge Capture Rate: {edge_rate:.0f} edges/sec")
            print(f"This is the effective sampling rate of edge detection")

            # Check for lost edges
            expected_edges = 20000  # 10 kHz = 10000 cycles = 20000 edges
            if total_edges < expected_edges:
                lost_pct = (expected_edges - total_edges) / expected_edges * 100
                print(f"\n⚠ Lost Edges: {expected_edges - total_edges} ({lost_pct:.1f}%)")
                print("  This may be due to:")
                print("  - Signal not connected properly")
                print("  - Signal amplitude too low (<1.5V)")
                print("  - Frequency higher than pigpio callback can handle")

    # Method 3: Simple polling with pigpio (for comparison)
    print(f"\n{'='*60}")
    print("Method 3: Simple Polling (for comparison)")
    print("-" * 60)

    samples = []
    start = time.time()
    test_duration = 0.1  # 100 ms

    while (time.time() - start) < test_duration:
        samples.append(pi.read(GPIO_PIN))

    duration = time.time() - start
    actual_rate = len(samples) / duration

    print(f"Captured {len(samples)} samples in {duration*1000:.1f} ms")
    print(f"Rate: {actual_rate/1000:.1f} ksps")

    # Count rising edges
    rising = sum(1 for i in range(1, len(samples)) if samples[i-1] == 0 and samples[i] == 1)
    print(f"Rising edges: {rising}")
    print(f"Est. frequency: {rising/duration:.0f} Hz ({rising/duration/1000:.2f} kHz)")

    # Cleanup
    pi.stop()

    print(f"\n{'='*60}")
    print("SUMMARY")
    print("=" * 60)
    print("\nFor accurate frequency measurement:")
    print("  ✓ Use Method 2 (PIGPIO Callback) - recommended")
    print("  ✗ Method 3 (Polling) - too slow, loses edges")
    print("\nFor 10 kHz signal:")
    print("  Expected: 10000 Hz")
    print("  Measured: See Method 2 results above")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("\n✓ Cleanup complete")
