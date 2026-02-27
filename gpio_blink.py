#!/usr/bin/env python3
"""
Simple GPIO Example - Blink LED
Demonstrates basic GPIO control
"""

import time
import sys

# Try different GPIO libraries
try:
    import RPi.GPIO as GPIO
    USE_GPIO = "RPi.GPIO"
except ImportError:
    print("RPi.GPIO not installed. Please install:")
    print("  sudo apt install python3-rpi.gpio")
    sys.exit(1)

# Configuration
LED_PIN = 17  # GPIO 17 (physical pin 11)

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

print("Simple GPIO Blink Example")
print(f"LED Pin: GPIO {LED_PIN}")
print("Blinking 10 times...")

try:
    for i in range(10):
        GPIO.output(LED_PIN, GPIO.HIGH)
        print(f"  {i+1}. ON")
        time.sleep(0.5)
        GPIO.output(LED_PIN, GPIO.LOW)
        print(f"  {i+1}. OFF")
        time.sleep(0.5)

    print("\nDone!")
finally:
    GPIO.cleanup()
    print("GPIO cleaned up")
