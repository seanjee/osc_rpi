#!/usr/bin/env python3
"""
GPIO Frequency Measurement Tool - FIXED
Using /dev/gpiochip4 (RP1) for Raspberry Pi 5 / Ubuntu 24.04
"""

import sys
import os
import time
from datetime import datetime

# Try to import GPIO libraries
GPIO_LIBRARY = None

# Priority 1: libgpiod (recommended for Ubuntu)
try:
    import gpiod
    GPIO_LIBRARY = "libgpiod"
    print(f"✓ Using libgpiod library (recommended for Ubuntu)")
except ImportError:
    pass

# Priority 2: pigpio
if GPIO_LIBRARY is None:
    try:
        import pigpio
        GPIO_LIBRARY = "pigpio"
        print(f"✓ Using pigpio library")
    except ImportError:
        pass

# Priority 3: RPi.GPIO
if GPIO_LIBRARY is None:
    try:
        import RPi.GPIO as GPIO
        GPIO_LIBRARY = "RPi.GPIO"
        print(f"✓ Using RPi.GPIO library")
    except ImportError:
        pass

if GPIO_LIBRARY is None:
    print("✗ No GPIO library found!")
    print("\nTo install on Ubuntu 24.04:")
    print("  sudo bash install_gpio_ubuntu.sh")
    sys.exit(1)


