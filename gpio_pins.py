#!/usr/bin/env python3
"""
Quick GPIO Pin Reference Viewer
Shows the 40-pin GPIO header layout with key information
"""

def print_gpio_diagram():
    """Print the GPIO pin diagram"""
    print("\n" + "=" * 60)
    print("Raspberry Pi 5 GPIO 40-Pin Header")
    print("=" * 60)
    print("""
      ┌─────────────────────────────────────────┐
      │  3.3V  (1)  (2)  5V     ⚠️ Don't mix!  │
      │  GPIO2 (3)  (4)  5V                      │
      │  GPIO3 (5)  (6)  GND                    │
      │  GPIO4 (7)  (8)  GPIO14    UART TX      │
      │    GND (9)  (10) GPIO15    UART RX      │
      │ GPIO17 (11) (12) GPIO18    PWM/PCM      │
      │ GPIO27 (13) (14) GND                    │
      │ GPIO22 (15) (16) GPIO23                 │
      │   3.3V (17) (18) GPIO24                 │
      │ GPIO10 (19) (20) GND       SPI MISO     │
      │  GPIO9 (21) (22) GPIO25    SPI MOSI     │
      │ GPIO11 (23) (24) GPIO8     SPI CLK      │
      │    GND (25) (26) GPIO7     SPI CE1      │
      │   ID_SD (27) (28) ID_SC    ⚠️ EEPROM!   │
      │  GPIO5 (29) (30) GND                    │
      │  GPIO6 (31) (32) GPIO12    PWM0         │
      │ GPIO13 (33) (34) GND       PWM1         │
      │ GPIO19 (35) (36) GPIO16    PCM FS       │
      │ GPIO26 (37) (38) GPIO20    PCM DIN      │
      │    GND (39) (40) GPIO21    PCM DOUT     │
      └─────────────────────────────────────────┘
    """)

def print_gpio_summary():
    """Print GPIO pin summary"""
    print("\n" + "=" * 60)
    print("GPIO PIN QUICK REFERENCE")
    print("=" * 60)

    sections = [
        ("Power Pins", [
            ("1, 2, 4, 17", "3.3V & 5V Power"),
            ("6, 9, 14, 20, 25, 30, 34, 39", "GND Ground pins"),
        ]),
        ("General Purpose GPIO (Recommended)", [
            ("4, 5, 6, 16, 17, 22, 23, 24, 25, 26, 27",
             "Safe to use, no special functions"),
        ]),
        ("I2C Bus", [
            ("3, 5", "I2C-1: SDA, SCL (1.8kΩ pull-up)"),
        ]),
        ("UART Serial", [
            ("8, 10", "UART0: TXD, RXD (console enabled)"),
        ]),
        ("SPI Bus", [
            ("19, 21, 23", "SPI0: MISO, MOSI, SCLK"),
            ("24, 26", "SPI0: CE0, CE1 (chip select)"),
        ]),
        ("PWM (Pulse Width Modulation)", [
            ("12, 18", "Hardware PWM / PCM audio"),
            ("32, 33", "Hardware PWM0, PWM1"),
        ]),
        ("EEPROM Identification", [
            ("27, 28", "ID_SD, ID_SC (HAT only - DO NOT USE)"),
        ]),
    ]

    for section_name, pins in sections:
        print(f"\n[{section_name}]")
        for pin, desc in pins:
            print(f"  Pin {pin:<40} : {desc}")

def print_warnings():
    """Print safety warnings"""
    print("\n" + "=" * 60)
    print("⚠️  CRITICAL SAFETY WARNINGS  ⚠️")
    print("=" * 60)
    print("""
1. NEVER connect 5V to GPIO pins!
   - GPIO pins are 3.3V logic level only
   - Connecting 5V will PERMANENTLY DAMAGE your Pi

2. Current limits:
   - Single GPIO: Max 16mA
   - All GPIO combined: Max 50mA
   - Use transistors/MOSFETs for high current loads

3. Pin conflicts:
   - Some pins have multiple functions (I2C/SPI/UART/PWM)
   - Check if a pin is already in use
   - Use 'cat /sys/kernel/debug/gpio' to check status

4. Special pins:
   - Pins 27, 28 (ID_SD, ID_SC) are for HAT EEPROM only
   - Do NOT connect anything to these pins

5. Signal integrity:
   - For high-speed signals (>100 kHz), use short cables
   - Proper grounding is essential
   - Consider noise and EMI interference
    """)

def print_oscilloscope_pins():
    """Print recommended pins for oscilloscope use"""
    print("\n" + "=" * 60)
    print("📊  RECOMMENDED PINS FOR OSCILLOSCOPE")
    print("=" * 60)
    print("""
Best pins for digital signal sampling:

Primary choices:
  - GPIO4  (Pin 7)   : Clean, no conflicts
  - GPIO5  (Pin 29)  : Clean, no conflicts
  - GPIO6  (Pin 31)  : Clean, no conflicts
  - GPIO17 (Pin 11)  : Clean, no conflicts (used in examples)

Secondary choices:
  - GPIO22 (Pin 15)
  - GPIO23 (Pin 16)
  - GPIO24 (Pin 18)
  - GPIO25 (Pin 22)
  - GPIO26 (Pin 37)
  - GPIO27 (Pin 13)

Before using any pin:
  1. Check if it's in use: cat /sys/kernel/debug/gpio
  2. Verify it's not configured for I2C/SPI/UART
  3. Disable conflicting functions in raspi-config if needed

Example usage:
  - Disable I2C: sudo raspi-config → Interface Options → I2C
  - Disable SPI: sudo raspi-config → Interface Options → SPI
  - Disable UART: sudo raspi-config → Interface Options → Serial
    """)

def main():
    print_gpio_diagram()
    print_gpio_summary()
    print_warnings()
    print_oscilloscope_pins()

    print("\n" + "=" * 60)
    print("For detailed information, see GPIO_README.md")
    print("=" * 60)

if __name__ == "__main__":
    main()
