#!/usr/bin/env python3
"""
GPIO Frequency Measurement - Optimized
Use more accurate time measurement and optimized sampling
"""

import gpiod
import time
import sys

# CRITICAL: Use correct chip for RP1
GPIO_CHIP = "/dev/gpiochip4"
GPIO5_OFFSET = 5

print("=" * 60)
print("Optimized GPIO Frequency Measurement")
print("Using high-precision timing")
print("=" * 60)
print(f"GPIO Chip: {GPIO_CHIP} (RP1)")
print(f"GPIO Line: {GPIO5_OFFSET} (Pin 29)")
print("=" * 60)

try:
    # Open GPIO chip
    chip = gpiod.Chip(GPIO_CHIP)
    line = chip.get_line(GPIO5_OFFSET)
    line.request(consumer="osc_test", type=gpiod.LINE_REQ_DIR_IN)

    print("✓ GPIO initialized")
    print(f"\nExpected signal: 10 kHz square wave (0V - 3.3V)")
    print("Expected period: 100 μs")
    print("=" * 60)

    # Method 1: Edge detection with high-precision timing
    print("\nMethod 1: Edge Detection with time.perf_counter()")
    print("-" * 60)

    edges = []
    start_time = time.perf_counter()

    # Capture edges for 50ms (5 cycles at 10kHz)
    capture_duration = 0.05
    last_level = line.get_value()
    last_edge_time = start_time

    while (time.perf_counter() - start_time) < capture_duration:
        current_level = line.get_value()

        if current_level != last_level:
            edge_time = time.perf_counter()
            edges.append((edge_time, current_level))
            last_level = current_level

            # Debug: print first few edges
            if len(edges) <= 10:
                time_from_start = (edge_time - start_time) * 1e6
                print(f"  Edge #{len(edges)}: {time_from_start:.2f} μs → {current_level}")

        # Small sleep to prevent 100% CPU
        time.sleep(0.0001)  # 0.1 ms

    total_time = time.perf_counter() - start_time
    print(f"\nCaptured {len(edges)} edges in {total_time*1000:.2f} ms")

    # Analyze rising edges
    rising_edges = [t for t, level in edges if level == 1]

    if len(rising_edges) >= 2:
        # Calculate periods
        periods = []
        for i in range(len(rising_edges) - 1):
            period = rising_edges[i + 1] - rising_edges[i]
            periods.append(period * 1e6)  # Convert to microseconds

        avg_period = sum(periods) / len(periods)
        frequency = 1.0 / (avg_period / 1e6)

        # Statistics
        period_min = min(periods)
        period_max = max(periods)
        period_std = (sum((p - avg_period) ** 2 for p in periods) / len(periods)) ** 0.5

        print(f"\nFrequency Analysis (Edge Detection):")
        print(f"  Rising edges: {len(rising_edges)}")
        print(f"  Average period: {avg_period:.2f} μs")
        print(f"  Expected period: 100.00 μs (10 kHz)")
        print(f"  Period range: {period_min:.2f} - {period_max:.2f} μs")
        print(f"  Period std dev: {period_std:.2f} μs")
        print(f"  Calculated frequency: {frequency:.2f} Hz ({frequency/1000:.2f} kHz)")

        error_pct = abs(frequency - 10000) / 10000 * 100
        print(f"  Error: {error_pct:.2f}%")

        if error_pct < 5:
            print(f"  ✓ Excellent accuracy!")
        elif error_pct < 10:
            print(f"  ✓ Good accuracy")
        elif error_pct < 20:
            print(f"  ⚠ Acceptable accuracy")
        else:
            print(f"  ✗ Poor accuracy - need better method")

    # Method 2: Fixed-interval sampling with precise timing
    print(f"\n{'='*60}")
    print("Method 2: Fixed-Interval Sampling (50 kHz target)")
    print("-" * 60)

    sample_interval = 1.0 / 50000  # 50 kHz = 20 μs per sample
    duration = 0.1  # 100 ms
    target_samples = int(duration / sample_interval)

    print(f"Target sample rate: 50 kHz")
    print(f"Sample interval: {sample_interval*1e6:.1f} μs")
    print(f"Target samples: {target_samples}")
    print(f"Duration: {duration*1000:.0f} ms")

    samples = []
    next_sample_time = time.perf_counter()

    for i in range(target_samples):
        # Wait until next sample time
        now = time.perf_counter()
        if now < next_sample_time:
            time.sleep(next_sample_time - now)

        # Read GPIO
        samples.append(line.get_value())
        next_sample_time += sample_interval

    total_sampling_time = time.perf_counter() - start_time
    actual_sample_rate = target_samples / (total_sampling_time * 0.1)  # Normalize

    print(f"\nActual samples: {len(samples)}")
    print(f"Total time: {total_sampling_time*1000:.2f} ms")
    print(f"Actual sample rate: {actual_sample_rate:.1f} Hz")

    # Analyze samples
    rising_edges = []
    prev_level = samples[0]

    for i, level in enumerate(samples[1:], 1):
        if prev_level == 0 and level == 1:
            rising_edges.append(i / target_samples * duration)

        prev_level = level

    if len(rising_edges) >= 2:
        periods = []
        for i in range(len(rising_edges) - 1):
            periods.append(rising_edges[i + 1] - rising_edges[i])

        avg_period = sum(periods) / len(periods)
        frequency = 1.0 / avg_period

        period_std = (sum((p - avg_period) ** 2 for p in periods) / len(periods)) ** 0.5

        print(f"\nFrequency Analysis (Fixed-Interval Sampling):")
        print(f"  Rising edges: {len(rising_edges)}")
        print(f"  Average period: {avg_period*1e6:.2f} μs")
        print(f"  Calculated frequency: {frequency:.2f} Hz ({frequency/1000:.2f} kHz)")

        error_pct = abs(frequency - 10000) / 10000 * 100
        print(f"  Error: {error_pct:.2f}%")

        # Calculate duty cycle
        high_count = sum(samples)
        duty_cycle = (high_count / len(samples)) * 100
        print(f"\n  Duty cycle: {duty_cycle:.1f}% (expected ~50%)")

    # Method 3: Simple count-over-time (most reliable for low frequency)
    print(f"\n{'='*60}")
    print("Method 3: Edge Count Over Time")
    print("-" * 60)

    test_duration = 1.0  # 1 second
    print(f"Counting edges over {test_duration} second...")

    edge_count = 0
    last_level = line.get_value()
    start = time.perf_counter()

    while (time.perf_counter() - start) < test_duration:
        current_level = line.get_value()
        if current_level != last_level:
            edge_count += 1
            last_level = current_level
        time.sleep(0.0001)

    actual_duration = time.perf_counter() - start
    frequency = edge_count / 2 / actual_duration  # 2 edges per cycle

    print(f"\nEdge Count Analysis:")
    print(f"  Total edges: {edge_count}")
    print(f"  Duration: {actual_duration:.3f} s")
    print(f"  Cycles: {edge_count/2:.0f}")
    print(f"  Frequency: {frequency:.2f} Hz ({frequency/1000:.2f} kHz)")

    error_pct = abs(frequency - 10000) / 10000 * 100
    print(f"  Error: {error_pct:.2f}%")

    if error_pct < 1:
        print(f"  ✓ Excellent accuracy!")
    elif error_pct < 5:
        print(f"  ✓ Good accuracy")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("=" * 60)
    print("10 kHz square wave measurement results:")
    print(f"\n  Method 1 (Edge Detection):      SEE ABOVE")
    print(f"  Method 2 (Fixed-Interval):       SEE ABOVE")
    print(f"  Method 3 (Edge Count):          {frequency/1000:.2f} kHz")
    print(f"\n  Expected: 10.00 kHz")
    print(f"\nRecommendation:")
    print(f"  For 10 kHz signal, Method 3 (Edge Count) is most accurate.")
    print(f"  For higher frequencies, use pigpio DMA or C extension.")

    # Cleanup
    line.release()
    chip.close()

    print("\n✓ GPIO cleaned up")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
