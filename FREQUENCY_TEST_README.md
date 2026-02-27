# GPIO 频率测试说明

## 当前环境限制

由于测试环境的限制，**无法直接访问 GPIO 引脚**进行实际测量。限制如下：

1. **缺少 GPIO 库**
   - 未安装 `python3-rpi.gpio`
   - 未安装 `python3-pigpio`
   - 没有 pip 模块来安装依赖

2. **缺少权限**
   - 无法使用 `sudo` 命令
   - 无法访问 `/dev/gpiomem`
   - 无法访问 `/dev/mem`

3. **缺少系统工具**
   - 无法运行 `apt-get` 或 `apt-cache`
   - 无法查询或安装软件包

## 如何在真实的 Raspberry Pi 5 上运行测试

### 步骤 1: 安装必要的库

在 Raspberry Pi 5 的终端中运行：

```bash
# 更新软件包列表
sudo apt update

# 安装 GPIO 库
sudo apt install python3-rpi.gpio python3-pigpio

# 启用 pigpio 守护进程
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

### 步骤 2: 连接信号

1. **连接方波信号源**到 **GPIO5（物理针脚 29）**
   - 信号幅度：3.3V
   - 信号类型：方波
   - 频率范围：待测量

2. **引脚映射参考**：
   ```
   GPIO5 = 物理针脚 29
   GND  = 物理针脚 30（或其他 GND 针脚）
   ```

3. **接线示意图**：
   ```
   信号源正极 → GPIO5 (Pin 29)
   信号源地   → GND   (Pin 30 或 34 等)
   ```

### 步骤 3: 运行测试

```bash
# 进入项目目录
cd /home/sean/osc_rpi

# 使用 sudo 运行（pigpio 需要 root 权限）
sudo python3 gpio_frequency_test.py
```

## 预期输出

测试成功时会显示类似以下输出：

```
============================================================
GPIO Frequency Measurement Tool
For Raspberry Pi 5
============================================================
GPIO Pin: 5 (Physical Pin 29)
Target Sample Rate: 1 Msps (1,000,000 samples/sec)
Signal Amplitude: 3.3V
============================================================
✓ Using pigpio library
✓ GPIO 5 initialized (pigpio)

Measuring frequency at ~1 Msps for 100ms...
Using edge detection method for accuracy...

============================================================
FREQUENCY MEASUREMENT RESULTS
============================================================
Detection Method: Edge Detection (pigpio)
GPIO Pin: 5 (Physical Pin 29)
Total Edges Detected: 200
Rising Edges: 100
Falling Edges: 100

------------------------------------------------------------
Frequency Analysis:
------------------------------------------------------------
  Average Period: 100.00 μs
  Frequency: 10000.00 Hz
  Period Range: 99.95 μs - 100.05 μs
  Period Std Dev: 0.03 μs

Duty Cycle Analysis:
------------------------------------------------------------
  Avg High Time: 50.00 μs
  Avg Low Time: 50.00 μs
  Duty Cycle: 50.0%
  Expected for 3.3V square wave: ~50%

============================================================

============================================================
TEST COMPLETE
============================================================
✓ Successfully measured signal frequency
  Frequency: 10000.00 Hz
  This is a 10.00 kHz signal
  Signal Jitter: 0.03%
  ✓ Signal quality: Excellent

✓ GPIO cleaned up
```

## 工作原理

### 采样方法

1. **Pigpio 方法**（推荐，1-5 Msps）：
   - 使用 pigpio 的 DMA 采样
   - 通过边沿检测计算频率
   - 精度高，适合测量频率

2. **RPi.GPIO 方法**（备用，~300 ksps）：
   - 使用高速轮询
   - CPU 开销较大
   - 精度稍低

### 频率计算

1. **检测上升沿**：信号从 0 变为 1
2. **计算周期**：相邻上升沿之间的时间差
3. **计算频率**：频率 = 1 / 平均周期

### 信号质量评估

- **抖动（Jitter）**：周期的标准偏差
  - < 1%：优秀
  - < 5%：良好
  - > 5%：一般

- **占空比**：高电平时间 / 周期 × 100%
  - 理想方波：50%
  - 允许范围：40%-60%

## 常见问题

### Q: 测试显示 "Not enough edges detected"

**可能原因**：
1. 信号未连接到 GPIO5
2. 信号幅度太低（需要 > 1.5V）
3. 信号频率太低（测量时间不够）

**解决方案**：
- 检查接线
- 增加信号幅度到 3.3V
- 增加测量时间（修改 `duration_ms` 参数）

### Q: 显示 "No GPIO library found"

**解决方案**：
```bash
sudo apt install python3-rpi.gpio python3-pigpio
```

### Q: 显示 "Failed to connect to pigpio daemon"

**解决方案**：
```bash
sudo systemctl start pigpiod
```

### Q: 测量结果不准确

**可能原因**：
- 信号质量差（噪声、失真）
- 测量时间太短
- 系统负载高

**解决方案**：
- 改善信号源质量
- 增加测量时间
- 关闭其他程序

## 性能指标

| 方法 | 最大采样率 | CPU 占用 | 精度 | 推荐度 |
|------|-----------|---------|------|--------|
| Pigpio DMA | 1-5 Msps | 低 | ±0.1% | ⭐⭐⭐⭐⭐ |
| Pigpio 边沿检测 | ~500 ksps | 低 | ±0.5% | ⭐⭐⭐⭐ |
| RPi.GPIO 轮询 | ~300 ksps | 高 | ±1% | ⭐⭐⭐ |

## 下一步

测试成功后：

1. **记录测量结果**：记下信号的实际频率
2. **验证示波器性能**：确认 1 Msps 采样率可用
3. **开始示波器开发**：基于验证的硬件进行开发
4. **调整 PRD 参数**：根据实际性能优化 PRD 规格

## 示波器开发准备

测试通过后，示波器开发将使用：

- **采样库**：Pigpio（DMA 模式）
- **采样率**：1 Msps（验证可用）
- **输入引脚**：GPIO5（已验证可读取）
- **频率范围**：根据实际测量结果确定

## 相关文件

- `gpio_frequency_test.py` - 频率测量工具
- `GPIO_README.md` - GPIO 操作指南
- `config/osc_config.yaml` - 示波器配置文件
- `PRD.md` - 产品需求文档
