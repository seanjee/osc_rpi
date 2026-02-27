# High-Frequency Testing Guide

## Overview

This directory contains test scripts for validating high-frequency GPIO sampling performance on Raspberry Pi 5, as required by the PRD.

## Test Structure

The testing follows the **3-stage validation plan** from the PRD:

### Stage 1: Multi-Channel Test (50-100 kHz)
- **Script**: `multi_channel_freq_test.cpp`
- **Purpose**: Verify 4-channel simultaneous sampling at 50, 75, and 100 kHz
- **Success Criteria**: < 5% edge loss, < 80% CPU usage
- **Duration**: ~1 minute

### Stage 2: Stress Test (100-500 kHz)
- **Script**: `high_freq_stress_test.cpp`
- **Purpose**: Test stability and performance at 100, 200, and 500 kHz
- **Success Criteria**: < 10% edge loss, < 90% CPU usage, stable performance
- **Duration**: ~5 minutes

### Stage 3: Latency Test (500 kHz - 1 Msps)
- **Script**: `latency_test.cpp`
- **Purpose**: Measure trigger-to-display latency (must be < 100 ms)
- **Success Criteria**: < 100 ms from trigger to display
- **Duration**: ~1 minute

## Prerequisites

### Hardware
- Raspberry Pi 5 with Ubuntu 24.04
- Signal generator capable of 10 kHz - 1 MHz output
- 3.3V amplitude square wave signals
- Connect to GPIO4 (Pin 7), GPIO5 (Pin 29), GPIO6 (Pin 31), GPIO7 (Pin 26)
- Ground connection to any GND pin

### Software
```bash
# Install libgpiod development library
sudo apt update
sudo apt install libgpiod-dev

# Verify installation
ls /dev/gpiochip4  # Should exist (RP1 GPIO controller)
```

## Quick Start

### Option 1: Run All Tests (Recommended)

```bash
# Make scripts executable
chmod +x run_high_freq_tests.sh *.sh

# Run all tests (requires sudo)
sudo ./run_high_freq_tests.sh

# Select option 4 to run all stages
```

### Option 2: Run Individual Stages

#### Stage 1: Multi-Channel Test

```bash
# Compile
chmod +x compile_multi_channel_test.sh
./compile_multi_channel_test.sh

# Run
sudo ./multi_channel_freq_test
```

**Expected Output**:
```
============================================================
Testing at 10 kHz (baseline)
============================================================
Expected frequency: 10000 Hz

  Channel 1 (GPIO5, Pin 29):
    Total edges: 20000 (Rising: 10001, Falling: 9999)
    Measured: 10000.00 Hz (Expected: 10000 Hz)
    Edge loss: 0 (0.00%)
    ✓ EXCELLENT (< 1% loss)

  ...

Frequency Test Result: ✓ PASS - All channels < 5% edge loss
```

#### Stage 2: Stress Test

```bash
# Compile
chmod +x compile_stress_test.sh
./compile_stress_test.sh

# Run
sudo ./high_freq_stress_test
```

**Expected Output**:
```
============================================================
Stress Testing at 100 kHz
============================================================
Expected frequency: 100000 Hz
Test duration: 60 seconds

  Progress: 100/600 samples (16.7%) - Edge rate: 199998/s
  ...

  Channel 1 (GPIO5):
    Total edges: 11999988
    Total samples: 600
    Average edge rate: 199998 edges/s
    Average edge loss: 0.01%
    Average CPU usage: 35.2%
    Average memory: 12.34 MB
    Edge rate variation: 1.23%
    ✓ STABLE - Meets Stage 2 criteria
```

#### Stage 3: Latency Test

```bash
# Compile
chmod +x compile_latency_test.sh
./compile_latency_test.sh

# Run
sudo ./latency_test
```

**Expected Output**:
```
============================================================
Testing at 500 kHz
============================================================
Expected signal frequency: 500000 Hz

  Trigger detected at 1234.567 ms
  Display ready at   1238.901 ms
  Total latency:     4.33 ms ✓ PASS (< 100 ms)
  (Render time: 2.10 ms)

  =============================================================
  Latency Summary for 500 kHz:
  =============================================================
  Total latency:    4.33 ms
  PRD requirement: < 100 ms

  Result: ✓ PASS - Latency < 100 ms
```

## Understanding the Results

### Success Criteria

| Stage | Frequency | Edge Loss | CPU Usage | Result |
|-------|-----------|-----------|-----------|--------|
| Stage 1 | 50-100 kHz | < 5% | < 80% | ✓ PASS |
| Stage 2 | 100-500 kHz | < 10% | < 90% | ✓ PASS |
| Stage 3 | 500 kHz-1 Msps | N/A | N/A | < 100 ms latency |

### What to Do If Tests Fail

#### Stage 1 Fails
- **Symptom**: Edge loss > 5% or channels fail to capture
- **Check**:
  1. Signal connections (all 4 GPIO pins)
  2. Signal amplitude (must be 3.3V)
  3. Signal frequency (use oscilloscope to verify)
  4. System load (run tests with minimal load)
- **Solution**: Fix connections, ensure good signal quality

#### Stage 2 Fails
- **Symptom**: Edge loss > 10%, CPU > 90%, or unstable performance
- **Check**:
  1. CPU usage (close other applications)
  2. Memory usage (should be < 100 MB)
  3. Signal quality at higher frequencies