class FrequencyMeasurer:
    """High-frequency square wave measurement tool"""

    # CRITICAL FIX: Use /dev/gpiochip4 (RP1) not gpiochip0
    GPIO_CHIP = "/dev/gpiochip4"
    GPIO5_OFFSET = 5  # GPIO5 on RP1

    def __init__(self, gpio_pin=5, sample_rate=1000000):
        self.gpio_pin = gpio_pin
        self.sample_rate = sample_rate
        self.samples = []
        self.pi = None
        self.chip = None
        self.line = None

        # Check for root/sudo
        if os.geteuid() != 0:
            print("\n⚠️  WARNING: Not running as root/sudo")
            print("   GPIO access requires root privileges.")

        # Initialize GPIO
        if GPIO_LIBRARY == "libgpiod":
            self._init_libgpiod()
        elif GPIO_LIBRARY == "pigpio":
            self._init_pigpio()
        elif GPIO_LIBRARY == "RPi.GPIO":
            self._init_rpi_gpio()

    def _init_libgpiod(self):
        """Initialize using libgpiod with correct chip"""
        try:
            # FIXED: Use /dev/gpiochip4 (RP1) instead of gpiochip0
            self.chip = gpiod.Chip(self.GPIO_CHIP)

            # Request GPIO5 as input
            self.line = self.chip.get_line(self.GPIO5_OFFSET)
            self.line.request(consumer="osc_scope", type=gpiod.LINE_REQ_DIR_IN)

            print(f"✓ GPIO {self.gpio_pin} initialized (libgpiod)")
            print(f"  Using chip: {self.GPIO_CHIP} (RP1)")
            print(f"  Line offset: {self.GPIO5_OFFSET}")
        except PermissionError:
            print(f"\n✗ Permission denied accessing {self.GPIO_CHIP}")
            print(f"\nRun with: sudo python3 gpio_frequency_test.py")
            raise
        except Exception as e:
            print(f"\n✗ Error initializing GPIO: {e}")
            raise

    def _init_pigpio(self):
        """Initialize using pigpio"""
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Failed to connect to pigpio daemon")

        self.pi.set_mode(self.gpio_pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.gpio_pin, pigpio.PUD_OFF)
        print(f"✓ GPIO {self.gpio_pin} initialized (pigpio)")

    def _init_rpi_gpio(self):
        """Initialize using RPi.GPIO"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_pin, GPIO.IN)
        print(f"✓ GPIO {self.gpio_pin} initialized (RPi.GPIO)")

    def measure_frequency(self, duration_ms=100):
        """Measure frequency"""
        print(f"\nMeasuring frequency at {self.sample_rate/1000:.0f} ksps for {duration_ms}ms...")

        if GPIO_LIBRARY == "libgpiod":
            return self._measure_frequency_polling(duration_ms)
        elif GPIO_LIBRARY == "pigpio":
            return self._measure_frequency_pigpio(duration_ms)
        elif GPIO_LIBRARY == "RPi.GPIO":
            return self._measure_frequency_polling(duration_ms)

    def _measure_frequency_polling(self, duration_ms):
        """Measure using high-speed polling"""
        duration = duration_ms / 1000.0
        num_samples = int(self.sample_rate * duration)

        print(f"  Target samples: {num_samples}")
        print(f"  Polling GPIO {self.gpio_pin} on {self.GPIO_CHIP}...")

        samples = []
        start_time = time.time()
        prev_level = None
        edge_count = 0

        # High-speed polling loop
        for i in range(num_samples):
            # Read GPIO level
            if GPIO_LIBRARY == "libgpiod":
                level = self.line.get_value()
            elif GPIO_LIBRARY == "RPi.GPIO":
                level = GPIO.input(self.gpio_pin)
            else:
                level = 0

            samples.append(level)

            # Count edges
            if prev_level is not None and level != prev_level:
                edge_count += 1

            prev_level = level

        elapsed = time.time() - start_time
        actual_rate = num_samples / elapsed

        print(f"  Captured {len(samples)} samples in {elapsed*1000:.1f} ms")
        print(f"  Actual rate: {actual_rate/1000:.1f} ksps")
        print(f"  Total edges: {edge_count}")

        return self._analyze_samples(samples)

    def _measure_frequency_pigpio(self, duration_ms):
        """Measure using pigpio's fast sampling"""
        duration = duration_ms / 1000.0

        print(f"  Using pigpio edge detection...")

        edges = []
        start_time = time.time()

        def edge_callback(gpio, level, tick):
            if len(edges) < 10000:
                edges.append(time.time())

        self.pi.callback(self.gpio_pin, pigpio.EITHER_EDGE, edge_callback)
        time.sleep(duration)
        self.pi.callback(self.gpio_pin, pigpio.EITHER_EDGE, None)

        return self._analyze_edges(edges)

    def _analyze_samples(self, samples):
        """Analyze polled samples to calculate frequency"""
        if len(samples) < 2:
            print("✗ Not enough samples")
            return None

        # Find rising edges
        rising_edges = []
        prev_level = samples[0]

        for i, level in enumerate(samples[1:], 1):
            if prev_level == 0 and level == 1:
                edge_time = i / self.sample_rate
                rising_edges.append(edge_time)
            prev_level = level

        if len(rising_edges) < 2:
            print(f"✗ Only {len(rising_edges)} rising edge(s) detected")
            print("  Check if signal is connected")
            return None

        # Calculate periods
        periods = []
        for i in range(len(rising_edges) - 1):
            period = rising_edges[i + 1] - rising_edges[i]
            periods.append(period)

        avg_period = sum(periods) / len(periods)
        frequency = 1.0 / avg_period if avg_period > 0 else 0

        # Statistics
        period_min = min(periods)
        period_max = max(periods)
        period_std = (sum((p - avg_period) ** 2 for p in periods) / len(periods)) ** 0.5

        # Duty cycle
        total_high_time = sum(samples) * (1.0 / self.sample_rate)
        total_time = len(samples) / self.sample_rate
        duty_cycle = (total_high_time / total_time) * 100

        # Print results
        print(f"\n{'='*60}")
        print("FREQUENCY MEASUREMENT RESULTS")
        print(f"{'='*60}")
        print(f"Method: {GPIO_LIBRARY} Polling")
        print(f"GPIO Chip: {self.GPIO_CHIP}")
        print(f"GPIO Line: {self.GPIO5_OFFSET} (Pin 29)")
        print(f"Rising Edges: {len(rising_edges)}")
        print(f"\n{'-'*60}")
        print("Frequency Analysis:")
        print(f"{'-'*60}")
        print(f"  Average Period: {avg_period*1e6:.2f} μs")
        print(f"  Frequency: {frequency:.2f} Hz")
        print(f"  Period Range: {period_min*1e6:.2f} - {period_max*1e6:.2f} μs")
        print(f"  Period Std Dev: {period_std*1e6:.2f} μs")
        print(f"\nDuty Cycle Analysis:")
        print(f"{'-'*60}")
        print(f"  Duty Cycle: {duty_cycle:.1f}%")
        print(f"  Expected for 3.3V square wave: ~50%")

        # Signal quality
        jitter_pct = (period_std / avg_period) * 100 if avg_period > 0 else 100
        print(f"\n  Signal Jitter: {jitter_pct:.3f}%")
        if jitter_pct < 1:
            print(f"  ✓ Signal Quality: Excellent")
        elif jitter_pct < 5:
            print(f"  ✓ Signal Quality: Good")
        elif jitter_pct < 15:
            print(f"  ⚠ Signal Quality: Acceptable")
        else:
            print(f"  ✗ Signal Quality: Poor")

        print(f"{'='*60}")

        return {
            'frequency': frequency,
            'period': avg_period,
            'period_std': period_std,
            'rising_edges': len(rising_edges),
            'duty_cycle': duty_cycle
        }

    def _analyze_edges(self, edges):
        """Analyze edge data from pigpio"""
        if len(edges) < 2:
            print("✗ Not enough edges detected")
            return None

        rising_edges = edges[::2]

        if len(rising_edges) < 2:
            print(f"✗ Only {len(rising_edges)} rising edge(s) detected")
            return None

        periods = []
        for i in range(len(rising_edges) - 1):
            periods.append(rising_edges[i + 1] - rising_edges[i])

        avg_period = sum(periods) / len(periods)
        frequency = 1.0 / avg_period if avg_period > 0 else 0

        print(f"\n{'='*60}")
        print("FREQUENCY MEASUREMENT RESULTS")
        print(f"{'='*60}")
        print(f"Method: Pigpio Edge Detection")
        print(f"Frequency: {frequency:.2f} Hz")
        print(f"Period: {avg_period*1e6:.2f} μs")
        print(f"{'='*60}")

        return {'frequency': frequency, 'period': avg_period}

    def cleanup(self):
        """Clean up GPIO resources"""
        if GPIO_LIBRARY == "libgpiod":
            if self.line:
                self.line.release()
            if self.chip:
                self.chip.close()
        elif GPIO_LIBRARY == "pigpio" and self.pi:
            self.pi.stop()
        elif GPIO_LIBRARY == "RPi.GPIO":
            import RPi.GPIO as GPIO
            GPIO.cleanup()


