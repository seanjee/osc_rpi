# 频率测试跟踪记录

## 测试环境
- 测试日期：2025-02-26
- 硬件：Raspberry Pi 5, Ubuntu 24.04
- GPIO 接口：/dev/gpiochip4 (RP1 controller)
- 通道配置：
  - CH1: GPIO5 (Pin 29)
  - CH2: GPIO6 (Pin 31)
  - CH3: GPIO23 (Pin 16)
  - CH4: GPIO24 (Pin 18)
- 测试方法：libgpiod C++ edge events

## Stage 1: 频率边界测试 (10-100 kHz)

### 测试通过标准
- 边沿丢失率 < 5%
- 频率误差 < 1%
- 所有4个通道同步测试

### 测试结果

| 频率 | 日期 | 边沿丢失率 | CPU使用率 | 状态 | 备注 |
|------|------|-----------|----------|------|------|
| 10 kHz | 2025-02-26 | <0.01% | - | ✅ PASS | 基准测试，20,002边沿/秒，100.01%准确度 |
| 20 kHz | 2025-02-26 | 0.37% | - | ✅ PASS | 所有通道 <1%，CH3最高(0.37%) |
| 30 kHz | 2025-02-26 | 0.46% | - | ✅ PASS | 所有通道 <1%，CH2最高(0.46%) |
| 40 kHz | 2025-02-26 | 10.78% | - | ❌ FAIL | CH3失败(10.78%)，其他通道<5% |
| 50 kHz | 2025-02-26 | >5% | - | ❌ FAIL | 边沿丢失超过阈值 |
| 75 kHz | | | | ⏳ PENDING | 待测试 |
| 100 kHz | | | | ⏳ PENDING | 待测试 |

### 通道性能分析（40 kHz 测试）

| 通道 | GPIO | Pin | 边沿丢失率 | 实测频率 | 状态 |
|------|------|-----|-----------|---------|------|
| CH1 | GPIO5 | 29 | 4.93% | 38,028 Hz | ⚠ GOOD |
| CH2 | GPIO6 | 31 | 4.65% | 38,139 Hz | ⚠ GOOD |
| CH3 | GPIO23 | 16 | 10.78% | 35,686 Hz | ✗ POOR |
| CH4 | GPIO24 | 18 | 3.11% | 38,757 Hz | ✓ EXCELLENT |

**关键发现**：
- 通道3 (GPIO23, Pin 16) 性能最差，40 kHz 时边沿丢失率 10.78%
- 通道1、2、4 性能接近，40 kHz 时 <5%
- 可能原因：
  - GPIO23 硬件问题
  - 引脚布局/干扰问题
  - 特定GPIO线路的内核调度优先级不同

### 测试命令

```bash
# 测试 10 kHz (基准)
sudo ./multi_channel_freq_test 0

# 测试 20 kHz (通过)
sudo ./multi_channel_freq_test 1

# 测试 30 kHz (通过)
sudo ./multi_channel_freq_test 2

# 测试 35 kHz (优先级1 - 细化边界)
sudo ./multi_channel_freq_test 3

# 测试 40 kHz (失败 - CH3: 10.78%)
sudo ./multi_channel_freq_test 4

# 测试 45 kHz (待测试)
sudo ./multi_channel_freq_test 5

# 测试 50 kHz (失败)
sudo ./multi_channel_freq_test 6

# 测试 75 kHz (待测试)
sudo ./multi_channel_freq_test 7

# 测试 100 kHz (待测试)
sudo ./multi_channel_freq_test 8
```

## Stage 2: 压力测试 (100-500 kHz)

### 测试通过标准
- 边沿丢失率 < 10%
- CPU 使用率 < 90%
- 性能稳定（波动 < 20%）

### 测试结果

| 频率 | 日期 | 边沿丢失率 | CPU使用率 | 状态 | 备注 |
|------|------|-----------|----------|------|------|
| 100 kHz | | | | ⏳ PENDING | 60秒压力测试 |
| 200 kHz | | | | ⏳ PENDING | 60秒压力测试 |
| 500 kHz | | | | ⏳ PENDING | 60秒压力测试 |

### 测试命令

```bash
# 测试 100 kHz (60秒)
sudo ./high_freq_stress_test 0

# 测试 200 kHz (60秒)
sudo ./high_freq_stress_test 1

# 测试 500 kHz (60秒)
sudo ./high_freq_stress_test 2
```

