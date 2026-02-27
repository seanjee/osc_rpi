# Raspberry Pi 5 GPIO 操作指南

## 硬件信息
- 设备: Raspberry Pi 5 Model B Rev 1.1
- CPU: 2400 MHz
- GPIO: 4 个 GPIO 芯片，共 111 个 GPIO 引脚

## GPIO 采样频率上限

### Python 纯轮询方案
| 方法 | 采样频率 | 说明 |
|------|---------|------|
| sysfs 文件操作 | ~1-5 kHz | 最慢，不推荐 |
| RPi.GPIO 轮询 | ~50-150 kHz | 适合低速信号 |
| RPi.GPIO 边沿检测 | ~100-300 kHz | 适合边沿触发 |

### 高性能方案
| 方法 | 采样频率 | 复杂度 |
|------|---------|--------|
| Pigpio (Python) | ~200-500 kHz | 中等 |
| Pigpio DMA | ~1-2 MHz | 中等 |
| C/C++ 直接内存 | ~1-5 MHz | 高 |
| 内核模块 | 10-50+ MHz | 极高 |

## 安装驱动

### 基础安装
```bash
sudo apt update
sudo apt install python3-rpi.gpio python3-gpiozero
```

### 高性能方案（可选）
```bash
sudo apt install pigpio
```

## 脚本使用

### 1. 快速查看 GPIO 引脚图
```bash
python3 gpio_pins.py
```
显示 40 针 GPIO 排针布局、引脚功能分类、安全警告和示波器推荐引脚。

### 2. 检查 GPIO 状态
```bash
python3 gpio_status.py
```
显示硬件信息、可用 GPIO 芯片和已安装的库。

### 3. LED 闪烁示例
```bash
sudo python3 gpio_blink.py
```
需要 root 权限，在 GPIO 17 上闪烁 LED。

### 4. 数字示波器采样
```bash
sudo python3 digital_oscilloscope.py
```
捕获 GPIO 信号并保存到 CSV 文件。

## GPIO 引脚映射

Raspberry Pi 5 使用新的 RP1 GPIO 控制器，常用引脚：

- GPIO 0-27: 标准 40 针接口引脚
- GPIO 17 (物理针脚 11): 示例中使用

## GPIO 引脚图（40 针排针）

```
      ┌─────────────────────────────────────┐
      │  3.3V  (1)  (2)  5V               │
      │  GPIO2 (3)  (4)  5V               │
      │  GPIO3 (5)  (6)  GND              │
      │  GPIO4 (7)  (8)  GPIO14           │
      │    GND (9)  (10) GPIO15           │
      │ GPIO17 (11) (12) GPIO18           │
      │ GPIO27 (13) (14) GND              │
      │ GPIO22 (15) (16) GPIO23           │
      │   3.3V (17) (18) GPIO24           │
      │ GPIO10 (19) (20) GND              │
      │  GPIO9 (21) (22) GPIO25           │
      │ GPIO11 (23) (24) GPIO8            │
      │    GND (25) (26) GPIO7            │
      │   ID_SD (27) (28) ID_SC           │
      │  GPIO5 (29) (30) GND              │
      │  GPIO6 (31) (32) GPIO12           │
      │ GPIO13 (33) (34) GND              │
      │ GPIO19 (35) (36) GPIO16           │
      │ GPIO26 (37) (38) GPIO20           │
│    GND (39) (40) GPIO21           │
      └─────────────────────────────────────┘
```

### 引脚详细功能表

