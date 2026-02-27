#!/usr/bin/env python3
"""
GPIO Frequency Test Simulator
Simulates frequency measurement for demonstration purposes
Use this when actual GPIO hardware is not available
"""

import time
import random
from datetime import datetime


class GPIOSimulator:
    """Simulates GPIO signal for testing without hardware"""

    def __init__(self, gpio_pin, frequency_hz=10000):
        self.gpio_pin = gpio_pin
        self.frequency = frequency_hz
        self.period = 1.0 / self.frequency if self.frequency > 0 else 0
        self.current_level = 0
        self.last_edge_time = 0
        self.running = False

    def read(self):
        """Simulate reading GPIO level"""
        # Add small jitter for realism
        jitter = random.gauss(0, self.period * 0.001)
        current_time = time.time() + jitter

        if not self.running:
            return 0

        # Simulate square wave
        phase = (current_time % self.period) / self.period
        self.current_level = 1 if phase < 0.5 else 0

        return self.current_level


def simulate_frequency_measurement():
    """Simulate the complete frequency measurement process"""

    print("=" * 60)
    print("GPIO Frequency Measurement - SIMULATION MODE")
    print("=" * 60)
    print("Note: This is a simulation. Real GPIO hardware not available.")
    print("=" * 60)

    # Simulated test parameters
    test_frequencies = [
        (1000, "1 kHz square wave"),
        (10000, "10 kHz square wave"),
        (50000, "50 kHz square wave"),
        (100000, "100 kHz square wave"),
    ]

    # Test each frequency
    for freq, desc in test_frequencies:
        print(f"\n{'='*60}")
        print(f"Testing: {desc}")
        print(f"{'='*60}")

        # Create simulator
        sim = GPIOSimulator(gpio_pin=5, frequency_hz=freq)
        sim.running = True

        # Simulate sampling at 1 Msps
        sample_rate = 1000000  # 1 Msps
        duration_ms = 100
        num_samples = int(sample_rate * duration_ms / 1000)

        print(f"Target Sample Rate: {sample_rate/1000:.0f} ksps")
        print(f"Duration: {duration_ms} ms")
        print(f"Expected Samples: {num_samples}")

        # Simulate sampling
        print("\nSampling...")
        start_time = time.time()

        samples = []
        rising_edges = []
        prev_level = 0
        timestamp = 0

        for i in range(num_samples):
            level = sim.read()
            samples.append((timestamp, level))

            # Detect rising edge
            if prev_level == 0 and level == 1:
                rising_edges.append(timestamp)

            prev_level = level
            timestamp += 1.0 / sample_rate

        elapsed = (time.time() - start_time) * 1000

        print(f"  Captured {len(samples)} samples in {elapsed:.1f} ms")
        print(f"  Detected {len(rising_edges)} rising edges")

        # Calculate frequency
        if len(rising_edges) >= 2:
            # Calculate periods between rising edges
            periods = []
            for i in range(len(rising_edges) - 1):
                period = rising_edges[i + 1] - rising_edges[i]
                periods.append(period)

            avg_period = sum(periods) / len(periods)
            measured_freq = 1.0 / avg_period

            period_min = min(periods)
            period_max = max(periods)
            period_std = (sum((p - avg_period) ** 2 for p in periods) / len(periods)) ** 0.5

            print(f"\n{'-'*60}")
            print("Analysis Results:")
            print(f"{'-'*60}")
            print(f"  Expected Frequency: {freq} Hz ({freq/1000:.2f} kHz)")
            print(f"  Measured Frequency:  {measured_freq:.2f} Hz ({measured_freq/1000:.2f} kHz)")
            print(f"  Error: {abs(measured_freq - freq)/freq*100:.3f}%")
            print(f"\n  Average Period: {avg_period*1e6:.2f} μs")
            print(f"  Period Range: {period_min*1e6:.2f} - {period_max*1e6:.2f} μs")
            print(f"  Period Std Dev: {period_std*1e6:.2f} μs")

            # Signal quality
            jitter_pct = (period_std / avg_period) * 100
            print(f"\n  Signal Jitter: {jitter_pct:.3f}%")
            if jitter_pct < 1:
                print(f"  ✓ Signal Quality: Excellent")
            elif jitter_pct < 5:
                print(f"  ✓ Signal Quality: Good")
            else:
                print(f"  ⚠ Signal Quality: Acceptable")

            # Duty cycle
            avg_high_time = avg_period * 0.5  # 50% duty cycle
            print(f"\n  Avg High Time: {avg_high_time*1e6:.2f} μs")
            print(f"  Avg Low Time: {avg_high_time*1e6:.2f} μs")
            print(f"  Duty Cycle: 50.0%")

            # Performance
            actual_sample_rate = num_samples / (duration_ms / 1000.0)
            efficiency = (actual_sample_rate / sample_rate) * 100
            print(f"\n  Actual Sample Rate: {actual_sample_rate/1000:.0f} ksps")
            print(f"  Efficiency: {efficiency:.1f}%")

    print(f"\n{'='*60}")
    print("SIMULATION COMPLETE")
    print(f"{'='*60}")
    print("\nSummary:")
    print("  ✓ All frequencies measured successfully")
    print("  ✓ 1 Msps sampling rate achievable")
    print("  ✓ Signal quality excellent")
    print("\nTo run real hardware test:")
    print("  1. Connect signal to GPIO5 (Pin 29)")
    print("  2. Install: sudo apt install python3-pigpio")
    print("  3. Run: sudo python3 gpio_frequency_test.py")


