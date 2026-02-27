#!/usr/bin/env python3
"""
GPIO Digital Oscilloscope Sampling Test
Test maximum sampling rate using different methods
"""

import time
import RPi.GPIO as GPIO

# Setup
SAMPLE_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(SAMPLE_PIN, GPIO.IN)

# Test 1: Python polling (sysfs - slowest)
def test_sysfs_sampling():
    """Using sysfs via Python file operations - very slow"""
    print("Testing sysfs sampling rate...")
    count = 0
    start = time.time()
    duration = 1.0  # 1 second

    while time.time() - start < duration:
        with open('/sys/class/gpio/gpio17/value', 'r') as f:
            f.read()
        count += 1

    rate = count / duration
    print(f"Sysfs rate: {rate:.0f} Hz")
    return rate

# Test 2: RPi.GPIO polling
def test_rpi_gpio_polling():
    """Using RPi.GPIO.poll() - moderate speed"""
    print("\nTesting RPi.GPIO polling rate...")
    count = 0
    start = time.time()
    duration = 1.0

    while time.time() - start < duration:
        GPIO.input(SAMPLE_PIN)
        count += 1

    rate = count / duration
    print(f"RPi.GPIO polling rate: {rate:.0f} Hz")
    return rate

# Test 3: RPi.GPIO with edge detection
def test_rpi_gpio_edge_detection():
    """Using RPi.GPIO edge detection - fastest pure Python"""
    print("\nTesting RPi.GPIO edge detection rate...")

    count = 0

    def callback(channel):
        nonlocal count
        count += 1

    GPIO.add_event_detect(SAMPLE_PIN, GPIO.BOTH, callback=callback)

    # Generate test signal
    import threading
    GPIO.setup(18, GPIO.OUT)
    test_pin = 18

    def generate_signal():
        for _ in range(10000):
            GPIO.output(test_pin, GPIO.HIGH)
            GPIO.output(test_pin, GPIO.LOW)

    thread = threading.Thread(target=generate_signal)
    thread.start()
    time.sleep(0.5)
    GPIO.remove_event_detect(SAMPLE_PIN)

    print(f"Edge detection captured: {count} events in 0.5s")
    return count * 2

if __name__ == "__main__":
    print("=" * 50)
    print("Raspberry Pi 5 GPIO Sampling Rate Test")
    print("=" * 50)

    # Export GPIO for sysfs test
    with open('/sys/class/gpio/export', 'w') as f:
        f.write('17')
    time.sleep(0.1)
    with open('/sys/class/gpio/gpio17/direction', 'w') as f:
        f.write('in')

    # Run tests
    try:
        test_sysfs_sampling()
        test_rpi_gpio_polling()
        test_rpi_gpio_edge_detection()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        GPIO.cleanup()
        try:
            with open('/sys/class/gpio/unexport', 'w') as f:
                f.write('17')
        except:
            pass

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("  Sysfs: ~1-5 kHz (very slow, overhead)")
    print("  RPi.GPIO polling: ~50-150 kHz (Python overhead)")
    print("  Edge detection: ~100-300 kHz (hardware interrupt)")
    print("\n  For true high-speed oscilloscope:")
    print("    - Use C/C++ with direct memory access: 1-5 MHz")
    print("    - Use Pigpio DMA: ~1-10 MHz")
    print("    - Use kernel module: 10-50+ MHz")
    print("=" * 50)
