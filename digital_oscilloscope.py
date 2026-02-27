#!/usr/bin/env python3
"""
Digital Oscilloscope - GPIO Sampling
Captures GPIO pin state changes with timing
"""

import time
import RPi.GPIO as GPIO
from datetime import datetime

class DigitalOscilloscope:
    def __init__(self, pin, duration_ms=1000):
        self.pin = pin
        self.duration_ms = duration_ms
        self.samples = []

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)

    def capture_polling(self):
        """
        Capture using polling (moderate speed)
        Estimated: 50-150 kHz
        """
        print(f"\nCapturing GPIO {self.pin} (polling mode)...")
        print(f"Duration: {self.duration_ms}ms")

        start_time = time.time()
        end_time = start_time + (self.duration_ms / 1000.0)
        sample_count = 0

        while time.time() < end_time:
            timestamp = time.time()
            value = GPIO.input(self.pin)
            self.samples.append({
                'time': timestamp,
                'value': value
            })
            sample_count += 1

        actual_duration = (time.time() - start_time) * 1000
        sample_rate = sample_count / (actual_duration / 1000)

        print(f"Captured {sample_count} samples")
        print(f"Actual duration: {actual_duration:.2f}ms")
        print(f"Sample rate: {sample_rate:.0f} Hz")

        return self.samples, sample_rate

    def capture_edge_detection(self, timeout_ms=1000):
        """
        Capture using edge detection (higher speed for changing signals)
        Estimated: up to 300 kHz for fast edges
        """
        print(f"\nCapturing GPIO {self.pin} (edge detection mode)...")
        print(f"Timeout: {timeout_ms}ms")

        self.samples = []
        last_value = GPIO.input(self.pin)
        edge_count = 0
        start_time = time.time()

        def edge_callback(channel):
            nonlocal edge_count, last_value
            timestamp = time.time()
            current_value = GPIO.input(self.pin)
            if current_value != last_value:
                self.samples.append({
                    'time': timestamp,
                    'value': current_value
                })
                last_value = current_value
                edge_count += 1

        # Add edge detection for both rising and falling
        GPIO.add_event_detect(
            self.pin,
            GPIO.BOTH,
            callback=edge_callback,
            bouncetime=0
        )

        # Wait for timeout
        time.sleep(timeout_ms / 1000.0)

        # Remove detection
        GPIO.remove_event_detect(self.pin)

        actual_duration = (time.time() - start_time) * 1000
        print(f"Captured {edge_count} edges")
        print(f"Actual duration: {actual_duration:.2f}ms")

        return self.samples

    def print_summary(self, samples, sample_rate=None):
        """Print captured data summary"""
        if not samples:
            print("No samples captured")
            return

        print("\n" + "=" * 50)
        print("DATA SUMMARY")
        print("=" * 50)

        # Calculate transitions
        transitions = 0
        high_count = 0
        low_count = 0

        for i, sample in enumerate(samples):
            if sample['value'] == 1:
                high_count += 1
            else:
                low_count += 1

            if i > 0 and sample['value'] != samples[i-1]['value']:
                transitions += 1

        print(f"Total samples: {len(samples)}")
        print(f"High samples: {high_count} ({high_count/len(samples)*100:.1f}%)")
        print(f"Low samples: {low_count} ({low_count/len(samples)*100:.1f}%)")
        print(f"Transitions: {transitions}")

        if sample_rate:
            print(f"Sample rate: {sample_rate:.0f} Hz")

        # Show first 20 samples
        print("\nFirst 20 samples:")
        print("Time (ms) | Value")
        print("-" * 20)
        base_time = samples[0]['time']
        for i, sample in enumerate(samples[:20]):
            relative_time = (sample['time'] - base_time) * 1000
            print(f"{relative_time:9.2f} | {sample['value']}")

        if len(samples) > 20:
            print(f"... and {len(samples) - 20} more")

    def save_csv(self, filename):
        """Save samples to CSV file"""
        if not self.samples:
            print("No samples to save")
            return

        base_time = self.samples[0]['time']
        with open(filename, 'w') as f:
            f.write("Time_ms,Value\n")
            for sample in self.samples:
                time_ms = (sample['time'] - base_time) * 1000
                f.write(f"{time_ms:.3f},{sample['value']}\n")
        print(f"\nSaved {len(self.samples)} samples to {filename}")

    def cleanup(self):
        GPIO.cleanup()


def main():
    print("=" * 60)
    print("Digital Oscilloscope - GPIO Sampling")
    print("=" * 60)

    PIN = 17
    DURATION_MS = 1000  # 1 second capture

    osc = DigitalOscilloscope(PIN, DURATION_MS)

    print(f"\nPin Configuration: GPIO {PIN}")
    print("Connect a signal source to this pin")
    print("Example: PWM output or square wave generator")
    print("\nPress Enter to start capture...")
    input()

    try:
        # Test polling mode
        samples, rate = osc.capture_polling()
        osc.print_summary(samples, rate)
        osc.save_csv('gpio_samples_polling.csv')

        print("\n" + "=" * 60)
        print("Press Enter to test edge detection mode...")
        input()

        # Test edge detection mode
        samples = osc.capture_edge_detection(timeout_ms=2000)
        osc.print_summary(samples)

    except KeyboardInterrupt:
        print("\n\nCapture interrupted")
    finally:
        osc.cleanup()
        print("\nGPIO cleaned up")

    print("\n" + "=" * 60)
    print("TIPS FOR BETTER PERFORMANCE:")
    print("=" * 60)
    print("""
For higher sampling rates, consider:

1. Use Pigpio library:
   sudo apt install pigpio
   pip3 install pigpio

2. For 1-2 MHz rates, use Pigpio DMA:
   - Preallocates buffers
   - Zero CPU overhead during capture
   - Requires signal triggering

3. For 5-10+ MHz rates, use C/C++:
   - Direct memory access to GPIO registers
   - No Python overhead
   - See: libgpiod

4. Kernel space solutions:
   - Custom kernel module
   -可以达到 50+ MHz
   - More complex to develop
""")


if __name__ == "__main__":
    main()
