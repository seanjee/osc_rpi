#!/usr/bin/env python3
"""
Install Full PIGPIO from Source
For Ubuntu 24.04 on Raspberry Pi 5
"""

import subprocess
import sys
import os

print("=" * 60)
print("Installing Full PIGPIO from Source")
print("=" * 60)
print("\nThis will install pigpiod daemon for DMA access")

def run_command(cmd, description):
    """Run a command and report result"""
    print(f"\n{description}")
    print(f"  Running: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, check=True,
                            capture_output=True, text=True)
        print(f"  ✓ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed")
        print(f"  Error: {e.stderr}")
        return False

# Check if running as root
if os.geteuid() != 0:
    print("\n⚠️  This script requires root privileges")
    print("   Please run with: sudo")
    sys.exit(1)

# Install dependencies
print("\n" + "=" * 60)
print("Step 1: Install Dependencies")
print("=" * 60)

success = run_command(
    "apt update",
    "Updating package list"
)

if success:
    success = run_command(
        "apt install -y python3-dev python3-setuptools build-essential",
        "Installing build dependencies"
    )

if not success:
    print("\n✗ Failed to install dependencies")
    sys.exit(1)

# Download and build pigpio
print("\n" + "=" * 60)
print("Step 2: Download and Build PIGPIO")
print("=" * 60)

import tempfile
import shutil

# Use temp directory
work_dir = "/tmp/pigpio_install"
if os.path.exists(work_dir):
    shutil.rmtree(work_dir)

os.makedirs(work_dir)
os.chdir(work_dir)

print(f"  Working directory: {work_dir}")

# Try multiple mirror sources
mirrors = [
    "https://ghproxy.com/https://github.com/joan2937/pigpio/archive/refs/tags/V79.tar.gz",
    "https://mirror.ghproxy.com/https://github.com/joan2937/pigpio/archive/refs/tags/V79.tar.gz",
    "https://github.com/joan2937/pigpio/archive/refs/tags/V79.tar.gz",
]

downloaded = False
for mirror_url in mirrors:
    print(f"\n  Trying mirror: {mirror_url.split('/')[2]}")
    success = run_command(
        f"wget -q {mirror_url}",
        f"Downloading PIGPIO V79"
    )
    if success:
        downloaded = True
        break
    print(f"  ✗ Failed, trying next mirror...")

if not downloaded:
    print("\n✗ All download mirrors failed")
    print("\nAlternative: You can manually download PIGPIO:")
    print("  1. Download from: https://github.com/joan2937/pigpio/releases")
    print("  2. Upload to: /tmp/pigpio_install/")
    print("  3. Run: tar -xzf V79.tar.gz && cd pigpio-79 && make && sudo make install")
    sys.exit(1)

success = True

if success:
    success = run_command(
        "tar -xzf V79.tar.gz",
        "Extracting archive"
    )

if success:
    os.chdir("pigpio-79")
    print(f"  Changed to: {os.getcwd()}")

    success = run_command(
        "make -j$(nproc)",
        "Building PIGPIO (this may take a minute)"
    )

# Install
if success:
    print("\n" + "=" * 60)
    print("Step 3: Install PIGPIO")
    print("=" * 60)

    success = run_command(
        "make install",
        "Installing binaries and libraries"
    )

    if success:
        # Install Python bindings
        print("\n  Installing Python bindings...")
        os.chdir("Python")
        success = run_command(
            "python3 setup.py install",
            "Installing Python pigpio module"
        )

# Create systemd service
if success:
    print("\n" + "=" * 60)
    print("Step 4: Create Systemd Service")
    print("=" * 60)

    service_content = """[Unit]
Description=Pigpio daemon
After=network.target

[Service]
ExecStart=/usr/local/bin/pigpiod -s
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

    try:
        with open("/etc/systemd/system/pigpiod.service", "w") as f:
            f.write(service_content)
        print("  ✓ Created /etc/systemd/system/pigpiod.service")
    except Exception as e:
        print(f"  ✗ Failed to create service file: {e}")
        success = False

# Start and enable service
if success:
    print("\n" + "=" * 60)
    print("Step 5: Start PIGPIOD Service")
    print("=" * 60)

    run_command(
        "systemctl daemon-reload",
        "Reloading systemd"
    )

    success = run_command(
        "systemctl start pigpiod",
        "Starting pigpiod service"
    )

    if success:
        success = run_command(
            "systemctl enable pigpiod",
            "Enabling pigpiod on boot"
        )

# Test
if success:
    print("\n" + "=" * 60)
    print("Step 6: Test Installation")
    print("=" * 60)

    result = subprocess.run(
        ["pigs", "hwver"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"  ✓ PIGPIOD working")
        print(f"  Hardware version: {result.stdout.strip()}")
    else:
        print(f"  ⚠ PIGPIOD test failed")
        print(f"    Error: {result.stderr}")

# Cleanup
os.chdir("/home/sean/osc_rpi")
print(f"\n  Cleaning up: {work_dir}")
shutil.rmtree(work_dir, ignore_errors=True)

# Summary
print("\n" + "=" * 60)
print("INSTALLATION COMPLETE")
print("=" * 60)

if success:
    print("\n✓ PIGPIO V79 installed from source")
    print("✓ PIGPIOD daemon running")
    print("✓ PIGPIOD enabled on boot")
    print("\nYou can now run:")
    print("  sudo python3 gpio_freq_dma.py")
else:
    print("\n✗ Installation failed")
    print("  Please check the error messages above")
    print("  and try again")

print("\n" + "=" * 60)