## Stage 3: 延迟测试 (500 kHz - 1 Msps)

### 测试通过标准
- 触发到显示延迟 < 100 ms

### 测试结果

| 频率 | 日期 | 延迟 (ms) | 状态 | 备注 |
|------|------|----------|------|------|
| 500 kHz | | | ⏳ PENDING | 待测试 |
| 750 kHz | | | ⏳ PENDING | 待测试 |
| 1 Msps | | | ⏳ PENDING | 待测试 |

### 测试命令

```bash
# 测试 500 kHz
sudo ./latency_test 0

# 测试 750 kHz
sudo ./latency_test 1

# 测试 1 Msps
sudo ./latency_test 2
```

## 关键发现

### 已知问题
1. **40 kHz 测试失败**：通道3 边沿丢失率 10.78%，超过 5% 阈值
2. **通道性能不均匀**：通道3 (GPIO23) 性能明显低于其他通道
   - CH3: 10.78% 丢失率
   - CH1: 4.93% 丢失率
   - CH2: 4.65% 丢失率
   - CH4: 3.11% 丢失率

3. **边界频率**：
   - 30 kHz: 所有通道通过 (最大 0.46%)
   - 40 kHz: 通道3失败 (10.78%)
   - 边界在 30-40 kHz 之间

### 假设
1. **GPIO23 硬件问题**：
   - 可能 GPIO23 (Pin 16) 的物理连接有问题
   - 可能该引脚存在信号干扰
   - 可能是该 GPIO 线路的内核驱动或中断处理有问题

2. **系统资源竞争**：
   - 不同 GPIO 线路可能由不同的 CPU 核心处理
   - 某些核心可能负载更高，导致处理延迟

3. **libgpiod 事件缓冲区**：
   - 可能某些 GPIO 线路的缓冲区更快被填满
   - 可能需要调整内核参数

### 待验证
1. ✅ 20 kHz 通过 (最大 0.37%)
2. ✅ 30 kHz 通过 (最大 0.46%)
3. ❌ 40 kHz 失败 (CH3: 10.78%)
4. ⏳ 35 kHz 待测试（细化边界）
5. ⏳ 45 kHz 待测试（验证边界稳定性）
6. ⏳ 单独测试 GPIO23（排除硬件问题）

## 下一步行动

1. **优先级 1**：测试 35 kHz
   - 确定边界是否在 35 kHz 左右
   - 观察通道3的表现

2. **优先级 2**：单独测试 GPIO23
   - 使用 freq_measure_cpp.cpp 只测试 GPIO23
   - 排除多通道竞争问题
   - 确认是否是硬件或引脚问题

3. **优先级 3**：交换通道测试
   - 将信号源重新连接，交换GPIO23和其他引脚
   - 验证问题是否跟随GPIO23还是物理位置
   - 确认是否是引脚布局或干扰问题

4. **优先级 4**：检查系统资源
   - 运行 top/htop 监控 CPU 核心负载
   - 检查中断分布（/proc/interrupts）
   - 测试时关闭其他程序

5. **优先级 5**：如果 35 kHz 通过，测试 37.5 kHz, 45 kHz
   - 进一步细化边界
   - 找到通道3的极限频率

6. **优先级 6**：考虑 GPIO23 替代方案
   - 如果 GPIO23 确实有问题，考虑使用其他 GPIO 引脚
   - 更新 PRD 和配置文件

## 备注

- 所有测试需要 sudo 权限
- 所有4个通道必须连接到同一信号源
- 测试前确保信号发生器已正确设置
- 建议在最小系统负载下进行测试

## GPIO23 单独测试

为了排除多通道竞争问题，单独测试 GPIO23：

```bash
# 修改 freq_measure_cpp.cpp 使用 GPIO23
# 将 line_offset 从 5 改为 23

# 编译和运行
./compile_freq_cpp.sh
sudo ./freq_measure_cpp
```

然后对比：
1. GPIO5 (原基准) 的表现
2. GPIO23 (问题引脚) 的表现

如果单独测试 GPIO23 仍然表现差，说明是硬件/引脚问题。
如果单独测试 GPIO23 表现正常，说明是多通道竞争问题。