- **Solutions**:
  1. Optimize sampling thread (reduce overhead)
  2. Use CPU affinity (`taskset` to bind to specific core)
  3. Consider reducing target to 200 kHz
  4. Implement memory mapping (more complex)

#### Stage 3 Fails
- **Symptom**: Latency >= 100 ms
- **Check**:
  1. Sample depth (try reducing to 50k points)
  2. GUI rendering (ensure PyQtGraph with OpenGL)
  3. System load (CPU, memory)
- **Solutions**:
  1. Reduce sample depth to 50k points
  2. Implement asynchronous PNG/CSV save
  3. Use GPU acceleration for rendering
  4. Relax latency requirement to 150 ms

## Performance Benchmark

Based on actual test results (10 kHz verified):

| Method | 10 kHz | 50 kHz | 100 kHz | 500 kHz | 1 Msps |
|--------|---------|---------|----------|----------|--------|
| **C++ Edge Events** | 100.01% | ⚠️ TBD | ⚠️ TBD | ⚠️ TBD | ⚠️ TBD |
| Python Polling | 23% | N/A | N/A | N/A | N/A |
| PIGPIO DMA | N/A | N/A | N/A | N/A | N/A |

**Legend**:
- ✓ Verified performance
- ⚠️ To Be Determined (needs testing)
- ✗ Not compatible/not achievable

## Decision Tree

```
Run Stage 1 Test
  ├─ Pass → Run Stage 2 Test
  └─ Fail → Fix connections, retry

Run Stage 2 Test
  ├─ Pass → Run Stage 3 Test
  ├─ Partial (200-500 kHz OK) → Deploy with 200 kHz max
  └─ Fail → Consider:
      ├─ Lower target to 100 ksps
      ├─ Memory mapping (complex)
      └─ Deploy with 100 kHz max

Run Stage 3 Test
  ├─ Pass (≤ 100 ms) → Deploy with 1 Msps ✓
  ├─ Pass (100-150 ms) → Deploy with 1 Msps, relaxed requirement
  └─ Fail → Consider:
      ├─ Reduce sample depth to 50k
      ├─ Optimize GUI rendering
      ├─ Deploy with 500 kHz max
      └─ Relax latency requirement
```

## Troubleshooting

### Permission Denied
```
[Errno 13] Permission denied
```
**Solution**: Always run with `sudo`

### GPIO Not Found
```
Error: /dev/gpiochip4 not found
```
**Solution**: Check RP1 GPIO controller is loaded:
```bash
ls /dev/gpiochip*
# Should see /dev/gpiochip4
```

### Compilation Errors
```
fatal error: gpiod.hpp: No such file or directory
```
**Solution**: Install libgpiod-dev:
```bash
sudo apt install libgpiod-dev
```

### No Events Captured
```
Total edges: 0
```
**Solution**:
1. Check signal connections
2. Verify signal is connected to correct GPIO pins
3. Check signal amplitude (must be 3.3V)
4. Verify signal is present with oscilloscope

## Advanced Usage

### CPU Affinity Optimization
Bind sampling threads to specific CPU cores:

```bash
# Run test on CPU core 2 only
taskset -c 2 sudo ./high_freq_stress_test
```

### Real-time Kernel (Optional)
For better performance, install PREEMPT_RT kernel:
```bash
# WARNING: This is experimental!
sudo apt install linux-image-rt-arm64
# Reboot
```

### Memory Mapping Alternative
If C++ edge events don't meet 1 Msps target, consider memory mapping:
- Directly map `/dev/mem` to user space
- Read RP1 GPIO registers directly
- Complex but can achieve 1-5 Msps
- See PRD Section 7.6 for details

## Test Output Files

All tests output results to stdout. To save results:

```bash
# Save Stage 1 results
sudo ./multi_channel_freq_test > stage1_results.txt 2>&1

# Save all tests with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
sudo ./run_high_freq_tests.sh > all_tests_$TIMESTAMP.log 2>&1
```

## Next Steps

### If All Tests Pass
✓ Proceed to oscilloscope development
✓ Use `freq_measure_cpp.cpp` as sampling thread template
✓ Implement GUI with PyQt6 + PyQtGraph
✓ Deploy with 1 Msps max sampling rate

### If Some Tests Fail
1. Review failure reasons above
2. Consider alternative solutions from PRD:
   - **Option A**: Lower target (100 ksps)
   - **Option B**: Memory mapping (complex)
   - **Option C**: External hardware (FPGA/ADC)
3. Update PRD with actual achievable performance
4. Proceed with adjusted requirements

## References

- **PRD**: `PRD.md` (Sections 7.6, 7.7, 7.8)
- **GPIO Documentation**: `GPIO_README.md`
- **Frequency Test Summary**: `FREQUENCY_TEST_SUMMARY.md`
- **libgpiod API**: https://libgpiod.readthedocs.io/
- **RP1 Datasheet**: https://datasheets.raspberrypi.com/rp1/rp1-peripherals.pdf

## Support

For issues or questions:
1. Check this README first
2. Review PRD lessons learned (Section 7)
3. Check test output for specific error messages
4. Verify hardware connections with oscilloscope

---

**Status**: Ready for testing
**Last Updated**: 2026-02-27
**Version**: 1.0
