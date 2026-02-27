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

**测试接线说明**：
- 将信号发生器的输出端同时连接到所有4个通道：
  - GPIO5 (Pin 29) - 通道1
  - GPIO6 (Pin 31) - 通道2
  - GPIO23 (Pin 16) - 通道3
  - GPIO24 (Pin 18) - 通道4
- 地线 (GND) 连接到任何 GND 引脚
- 所有通道测试相同频率，请从外部信号发生器设置频率

### Software
```bash
# Install libgpiod development library
sudo apt update
sudo apt install libgpiod-dev

# Verify installation
ls /dev/gpiochip4  # Should exist (RP1 GPIO controller)
```

## Quick Start

### 重要说明：每次只测试一个频率

**所有测试程序已修改为每次只测试一个频率**，给您足够的时间设置信号发生器。

### 运行方式

#### 方式1：交互式选择（推荐）

```bash
# Stage 1: 多通道测试
sudo ./multi_channel_freq_test

# Stage 2: 压力测试
sudo ./high_freq_stress_test

# Stage 3: 延迟测试
sudo ./latency_test
```

程序会列出可用频率，您选择一个后，程序会提示您设置信号发生器，按回车后开始测试。

#### 方式2：命令行参数

```bash
# 列出可用频率
sudo ./multi_channel_freq_test --list

# 直接指定频率（可以用索引或频率值）
sudo ./multi_channel_freq_test 1        # 选择索引1（50 kHz）
sudo ./multi_channel_freq_test 10000     # 直接指定10 kHz

# Stage 2 压力测试
sudo ./high_freq_stress_test 1          # 选择200 kHz
sudo ./high_freq_stress_test 200000     # 直接指定200 kHz

# Stage 3 延迟测试
sudo ./latency_test 2                    # 选择1 MHz
sudo ./latency_test 1000000             # 直接指定1 MHz
```

### 测试流程

1. 运行测试程序
2. 选择要测试的频率（或通过命令行指定）
3. 程序显示提示："请设置信号发生器频率: XXX Hz"
4. 手动设置信号发生器到指定频率
5. 按回车键开始测试
6. 等待测试完成
7. 查看结果
8. 重复以上步骤测试下一个频率

### 测试频率清单

#### Stage 1: Multi-Channel Test (multi_channel_freq_test)
- [0] 10 kHz (baseline) - ✅ PASS
- [1] 20 kHz - ✅ PASS (最大 0.37%)
- [2] 30 kHz - ✅ PASS (最大 0.46%)
- [3] 35 kHz - ⏳ PENDING (优先级1，细化边界)
- [4] 40 kHz - ❌ FAIL (CH3: 10.78%)
- [5] 45 kHz - ⏳ PENDING
- [6] 50 kHz - ❌ FAIL
- [7] 75 kHz - ⏳ PENDING
- [8] 100 kHz - ⏳ PENDING

#### Stage 2: Stress Test (high_freq_stress_test)
- [0] 100 kHz (60秒)
- [1] 200 kHz (60秒)
- [2] 500 kHz (60秒)

#### Stage 3: Latency Test (latency_test)
- [0] 500 kHz
- [1] 750 kHz
- [2] 1 Msps (1000 kHz)

### 完整测试流程示例

**注意**：10-30 kHz 通过，40 kHz 失败（GPIO23问题），优先测试 35 kHz。

```bash
# Stage 1: 优先测试 35 kHz（细化边界）
sudo ./multi_channel_freq_test
# 选择 3，设置信号发生器为 35 kHz，按回车，等待结果
# 重点观察通道3 (GPIO23) 的表现

# 如果 35 kHz 通过，测试 45 kHz
sudo ./multi_channel_freq_test
# 选择 5，设置信号发生器为 45 kHz，按回车，等待结果

# 如果 35 kHz 失败，测试 37.5 kHz（需要添加频率）
# 或者单独测试 GPIO23 排除竞争问题

# Stage 2: 测试压力频率（如果 Stage 1 边界 > 30 kHz）
sudo ./high_freq_stress_test
# 选择 0，设置信号发生器为 100 kHz，按回车，等待60秒
sudo ./high_freq_stress_test
# 选择 1，设置信号发生器为 200 kHz，按回车，等待60秒
sudo ./high_freq_stress_test
# 选择 2，设置信号发生器为 500 kHz，按回车，等待60秒

# Stage 3: 测试延迟（如果 Stage 1 边界 > 100 kHz）
sudo ./latency_test
# 选择 0，设置信号发生器为 500 kHz，按回车
sudo ./latency_test
# 选择 1，设置信号发生器为 750 kHz，按回车
sudo ./latency_test
# 选择 2，设置信号发生器为 1000 kHz，按回车
```

---

## 详细说明

### Option 2: Run Individual Stages

#### Stage 1: Multi-Channel Test

```bash
# Compile
chmod +x compile_multi_channel_test.sh
./compile_multi_channel_test.sh

# Run - 交互式选择频率
sudo ./multi_channel_freq_test
```