| 物理针脚 | GPIO 编号 | 功能 | 注意事项 |
|---------|-----------|------|---------|
| 1 | - | 3.3V 电源 | 最大输出 500mA |
| 2 | - | 5V 电源 | 直接来自 USB 输入 |
| 3 | GPIO2 | I2C SDA1 | 默认启用了上拉电阻，1.8kΩ |
| 4 | - | 5V 电源 | 直接来自 USB 输入 |
| 5 | GPIO3 | I2C SCL1 | 默认启用了上拉电阻，1.8kΩ |
| 6 | - | GND | 接地 |
| 7 | GPIO4 | GPIO 通用 | 推荐用于数字输入/输出 |
| 8 | GPIO14 | UART0 TXD | 串口发送，默认启用 |
| 9 | - | GND | 接地 |
| 10 | GPIO15 | UART0 RXD | 串口接收，默认启用 |
| 11 | GPIO17 | GPIO 通用 | 推荐用于数字输入/输出 |
| 12 | GPIO18 | PWM/PCM | 可用作 PWM 或 PCM 音频 |
| 13 | GPIO27 | GPIO 通用 | 推荐用于数字输入/输出 |
| 14 | - | GND | 接地 |
| 15 | GPIO22 | GPIO 通用 | 推荐用于数字输入/输出 |
| 16 | GPIO23 | GPIO 通用 | 推荐用于数字输入/输出 |
| 17 | - | 3.3V 电源 | 最大输出 500mA |
| 18 | GPIO24 | GPIO 通用 | 推荐用于数字输入/输出 |
| 19 | GPIO10 | SPI0 MOSI | SPI 主机输出从机输入 |
| 20 | - | GND | 接地 |
| 21 | GPIO9 | SPI0 MISO | SPI 主机输入从机输出 |
| 22 | GPIO25 | GPIO 通用 | 推荐用于数字输入/输出 |
| 23 | GPIO11 | SPI0 SCLK | SPI 时钟信号 |
| 24 | GPIO8 | SPI0 CE0_N | SPI 片选 0 |
| 25 | - | GND | 接地 |
| 26 | GPIO7 | SPI0 CE1_N | SPI 片选 1 |
| 27 | ID_SD | EEPROM SDA | 用于 HAT EEPROM 识别 |
| 28 | ID_SC | EEPROM SCL | 用于 HAT EEPROM 识别 |
| 29 | GPIO5 | GPIO 通用 | 推荐用于数字输入/输出 |
| 30 | - | GND | 接地 |
| 31 | GPIO6 | GPIO 通用 | 推荐用于数字输入/输出 |
| 32 | GPIO12 | PWM0 | 硬件 PWM 通道 0 |
| 33 | GPIO13 | PWM1 | 硬件 PWM 通道 1 |
| 34 | - | GND | 接地 |
| 35 | GPIO19 | PCM_FS | PCM 音频帧同步 |
| 36 | GPIO16 | GPIO 通用 | 推荐用于数字输入/输出 |
| 37 | GPIO26 | GPIO 通用 | 推荐用于数字输入/输出 |
| 38 | GPIO20 | PCM_DIN | PCM 音频数据输入 |
| 39 | - | GND | 接地 |
| 40 | GPIO21 | PCM_DOUT | PCM 音频数据输出 |

## 各引脚使用注意事项

### 电源引脚（1, 2, 17）
- **3.3V 引脚（1, 17）**:
  - 最大输出电流：500mA（所有 3.3V 引脚总和）
  - 仅用于低功耗外设
  - 不要将 5V 连接到 3.3V 引脚，会损坏 Pi

- **5V 引脚（2, 4）**:
  - 直接来自 USB 输入电源
  - 电流能力取决于电源适配器
  - 不要将 5V 连接到任何 GPIO 引脚

### I2C 引脚（3, 5）
- **GPIO2 (SDA) / GPIO3 (SCL)**:
  - 默认配置为 I2C-1 总线
  - 已启用内部上拉电阻（1.8kΩ）
  - 不要用作普通 GPIO，除非禁用 I2C
  - 用于连接 I2C 传感器、显示屏等
  - 禁用方法：`sudo raspi-config` → Interface Options → I2C

### UART 引脚（8, 10）
- **GPIO14 (TXD) / GPIO15 (RXD)**:
  - 默认配置为 UART0（串口控制台）
  - 波特率通常为 115200
  - 用作 GPIO 前需禁用串口控制台
  - 禁用方法：`sudo raspi-config` → Interface Options → Serial Port