def main():
    print("=" * 60)
    print("GPIO Frequency Measurement Tool - FIXED")
    print("Ubuntu 24.04 / Raspberry Pi 5")
    print("=" * 60)
    print(f"GPIO Pin: 5 (Physical Pin 29)")
    print(f"GPIO Chip: /dev/gpiochip4 (RP1)")
    print(f"Target Sample Rate: 1 Msps")
    print(f"Signal Amplitude: 3.3V")
    print("=" * 60)

    measurer = FrequencyMeasurer(gpio_pin=5, sample_rate=1000000)

    try:
        # Measure for 100ms
        result = measurer.measure_frequency(duration_ms=100)

        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)

        if result and 'frequency' in result:
            freq = result['frequency']
            print(f"✓ Successfully measured signal")
            print(f"  Frequency: {freq:.2f} Hz")

            if freq > 1000:
                print(f"  This is a {freq/1000:.2f} kHz signal")
            elif freq > 1000000:
                print(f"  This is a {freq/1000000:.2f} MHz signal")

            # Check if within oscilloscope range
            if freq <= 100000:
                print(f"\n✓ Signal is within 100 kHz oscilloscope range")
            else:
                print(f"\n⚠ Signal exceeds 100 kHz range")

    except KeyboardInterrupt:
        print("\n\nMeasurement interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        measurer.cleanup()
        print("\n✓ GPIO cleaned up")


if __name__ == "__main__":
    main()