**Expected Output**:
```
======================================================================
Multi-Channel High-Frequency GPIO Sampling Test
======================================================================
PRD Stage 1 Validation: 50-100 kHz range
Chip: /dev/gpiochip4 (RP1 controller)
Channels: 4 simultaneous (GPIO5/6/23/24)
Duration: 1 second per test

Available test frequencies:
  [0] 10 kHz (baseline) (10000 Hz)
  [1] 50 kHz (50000 Hz)
  [2] 75 kHz (75000 Hz)
  [3] 100 kHz (100000 Hz)

Select frequency to test (0-3): 1

=============================================================
请设置信号发生器频率: 50000 Hz (50 kHz)
=============================================================
所有4个通道连接到同一信号源:
  - GPIO5 (Pin 29)  通道1
  - GPIO6 (Pin 31)  通道2
  - GPIO23 (Pin 16) 通道3
  - GPIO24 (Pin 18) 通道4
=============================================================

按回车键开始测试 (或 Ctrl+C 取消)...

======================================================================
Testing at 50 kHz
======================================================================
Expected frequency: 50000 Hz
Expected edges: 100000 per channel

  Channel 1 (GPIO5, Pin 29):
    Total edges: 100000 (Rising: 50000, Falling: 50000)
    Measured: 50000.00 Hz (Expected: 50000 Hz)
    Edge loss: 0 (0.00%)
    ✓ EXCELLENT (< 1% loss)

  Channel 2 (GPIO6, Pin 31):
    Total edges: 99998 (Rising: 50000, Falling: 49998)
    Measured: 49999.00 Hz (Expected: 50000 Hz)
    Edge loss: 2 (0.002%)
    ✓ EXCELLENT (< 1% loss)

  ...

Frequency Test Result: ✓ PASS - All channels < 5% edge loss
```

#### Stage 2: Stress Test

```bash
# Compile
chmod +x compile_stress_test.sh
./compile_stress_test.sh

# Run - 交互式选择频率
sudo ./high_freq_stress_test
```

**Expected Output**:
```
======================================================================
High-Frequency Stress Test
======================================================================
PRD Stage 2 Validation: 100-500 kHz range
Duration: 60 seconds per frequency
Metrics: Edge loss, CPU usage, Memory, Stability

Available test frequencies:
  [0] 100 kHz (100000 Hz)
  [1] 200 kHz (200000 Hz)
  [2] 500 kHz (500000 Hz)

Select frequency to test (0-2): 1

=============================================================
请设置信号发生器频率: 200000 Hz (200 kHz)
=============================================================
所有4个通道连接到同一信号源:
  - GPIO5  通道1
  - GPIO6  通道2
  - GPIO23 通道3
  - GPIO24 通道4
=============================================================

按回车键开始测试 (或 Ctrl+C 取消)...

======================================================================
Stress Testing at 200 kHz
======================================================================
Expected frequency: 200000 Hz
Test duration: 60 seconds

  Progress: 600/600 samples (100.0%) - Edge rate: 399995/s

  Total test time: 60 seconds

  Channel 1 (GPIO5):
    Total edges: 23999700
    Total samples: 600
    Expected edge rate: 400000.0 edges/s
    Average edge rate: 399995 edges/s
    Edge rate range: 398500 - 401200 edges/s
    Average edge loss: 0.01%
    Average CPU usage: 58.3%
    Average memory: 14.56 MB
    Edge rate variation: 0.68%

    ✓ STABLE - Meets Stage 2 criteria

Stress Test Result: ✓ PASS - All channels meet Stage 2 criteria
```

#### Stage 3: Latency Test

```bash
# Compile
chmod +x compile_latency_test.sh
./compile_latency_test.sh

# Run - 交互式选择频率
sudo ./latency_test
```

**Expected Output**:
```
======================================================================
Trigger Latency Measurement Test
======================================================================
PRD Stage 3 Validation: Trigger-to-Display Latency
Target: < 100 ms from trigger to display
Channel: GPIO5 (Pin 29, /dev/gpiochip4 line 5)
Sample depth: 100k points per trigger
Simulated: Display rendering overhead (PyQtGraph)

Available test frequencies:
  [0] 500 kHz (500000 Hz)
  [1] 750 kHz (750000 Hz)
  [2] 1 Msps (1000000 Hz)

Select frequency to test (0-2): 2

=============================================================
请设置信号发生器频率: 1000000 Hz (1 Msps)
=============================================================
连接信号发生器到 GPIO5 (Pin 29)
=============================================================

按回车键开始测试 (或 Ctrl+C 取消)...

======================================================================
Testing at 1 Msps
======================================================================
Expected signal frequency: 1000000 Hz
Test duration: 5000 ms

  Trigger detected at 5678.123 ms
  Display ready at   5682.456 ms
  Total latency:     4.33 ms ✓ PASS (< 100 ms)
  (Render time: 2.10 ms)

  =============================================================
  Latency Summary for 1 Msps:
  =============================================================
  Trigger time:     5678.123 ms
  Display time:     5682.456 ms
  Total latency:    4.33 ms
  PRD requirement: < 100 ms
  Total edges:     20
  Sample depth:    100000 points

  Result: ✓ PASS - Latency < 100 ms

  Latency Breakdown:
  - Signal capture: < 1 ms (hardware edge detection)
  - Sample buffer:  50.00 ms (100k points at 1 Msps)
  - Data transfer:  1-2 ms (memory copy)
  - Processing:     1-2 ms (trigger evaluation)
  - Rendering:      2-5 ms (PyQtGraph + OpenGL)
  - Total:          4.33 ms
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