### SPI 引脚（19, 21, 23, 24, 26）
- **GPIO9, 10, 11, 8, 7**:
  - 默认配置为 SPI0 总线
  - 用于高速数据传输（SD 卡、ADC 等）
  - 用作 GPIO 前需禁用 SPI
  - 禁用方法：`sudo raspi-config` → Interface Options → SPI

### PWM 引脚（12, 32, 33, 35）
- **GPIO12 (PWM0) / GPIO13 (PWM1)**:
  - 硬件 PWM，最高频率可调
  - 适用于电机控制、LED 调光
  - 精度高，无需 CPU 干预

- **GPIO18**:
  - 可配置为 PWM 或 PCM 音频
  - 需要通过软件配置

### EEPROM 识别引脚（27, 28）
- **ID_SD / ID_SC**:
  - 专用于 HAT（Hardware Attached on Top）EEPROM
  - 不应连接到其他设备
  - 用于自动配置和识别扩展板

### PCM 音频引脚（19, 20, 21, 35, 40）
- **GPIO19, 20, 21**:
  - 用于 PCM 音频接口
  - 可连接外部音频设备
  - 与 PWM 共用某些引脚

### 通用 GPIO 引脚
**推荐用于数字示波器采样的引脚**:
- **GPIO4, 5, 6, 7, 16, 17, 20, 21, 22, 23, 24, 25, 26, 27**
- 这些引脚默认不绑定特殊功能
- 使用前确认未被其他程序占用
- GPIO17 是最常用的示例引脚

### GND 引脚（6, 9, 14, 20, 25, 30, 34, 39）
- 所有 GND 引脚是连通的
- 可以使用任意一个作为信号地
- 多个 GND 引脚提供更好的电流分布

## 重要安全警告

### ⚠️ 不要混淆 3.3V 和 5V
- GPIO 引脚是 **3.3V 逻辑电平**
- 输入超过 3.3V 的电压会损坏 Raspberry Pi
- 使用 5V 传感器时需要电平转换器

### ⚠️ 电流限制
- 单个 GPIO 最大输出电流：16mA
- 所有 GPIO 总和最大：50mA
- 不要直接驱动大电流负载（需要晶体管/MOSFET）

### ⚠️ 防止短路
- 连接电路前断电
- 使用万用表检查接线
- GND 必须正确连接

### ⚠️ 信号完整性
- 高速信号（>100 kHz）需要考虑：
  - 接地回路
  - 信号衰减
  - EMI 干扰
  - 使用短且屏蔽良好的线缆

### ⚠️ 引脚冲突
- 某些引脚有多种功能（I2C/SPI/UART/PWM）
- 使用前检查是否被其他程序占用
- 可以通过 `/sys/kernel/debug/gpio` 查看引脚使用情况

## 性能优化建议

### 对于低速信号 (<100 kHz)
使用 `RPi.GPIO` 轮询模式，简单直接。

### 对于中速信号 (100-500 kHz)
使用 `Pigpio` 库，提供更好的性能。

### 对于高速信号 (>500 kHz)
使用 C/C++ 直接内存访问或 Pigpio DMA 模式。

## 注意事项

1. **需要 root 权限**: GPIO 访问需要 sudo
2. **Raspberry Pi 5 特性**: 使用新的 RP1 GPIO 控制器
3. **Python 开销**: Python 解释器限制最大采样率
4. **信号完整性**: 高速采样需要考虑电路板噪声和走线

## 相关资源

- [RPi.GPIO 官方文档](https://sourceforge.net/p/raspberry-gpio-python/wiki/)
- [gpiozero 文档](https://gpiozero.readthedocs.io/)
- [Pigpio 文档](http://abyz.me.uk/rpi/pigpio/)
- [RP1 GPIO 控制器](https://datasheets.raspberrypi.com/rp1/rp1-peripherals.pdf)