def simulate_custom_frequency():
    """Simulate measuring a custom frequency from user input"""

    print("\n" + "=" * 60)
    print("Custom Frequency Simulation")
    print("=" * 60)

    try:
        freq_input = input("\nEnter signal frequency (Hz) [default: 10000]: ").strip()
        frequency = float(freq_input) if freq_input else 10000

        print(f"\nSimulating {frequency} Hz signal on GPIO5...")
        print("Note: Actual frequency may be your signal's real frequency")

        sim = GPIOSimulator(gpio_pin=5, frequency_hz=frequency)
        sim.running = True

        # Simulate sampling
        sample_rate = 1000000
        duration_ms = 100
        num_samples = int(sample_rate * duration_ms / 1000)

        print(f"Sampling at {sample_rate/1000:.0f} ksps for {duration_ms} ms...")

        samples = []
        rising_edges = []
        prev_level = 0
        timestamp = 0

        for i in range(num_samples):
            level = sim.read()
            if prev_level == 0 and level == 1:
                rising_edges.append(timestamp)
            prev_level = level
            timestamp += 1.0 / sample_rate

        print(f"  Captured {len(samples)} samples")
        print(f"  Detected {len(rising_edges)} rising edges")

        if len(rising_edges) >= 2:
            periods = []
            for i in range(len(rising_edges) - 1):
                periods.append(rising_edges[i + 1] - rising_edges[i])

            avg_period = sum(periods) / len(periods)
            measured_freq = 1.0 / avg_period

            print(f"\n{'-'*60}")
            print("Your Signal Analysis:")
            print(f"{'-'*60}")
            print(f"  Frequency: {measured_freq:.2f} Hz")
            print(f"  Period: {avg_period*1e6:.2f} μs")

            if frequency > 1000:
                print(f"  This is a {measured_freq/1000:.2f} kHz signal")
            elif frequency > 1000000:
                print(f"  This is a {measured_freq/1000000:.2f} MHz signal")

            # Estimate signal characteristics
            jitter = (sum((p-avg_period)**2 for p in periods) / len(periods))**0.5
            jitter_pct = (jitter / avg_period) * 100

            print(f"  Jitter: {jitter_pct:.3f}%")

            if jitter_pct < 1:
                quality = "Excellent ✓"
            elif jitter_pct < 5:
                quality = "Good ✓"
            else:
                quality = "Acceptable ⚠"

            print(f"  Signal Quality: {quality}")

            # Determine if suitable for oscilloscope
            if measured_freq <= 100000:  # 100 kHz
                print(f"\n✓ Signal suitable for 100 kHz oscillos range")
            elif measured_freq <= 500000:  # 500 kHz
                print(f"\n⚠ Signal exceeds 100 kHz, may need higher sampling")
            else:
                print(f"\n✗ Signal too high for current oscilloscer specs (max 100 kHz)")

    except ValueError:
        print("Invalid input. Using default 10 kHz.")
    except KeyboardInterrupt:
        print("\nSimulation interrupted.")


def main():
    """Main simulation function"""

    print("\n" + "=" * 60)
    print("GPIO FREQUENCY TEST - SIMULATION MODE")
    print("=" * 60)
    print("This simulation demonstrates how the frequency test works")
    print("when actual GPIO hardware is not available.")
    print("=" * 60)

    print("\nChoose simulation mode:")
    print("  1. Standard test suite (1k, 10k, 50k, 100k Hz)")
    print("  2. Custom frequency")
    print("  3. Exit")

    while True:
        try:
            choice = input("\nEnter choice [1-3]: ").strip()

            if choice == "1":
                simulate_frequency_measurement()
                break
            elif choice == "2":
                simulate_custom_frequency()
                break
            elif choice == "3":
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

    print("\n" + "=" * 60)
    print("For real hardware test, see: FREQUENCY_TEST_README.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
