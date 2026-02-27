# GPIO23 性能问题排查指南

## 问题描述

在 40 kHz 测试中，GPIO23 (Pin 16, 通道3) 的性能明显低于其他通道：

| 通道 | GPIO | Pin | 边沿丢失率 | 状态 |
|------|------|-----|-----------|------|
| CH1 | GPIO5 | 29 | 4.93% | ⚠ GOOD |
| CH2 | GPIO6 | 31 | 4.65% | ⚠ GOOD |
| **CH3** | **GPIO23** | **16** | **10.78%** | **✗ POOR** |
| CH4 | GPIO24 | 18 | 3.11% | ✓ EXCELLENT |

## 可能原因

### 1. 硬件问题
- GPIO23 物理引脚损坏
- 连接线质量差或接触不良
- 信号干扰（Pin 16 位于中间位置）

### 2. 内核/驱动问题
- GPIO23 由负载更高的 CPU 核心处理
- 中断处理优先级不同
- libgpiod 对该 GPIO 线路的缓冲区配置不同

### 3. 多通道竞争
- 4 个通道同时采集导致某些通道性能下降
- GPIO23 可能受到其他通道的影响

## 排查步骤

### 步骤 1：单独测试 GPIO23

修改 `freq_measure_cpp.cpp`，将 GPIO 从 5 改为 23：

```bash
# 查看当前配置
head -30 freq_measure_cpp.cpp | grep -E "(chip_path|line_offset)"
```

修改方式：
```cpp
// 将这两行：
static const char* const chip_path = "/dev/gpiochip4";
static const unsigned int line_offset = 5;

// 改为：
static const char* const chip_path = "/dev/gpiochip4";
static const unsigned int line_offset = 23;
```

编译和测试：
```bash
# 编译
./compile_freq_cpp.sh

# 测试 40 kHz（单独测试 GPIO23）
# 设置信号发生器为 40 kHz
sudo ./freq_measure_cpp
```

**结果判断**：
- 如果单独测试 GPIO23 性能正常（<5% 丢失率）→ 多通道竞争问题
- 如果单独测试 GPIO23 仍然性能差（>5% 丢失率）→ 硬件或驱动问题

### 步骤 2：交换通道测试

将信号源重新连接，交换 GPIO23 和其他引脚：

**测试 A**：将信号源接到 GPIO5 (Pin 29)，其他通道断开
```bash
# 修改 freq_measure_cpp.cpp 使用 GPIO5 (line_offset = 5)
./compile_freq_cpp.sh
sudo ./freq_measure_cpp
# 测试 40 kHz
```

**测试 B**：将信号源接到 GPIO23 (Pin 16)，其他通道断开
```bash
# 修改 freq_measure_cpp.cpp 使用 GPIO23 (line_offset = 23)
./compile_freq_cpp.sh
sudo ./freq_measure_cpp
# 测试 40 kHz
```

**结果判断**：
- 如果 GPIO5 和 GPIO23 单独测试性能都正常 → 多通道竞争问题
- 如果 GPIO23 单独测试仍然差 → 硬件或驱动问题

### 步骤 3：检查中断分布

```bash
# 查看 GPIO 相关中断
cat /proc/interrupts | grep -i gpio

# 在测试期间实时监控
watch -n 1 'cat /proc/interrupts | grep -i gpio'
```

在后台运行：
```bash
# 运行多通道测试
sudo ./multi_channel_freq_test 4

# 同时在另一个终端监控中断
watch -n 0.1 'cat /proc/interrupts | grep -i gpio'
```

**观察要点**：
- 哪个 CPU 核心处理 GPIO23 的中断
- GPIO23 的中断数量是否明显少于其他 GPIO
- 是否有中断丢失或延迟

### 步骤 4：检查系统负载

```bash
# 在测试期间监控 CPU 核心负载
top -H

# 或者使用 htop
htop
```

在后台运行测试，观察各个 CPU 核心的负载情况。

### 步骤 5：测试不同配置

#### 测试 A：减少通道数量

修改 `multi_channel_freq_test.cpp`，只使用 2 个通道：
```cpp
// 将：
#define MAX_CHANNELS 4

// 改为：
#define MAX_CHANNELS 2

// 并修改 channels 数组，只保留 GPIO5 和 GPIO23
ChannelConfig channels[MAX_CHANNELS] = {
    {"/dev/gpiochip4", 5,  "GPIO5",  29},
    {"/dev/gpiochip4", 23, "GPIO23", 16}
};
```

重新编译和测试：
```bash
./compile_multi_channel_test.sh
sudo ./multi_channel_freq_test 4  # 测试 40 kHz
```

观察 GPIO23 的性能是否改善。

#### 测试 B：使用 CPU 亲和性

修改测试程序，将 GPIO23 绑定到专用 CPU 核心。

### 步骤 6：检查物理连接

```bash
# 检查 GPIO23 的状态（多通道测试前）
sudo gpiodetect
sudo gpioinfo | grep -A 5 "23"

# 检查 GPIO23 是否被其他程序占用
sudo lsof /dev/gpiochip4

# 检查引脚电压（需要万用表）
# GPIO23 (Pin 16) 应该有 0-3.3V 的方波信号
```

## 解决方案

### 方案 1：更换 GPIO 引脚（如果 GPIO23 确实有问题）

如果确认 GPIO23 有问题，建议更换为其他 GPIO 引脚：

候选引脚：
- GPIO17 (Pin 11)
- GPIO18 (Pin 12)
- GPIO27 (Pin 13)
- GPIO22 (Pin 15)

需要更新：
1. `config/osc_config.yaml`
2. `PRD.md`
3. `multi_channel_freq_test.cpp`
4. `high_freq_stress_test.cpp`
5. `TEST_WIRING.md`

### 方案 2：优化系统参数（如果多通道竞争问题）

```bash
# 调整内核调度参数
echo 100000 | sudo tee /proc/sys/kernel/sched_rt_period_us
echo 95000 | sudo tee /proc/sys/kernel/sched_rt_runtime_us

# 提高 GPIO 中断优先级（需要修改内核）

# 使用 CPU 隔离
# 编辑 /boot/firmware/config.txt 添加：
# isolate_cpus=1,2,3
```

### 方案 3：调整测试频率（如果硬件限制）

如果 GPIO23 无法达到其他通道的性能，降低测试频率：
- 在 30 kHz 下所有通道都通过
- 限制示波器的最大采样频率为 30 kHz
- 重新评估 PRD 要求

## 下一步行动

1. **立即执行**：单独测试 GPIO23（步骤 1）
   - 判断是否硬件问题还是多通道竞争

2. **根据步骤 1 结果**：
   - 如果硬件问题：执行步骤 6（更换引脚）
   - 如果多通道竞争：执行步骤 2-5（优化系统）

3. **最终决策**：
   - 如果无法解决：更换 GPIO23 引脚
   - 如果可以解决：应用到所有测试

## 记录测试结果

请在 `TEST_TRACKING.md` 中记录所有排查步骤的结果：

```markdown
## GPIO23 排查结果

### 单独测试 40 kHz
- 日期：
- 结果：
- 边沿丢失率：

### 交换测试
- GPIO5 单独测试：
- GPIO23 单独测试：

### 中断分布
- GPIO23 中断数量：
- 处理 CPU 核心：

### 2 通道测试
- GPIO23 性能：

### 结论
- 问题原因：
- 解决方案：
```
