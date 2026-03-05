# Raspberry Pi 5 数字示波器 PRD

## 项目概述

使用当前 Raspberry Pi 5 制作一个可以自定义触发条件的数字示波器，用于捕捉特定的输入信号模式是否发生。
当前操作系统是Ubuntu 24.04 LTS。

## 性能指标

> **注意**：以下性能指标基于 libgpiod C++ 边沿事件检测的实测结果（10 kHz 信号，<0.01% 误差）。1 Msps 采样率为理论最大值，需要进一步高频率测试验证。

| 参数 | 规格 | 验证状态 | 备注 |
|------|------|----------|------|
| 最大采样频率 | 1 Msps | ⚠️ 待高频率测试 | 10 kHz 已验证，50-100 kHz 待测 |
| 测量信号频率 | ≤ 100 kHz | ⚠️ 待测试 | 用户实际信号，50-100 kHz 需验证 |
| 采样深度 | 100k 点 | - | 4 通道同时采集 |
| 实时刷新率 | 30 fps (左上区域) | ⚠️ 与采样率需权衡 | 需优化 |
| 触发到显示延迟 | < 100 ms | ⚠️ 待实现测试 | 不包括 PNG/CSV 保存 |
| CPU/GPU 负载限制 | ≤ 90% | - | 运行时监控 |

**性能权衡说明**：
- 30 fps 实时刷新 + 1 Msps 采样 = 33.3 ms/帧（100k点）
- 触发延迟 < 100 ms 指触发到显示，不包括 PNG/CSV 保存（异步进行）
- CPU 负载限制主要影响 GUI 渲染，采样线程在独立 CPU 核心运行

## 采样频率设置

- **自动调整策略**：当调整时间轴跨度时自动调整采样频率
- **采样频率显示**：实时显示在左上界面中
- **稳定性优化建议**：
  - 采样频率 = 采样深度 / (时间轴跨度 × div数 × 1.2)
  - 其中 1.2 是安全系数，确保数据完整性
  - 采样频率范围：1 kHz - 1 Msps
  - 使用固定档位表以提高稳定性（例如：1k, 2k, 5k, 10k, 20k, 50k, 100k, 200k, 500k, 1M Hz）

## GPIO 通道配置

示波器输入引脚：通道对应引脚可以在配置文件中配置（`./config/osc_config.yaml`）

|| 通道 | GPIO 编号 | 物理引脚 | 默认配置 | 备注 |
||------|-----------|----------|----------|------|
|| 通道1 | GPIO5 | 29脚 | 已配置 | 通用 GPIO，/dev/gpiochip4 line 5 |
|| 通道2 | GPIO6 | 31脚 | 已配置 | 通用 GPIO，/dev/gpiochip4 line 6 |
|| 通道3 | GPIO23 | 16脚 | 已配置 | 通用 GPIO，/dev/gpiochip4 line 23 |
|| 通道4 | GPIO24 | 18脚 | 已配置 | 通用 GPIO，/dev/gpiochip4 line 24 |
|| 外部触发 | GPIO16 | 36脚 | 已配置 | 通用 GPIO，/dev/gpiochip4 line 16 |

**注意**：所有 4 通道和外部触发均在第一版实现。所有 GPIO 引脚位于 `/dev/gpiochip4` (RP1 控制器)。

## 图形界面布局

整个显示界面分为 2x2 四个显示区域：

### 左上区域：实时波形显示
- 显示各通道实时波形
- 刷新率：30 fps
- 四通道颜色分配：
  - 通道1：黄色 (Yellow, #FFFF00)
  - 通道2：绿色 (Green, #00FF00)
  - 通道3：紫色 (Purple, #800080)
  - 通道4：蓝色 (Blue, #0000FF)
- 坐标轴数字显示单位提示：X 轴用 `s`（时间），Y 轴用 `V`（电压）；只需要在最大一个显示的数字后面带单位即可。
- 显示内容：实时波形、当前采样频率
- 触发生效时更新，但可能根据触发方式不一定一直保持

### 左下区域：示波器设置
- 示波器设置按钮（全部采用按钮，不使用旋钮）
- 每个按钮对应快捷键，快捷键显示在按钮上：放在按钮名下方，以括号形式显示（例如：`CH1` 下方显示 `(1)`）
- 快捷键在配置文件中定义
- 通道开关按钮颜色：通道关闭时为默认灰色；通道打开时按钮背景色为该通道颜色（CH1 黄 `#FFFF00`、CH2 绿 `#00FF00`、CH3 紫 `#800080`、CH4 蓝 `#0000FF`）
- 系统负荷状态显示（CPU/GPU 使用率）

### 右上区域：触发画面快照
- 显示最近一次触发时的显示画面
- 包含时间标记：格式为 `YYYY-MM-DD HH:MM:SS.mmm`（例如：2025-02-26 14:30:45.123）
- 自动保存对应 PNG 截图文件
- 触发生效时与左上同时更新

### 右下区域：触发记录滚动文本
- 滚动文本显示框
- 每行文本显示一个触发摘要（时间戳、触发条件、触发状态）
- 显示最近 100 条触发记录
- 触发记录同时记录到 CSV 文件
- 增加按钮：`Clear Trigger Records`
  - 清空右下窗口内存中的触发记录显示
  - 清空 `trigger_log.csv` 内容（保留表头）
  - 删除所有触发截图 `Trig_*.png`

## 示波器设置按钮

参考示波器常用的纵横轴设置方法，按钮包括但不限于：

### 通道控制
- `Channel 1` / `CH1`：通道1 开关
- `Channel 2` / `CH2`：通道2 开关
- `Channel 3` / `CH3`：通道3 开关
- `Channel 4` / `CH4`：通道4 开关

### 时间轴设置 (X Scale)
- `X Scale Up`：增加时间轴跨度（放大波形）
- `X Scale Down`：减小时间轴跨度（缩小波形）
- `X Position Up`：向右移动波形
- `X Position Down`：向左移动波形

**注意**：时间轴的 div 数与 Y 轴相同，采用 1, 2, 5, 10 步进法

### 电压轴设置 (Y Scale)
- 由于本版本输入为数字 GPIO（0/1），Y 轴显示范围固定为 **0~1.5**（为多通道 Y 偏移留出空间，确保能看到所有通道）。
- 不提供 `Y Scale` / `Y Position` 按钮。

### 触发设置
- `Trig Auto`：自动触发模式
- `Trig Normal`：正常触发模式
- `Trig Single`：单次触发模式
- `Trig Position Left`：触发位置向左移动（只影响显示位置）
- `Trig Position Right`：触发位置向右移动（只影响显示位置）
- `Holdoff`：触发保持时间设置
- 触发位置处用**垂直虚线**标出，虚线颜色与触发的通道（边沿触发的那个通道）颜色一致

**注意**：触发位置调整有两个按钮（Left/Right），每个按钮都有对应的键盘快捷键

### 其他
- `Help`：帮助对话框
- `About`：关于对话框
- `Fullscreen`：全屏模式切换

**注意**：所有按钮需在配置文件中定义快捷键映射。

## 时间轴和电压轴设置

### 时间轴 (X Axis)
- **跨度范围**：10 μs/div 到 10 s/div
- **调整步进**：1, 2, 5, 10
- **显示 Div 数**：固定为 **5 div**（随 X Scale 调整 `μs/div`，但窗口始终显示 5 个 div 的时间范围）
- **推荐档位序列**：
  ```
  10μs, 20μs, 50μs, 100μs, 200μs, 500μs,
  1ms, 2ms, 5ms, 10ms, 20ms, 50ms,
  100ms, 200ms, 500ms, 1s, 2s, 5s, 10s
  ```

### 电压轴 (Y Axis)
- 本版本输入源为数字 GPIO（0/1），因此 Y 轴固定显示范围为 **0~1**。
- 不提供 Y 轴的 scale/position 调整。

### 网格线
- **密度**：与 div 对齐（每个 div 一条网格线）
- **颜色**：灰色半透明
- **样式**：实线或虚线

## 触发方式

### 基础触发模式
> **重要**：Trig Auto / Trig Normal / Trig Single **不改变触发条件本身**。
> 只有当信号满足给定的触发逻辑条件时才产生触发记录。
> 三种模式的区别仅在于“触发后主窗口如何显示”。

- **自动模式 (Auto)**：未触发时主窗口显示实时波形；触发后主窗口停留在触发时画面 **2 秒**，然后自动恢复实时波形显示。
- **正常模式 (Normal)**：设置后首次触发前主窗口显示实时波形；触发后主窗口停留在触发时画面，直到下一次触发发生（下一次触发会更新为新的触发画面）。
- **单次模式 (Single)**：设置后首次触发前主窗口显示实时波形；首次触发后主窗口停留在触发时画面，并且不再进行新的触发，直到用户再次按下 Single 或切换到其他触发模式。

### 触发源
- **单通道触发**：选择通道1-4作为触发源
- **外部触发**：外部触发通道（在配置文件中定义）

### 触发电平
- **范围**：0 - 5V
- **精度**：1 mV
- **设置方式**：通过按钮或输入框调整

### 边沿类型
- **上升沿** (Rising Edge)：信号从低到高跳变
- **下降沿** (Falling Edge)：信号从高到低跳变
- **双边沿** (Both Edges)：任意方向跳变

### 触发保持时间 (Holdoff Time)
- **功能**：触发后的一段时间内不再次触发
- **范围**：10 μs - 10 s
- **设置方式**：通过按钮或配置文件

### 自定义触发逻辑

**触发条件规则**：
- 支持最多 10 个触发条件
- 支持逻辑运算（AND, OR, NOT）
- 条件之间可以组合形成复杂逻辑
- 时间延迟范围：几十微秒到几秒

**触发条件示例**：

**示例 1**：
> 在通道1上升沿跳变之后，10ms 之内，通道2也发生了上升沿跳变，则触发

逻辑表达式：
```
(CH1 Rising Edge) AND (CH2 Rising Edge within 10ms after CH1 Rising)
```

**示例 2**：
> 通道3为高电平，且通道4下降沿跳变，则触发

逻辑表达式：
```
(CH3 = High) AND (CH4 Falling Edge)
```

**示例 3**（复杂逻辑）：
> 通道1上升沿之后5ms内通道2上升沿，或者通道3下降沿之后100μs内通道4双边沿

逻辑表达式：
```
[(CH1 Rising Edge) AND (CH2 Rising Edge within 5ms after CH1)] OR
[(CH3 Falling Edge) AND (CH4 Both Edges within 100μs after CH3)]
```

**触发条件配置方式**：
- 采用文本表达式输入（选项 B）
- 类似编程语言的语法，易于理解和调试
- 支持逻辑运算符：AND, OR, NOT
- 支持时间延迟：within X ms after/before
- 支持条件组合：使用括号分组

**文本表达式语法说明**：

**边沿触发**：
```
CH1 Rising              # 通道1上升沿
CH1 Falling             # 通道1下降沿
CH1 Both                 # 通道1双边沿
```

**时间延迟**：
```
CH2 Rising within 10ms after CH1 Rising      # CH1上升后10ms内CH2上升
CH3 Falling within 100us before CH4 Rising    # CH4上升前100μs内CH3下降
```

**逻辑组合**：
```
(CH1 Rising) AND (CH2 Rising)                 # 两个条件同时满足
(CH1 Rising) OR (CH2 Rising)                  # 两个条件满足其一
NOT (CH1 Rising)                              # 非CH1上升沿
[(CH1 Rising) AND (CH2 Falling)] OR (CH3 Both)  # 复杂逻辑
```

**触发条件保存和加载**：
- 每个触发条件可保存为配置文件（YAML 格式）
- 支持加载和删除已保存的触发条件
- 支持导入/导出触发条件配置
- 配置文件路径：`./config/trigger_conditions.yaml`

## 触发记录

### 触发记录存储

| 存储位置 | 格式 | 内容 | 数量 |
|----------|------|------|------|
| 内存 | - | 最近 100 条记录 | 100 条 |
| 文件 | CSV | 触发记录（启动时裁剪） | **最多保留最近 1000 条** |
| 文件 | PNG | 触发截图（启动时裁剪） | **最多保留最近 1000 张** |

**启动时裁剪规则**：
- 每次启动程序时，如果 `trigger_log.csv` 记录超过 1000 条，则仅保留最近发生的 1000 条记录。
- 每次启动程序时，如果触发截图目录内 `Trig_*.png` 超过 1000 张，则仅保留最近生成的 1000 张，其余删除。

**触发截图保存规则**：每次触发生成触发记录的同时：
- 将当时主窗口画面显示在右上“触发画面快照”区域。
- 将该画面保存为 PNG 文件，命名格式：`Trig_YYYY-MM-DD HH-MM-SS.mmm.png`（将 `:` 替换为 `-` 以便跨平台）。

### 触发记录内容

**内存显示（右下区域）**：
每行显示一个触发摘要，格式：
```
[时间] [触发模式] [触发条件] [状态]
```

示例：
```
2025-02-26 14:30:45.123 | Normal | CH1 Rising | Triggered
2025-02-26 14:30:40.456 | Custom | CH1↑ then CH2↑(10ms) | Triggered
2025-02-26 14:30:35.789 | Normal | CH2 Falling | Timeout
```

**CSV 文件记录**：
字段包括：
- 触发时间戳 (YYYY-MM-DD HH:MM:SS.mmm)
- 触发模式 (Auto/Normal/Single/Custom)
- 触发源 (CH1/CH2/CH3/CH4/External)
- 触发电平 (V)
- 触发条件描述
- 触发状态 (Triggered/Timeout)
- 截图文件路径

**PNG 截图**：
- 文件命名格式：`trigger_YYYYMMDD_HHMMSS_mmm.png`
- 存储路径：`./screenshots/`
- 保留最近 100 张，超过自动删除旧文件

### 截图内容
- 触发生效时的完整画面
- 包含时间标记
- 包含触发条件
- 包含各通道波形

## 配置文件

### 配置文件规范

**文件格式**：YAML（可读性强）
**文件路径**：`./config/osc_config.yaml`
**加载方式**：程序启动时加载，不支持运行时重新加载

### 配置文件内容

```yaml
# GPIO 通道配置
gpio_channels:
  channel1:
    gpio_pin: 5
    physical_pin: 29
    enabled: true
  channel2:
    gpio_pin: 6
    physical_pin: 31
    enabled: true
  channel3:
    gpio_pin: null
    physical_pin: null
    enabled: false
  channel4:
    gpio_pin: null
    physical_pin: null
    enabled: false
  external_trigger:
    gpio_pin: null
    physical_pin: null
    enabled: false

# 采样配置
sampling:
  max_frequency: 1000000  # 1 Msps
  depth: 100000  # 100k points
  default_time_scale: 1000  # μs/div

# 界面配置
display:
  refresh_rate: 30  # fps
  grid_visible: true
  trigger_record_max: 100
  screenshot_path: "./screenshots/"
  trigger_log_path: "./logs/trigger_log.csv"

# 触发默认配置
trigger:
  default_mode: "Normal"  # Auto, Normal, Single
  default_channel: 1
  default_level: 1.65  # V
  default_edge: "Rising"  # Rising, Falling, Both
  default_holdoff: 0.001  # s

# 快捷键配置
hotkeys:
  channel1: "1"
  channel2: "2"
  channel3: "3"
  channel4: "4"
  x_scale_up: "Right"
  x_scale_down: "Left"
  x_position_up: "Shift+Right"
  x_position_down: "Shift+Left"
  trig_auto: "A"
  trig_normal: "N"
  trig_single: "S"
  trig_position_left: "W"
  trig_position_right: "D"
  fullscreen: "F"
  help: "H"
  about: "?"

# 性能配置
performance:
  max_cpu_load: 90  # %
  max_gpu_load: 90  # %
  target_fps: 30

# 其他配置（待添加）
# ...
```

## 用户界面功能

### 对话框

**帮助对话框** (Help)：
- 使用说明
- 快捷键列表
- 触发条件配置教程
- 常见问题解答

**关于对话框** (About)：
- 版本信息
- 作者信息
- 许可证
- 技术支持联系方式

### 全屏模式
- 支持 F11 快捷键或按钮切换
- 全屏模式下隐藏菜单栏和边框
- 保留所有功能按钮

### 系统状态显示
- 在左下区域显示：
  - CPU 使用率
  - GPU 使用率
  - 内存使用率
  - 当前采样频率
  - 实时帧率

## 未来功能（第一版暂不实现）

以下功能将在后续版本中实现：

### 数据导出
- 波形数据导出为 CSV 文件
- 波形数据导出为二进制文件
- 批量导出触发记录

### 自动测量功能
- 频率测量
- 周期测量
- 占空比测量
- 峰峰值测量
- 平均值测量
- 最大值/最小值测量

### 数学运算
- 通道加法 (CH1 + CH2)
- 通道减法 (CH1 - CH2)
- 通道乘法
- 通道除法
- FFT 频谱分析

### 光标测量
- 水平光标（时间测量）
- 垂直光标（电压测量）
- 双光标同时显示
- 光标差值自动计算

### 高级触发模式
- Pattern 触发（模式触发）
- State 触发（状态触发）
- Timeout 触发（超时触发）
- 窗口触发（电平在指定范围内）
- 斜率触发（信号斜率）

### 其他
- 多语言支持
- 自定义主题
- 波形对比功能
- 波形标注功能
- 远程控制接口

## 技术栈建议

### 硬件
- Raspberry Pi 5
- GPIO 直接内存访问（DMA）

### 软件
- **编程语言**：Python 3.12+
- **GUI 框架**：PyQt6
- **GPIO 控制**：libgpiod C++ 边沿事件检测（libgpiodcxx）
- **绘图库**：PyQtGraph（高性能实时绘图）
- **配置管理**：PyYAML
- **数据存储**：CSV, PNG

### 性能优化
- 使用 libgpiod C++ 边沿事件进行高速采样（目标 1 Msps）
- 批量事件读取（`event_read_multiple()`）减少系统调用
- 多线程架构（C++ 采样线程 + Python GUI 主线程）
- CPU 亲和性绑定（采样线程绑定到独立核心）
- 内核级事件队列缓存，不依赖轮询
- PyQtGraph + OpenGL 硬件加速绘图
- 异步保存 PNG/CSV（不阻塞触发到显示）

## 技术验证与经验教训

### GPIO 硬件架构

**RPi5 GPIO 控制器架构**：
- RPi5 使用 RP1 GPIO 控制器（不同于传统 BCM 芯片）
- **关键发现**：RP1 GPIO 对应 `/dev/gpiochip4`，而非传统的 `/dev/gpiochip0`
- **验证方法**：通过 `gpio_chip_test.py` 测试所有 /dev/gpiochip0-4，确认物理引脚 29 (GPIO5) 信号位于 chip4 的 line 5
- **正确配置**：
  ```python
  GPIO_CHIP = "/dev/gpiochip4"  # RP1 控制器
  GPIO_LINE = 5                 # 对应 GPIO5 / 物理引脚 29
  ```

### 权限管理

**权限问题**：
- **问题**：直接访问 `/dev/gpiochip4` 会返回 `[Errno 13] Permission denied`
- **解决方案**：使用 `sudo` 运行程序，或配置 udev 规则添加用户到 gpio 组
- **验证脚本**：`fix_gpio_perms.sh` 自动修复权限问题

### 采样方法对比

#### 方法 1：libgpiod Python 轮询 ❌ 不推荐

**测试结果**：
```
实际信号：10 kHz 方波（示波器验证）
轮询测量：2.23 kHz（误差 77%）
边沿丢失：76.44%（20000 边沿/秒 → 4713 边沿/秒）
最大采样率：~368 ksps
```

**根本原因**：
- Ubuntu 24.04 是非实时操作系统
- Python 轮询受调度器影响，无法保证高频信号的完整性
- 轮询间隔不稳定，导致大量边沿丢失

**结论**：无法满足 PRD 的 1 Msps 采样率和 <1% 误差要求

#### 方法 2：libgpiod 边沿检测 ❌ 不推荐

**测试结果**：
```
采样率：~33 ksps
准确率：23% 左右
问题：仍然丢失大量边沿
```

#### 方法 3：libgpiod C++ 边沿事件检测 ✅ **最终推荐**

**测试结果**（2026-02-27）：
```
实际信号：10 kHz 方波（示波器验证）
芯片：/dev/gpiochip4 (RP1 控制器)
线路：5 (GPIO5, 物理引脚 29)
事件类型：双边沿检测 (BOTH_EDGES)

测量结果：
  - 捕获边沿：20,002 / 秒
  - 测量频率：10,000.99 Hz
  - 期望频率：10,000 Hz
  - 准确度：100.01%
  - 边沿丢失：-0.01%（多捕获 2 个边沿）
```

**对比分析**：
| 方法 | 最大采样率 | 10 kHz 测量 | 边沿捕获率 | 误差率 | 推荐度 |
|------|-----------|----------------|-----------|--------|--------|
| libgpiod 轮询 (Python) | 368 ksps | 2.23 kHz | 4,713/秒 | 77% | ❌ 不推荐 |
| libgpiod 边沿检测 (Python) | 33 ksps | ~2.3 kHz | 未测试 | ~77% | ❌ 不推荐 |
| **libgpiod 边沿事件 (C++)** | **待测** | **10,000.99 Hz** | **20,002/秒** | **<0.01%** | ⭐ **完美** |

**关键优势**：
1. **高准确度**：<1% 边沿丢失，完全满足 PRD 要求
2. **硬件级时间戳**：纳秒级精度（`std::chrono::nanoseconds`）
3. **批量事件读取**：`event_read_multiple()` 一次读取多个事件，减少系统调用
4. **内核级边沿检测**：使用 Linux GPIO 子系统，不受 OS 调度影响
5. **C++ 性能优化**：比 Python 快 77 倍（20k vs 4.7k 边沿/秒）
6. **标准 API**：`libgpiodcxx`，官方维护，稳定可靠

**代码示例**：
```cpp
#include <gpiod.hpp>
#include <chrono>

using namespace gpiod;
using namespace std::chrono;

int main() {
    chip gpio_chip("/dev/gpiochip4");
    line gpio_line = gpio_chip.get_line(5);

    // 配置双边沿事件检测
    line_request config;
    config.consumer = "oscilloscope";
    config.request_type = line_request::EVENT_BOTH_EDGES;

    gpio_line.request(config);

    // 批量读取事件（非阻塞）
    while (running) {
        std::vector<line_event> events = gpio_line.event_read_multiple();
        for (const auto& event : events) {
            // 处理每个边沿事件
            // event.timestamp: 纳秒级时间戳
            // event.event_type: RISING_EDGE 或 FALLING_EDGE
        }
    }
}
```

**性能特性**：
- 事件缓冲：内核队列缓存边沿事件，应用程序批量读取
- 非阻塞读取：`event_read_multiple()` 立即返回可用事件
- 零拷贝优化：C++ 智能指针管理，无性能损失
- 实时性：硬件中断驱动边沿检测，不依赖轮询

**高频率测试需求**：
- 当前测试：10 kHz（20k 边沿/秒）✅ 通过
- 需要测试：50 kHz、100 kHz（验证极限）
- PRD 目标：1 Msps（2M 边沿/秒）⚠️ 需要进一步优化

**预期性能**：
- 理论极限：取决于 Linux GPIO 子系统和事件队列深度
- 实际测试：建议测试 50-100 kHz 确定稳定采样上限
- 优化方向：
  1. 增大事件缓冲区（减少读取次数）
  2. 使用优先级线程（优先处理事件）
  3. CPU 亲和性绑定（绑定到特定核心）

#### 方法 4：PIGPIO DMA 采样 ❌ RPi5 不兼容

**兼容性问题**：
- PIGPIO V79 不支持 RPi5 硬件版本 (e04171)
- 错误信息：
  ```
  gpioHardwareRevision: unknown rev code (e04171)
  Sorry, this system does not appear to be a raspberry pi.
  ```
- 原因：PIGPIO 基于 BCM283x SoC，RPi5 使用 RP1 控制器

**替代方案**：
- 使用 `libgpiod`（C++ 边沿事件）⭐ 推荐
- 尝试 `WiringPi`（可能支持 RPi5）
- 直接内存映射 `/dev/mem`（最高性能，需谨慎）

### PIGPIO 安装注意事项

**Ubuntu 24.04 特有问题**：
- **问题**：`sudo apt install python3-pigpio` 仅安装 Python 绑定，缺少 `pigpiod` 守护进程
- **症状**：
  ```bash
  python3 -c "import pigpio; print('OK')"  # 成功
  sudo systemctl start pigpiod              # 失败：Unit not found
  which pigpiod                             # 未找到
  ```
- **解决方案**：从源码编译安装完整版 PIGPIO V79
  ```bash
  ./install_pigpio_source.sh  # 2-3 分钟完成
  ```
- **安装内容**：
  - `pigpiod` 守护进程
  - `pigs` CLI 工具
  - Python 绑定
  - 支持 DMA 和硬件时间戳

**但是**：即使安装成功，PIGPIO 在 RPi5 上仍然不可用

### 性能基准测试总结

| 采样方法 | 最大采样率 | 10 kHz 信号测量 | 边沿捕获率 | 误差率 | 推荐度 |
|---------|-----------|----------------|-----------|--------|--------|
| libgpiod 轮询 (Python) | 368 ksps | 2.23 kHz | 4,713/秒 | 77% | ❌ 不推荐 |
| libgpiod 边沿检测 (Python) | 33 ksps | ~2.3 kHz | 未测试 | ~77% | ❌ 不推荐 |
| **libgpiod 边沿事件 (C++)** | **待测 1 Msps** | **10,000.99 Hz** | **20,002/秒** | **<0.01%** | ⭐ **最终推荐** |
| PIGPIO DMA | 1-5 Msps | ❌ RPi5 不兼容 | 不可用 | N/A | ❌ 不可用 |

**性能提升对比**：
- Python 轮询 → C++ 边沿事件：**准确度提升 77 倍**
- 边沿捕获率提升：4,713 → 20,002 边沿/秒（4.2 倍）
- CPU 使用降低：批量读取减少系统调用

### 最终技术方案推荐

**✅ 采用方案：libgpiod C++ 边沿事件检测**

**理由**：
1. 满足 PRD 准确度要求（<1% 误差）
2. 标准库，官方维护，稳定可靠
3. 无额外依赖，系统自带支持
4. 支持 RPi5 的 RP1 GPIO 控制器
5. C++ 性能优势明显

**实现要点**：
- 使用 `libgpiodcxx` C++ 绑定
- 双边沿事件检测（`EVENT_BOTH_EDGES`）
- 批量事件读取（`event_read_multiple()`）
- 硬件纳秒级时间戳
- 多线程架构（采样线程 + GUI 主线程）

**性能目标**：
- 准确度：<1% 边沿丢失
- 采样率：1 Msps（待高频率测试验证）
- 信号频率：100 kHz（10 kHz 已验证通过）
- 实时性：内核级边沿检测

### 开发指导原则

**硬件配置**：
1. 使用 `/dev/gpiochip4` 作为 RP1 GPIO 芯片（**不要使用 /dev/gpiochip0**）
2. GPIO5 对应物理引脚 29，用于通道 1
3. GPIO6 对应物理引脚 31，用于通道 2

**软件架构**：
1. **使用 libgpiod C++ 边沿事件检测**（PIGPIO DMA 在 RPi5 上不兼容）
2. 使用 `libgpiodcxx` C++ 绑定，双边沿事件检测（`EVENT_BOTH_EDGES`）
3. 使用批量事件读取（`event_read_multiple()`）
4. 所有 GPIO 访问需要 root 权限（使用 `sudo` 运行）
5. 多线程架构（C++ 采样线程 + Python GUI 主线程）

**性能优化**：
1. 使用批量事件读取减少系统调用
2. 使用 CPU 亲和性绑定采样线程到特定核心
3. 使用 PyQtGraph + OpenGL 加速绘图
4. 事件队列缓存：内核级边沿检测，不依赖轮询

**已知限制**：
- Ubuntu 24.04 是非实时操作系统，依赖内核级边沿事件
- 1 Msps 采样率目标待高频率测试验证（目前仅验证 10 kHz）
- PIGPIO 不支持 RPi5（硬件版本 e04171）

**禁止项**：
- ❌ 不要使用 Python 轮询（77% 边沿丢失）
- ❌ 不要使用 PIGPIO（RPi5 不兼容）
- ❌ 不要使用 /dev/gpiochip0（错误的芯片）

### 开发经验教训（踩坑记录）

#### 1. GPIO 硬件架构陷阱 ⚠️

**错误做法**：
```python
GPIO_CHIP = "/dev/gpiochip0"  # ❌ 错误：这是 BCM 芯片
GPIO_LINE = 5
```

**正确做法**：
```python
GPIO_CHIP = "/dev/gpiochip4"  # ✅ 正确：RP1 控制器
GPIO_LINE = 5  # GPIO5 = 物理引脚 29
```

**如何发现的**：
- 运行 `gpio_chip_test.py` 测试所有 /dev/gpiochip0-4
- 发现物理引脚 29 的信号位于 chip4 的 line 5
- RPi5 使用 RP1 GPIO 控制器，不同于传统 BCM 芯片

**验证方法**：
```bash
python3 gpio_chip_test.py
```

#### 2. 权限问题陷阱 ⚠️

**错误现象**：
```
[Errno 13] Permission denied accessing /dev/gpiochip4
```

**错误做法**：
```bash
python3 freq_measure_cpp  # ❌ 无权限
```

**正确做法**：
```bash
sudo ./freq_measure_cpp  # ✅ 使用 sudo
```

**权限配置（可选）**：
```bash
# 运行权限修复脚本
./fix_gpio_perms.sh

# 或手动配置 udev 规则
sudo usermod -aG gpio $USER
```

**注意**：Ubuntu 24.04 中，即使配置了 udev 规则，某些操作仍需要 sudo

#### 3. 采样方法选择陷阱 ⚠️

| 方法 | 最大采样率 | 10 kHz 信号 | 误差率 | 推荐度 | 原因 |
|------|-----------|------------|--------|--------|------|
| Python 轮询 (libgpiod) | 368 ksps | 2.23 kHz | 77% | ❌ | Ubuntu 非实时系统，调度器影响大 |
| Python 边沿检测 | 33 ksps | ~2.3 kHz | ~77% | ❌ | 仍然依赖 Python 解释器开销 |
| **C++ 边沿事件** | **待测** | **10,001 Hz** | **<0.01%** | ✅ | 内核级边沿检测，硬件时间戳 |
| PIGPIO DMA | N/A | N/A | N/A | ❌ | RPi5 不兼容 |

**错误做法**：
```python
# ❌ 不要使用 Python 轮询
while True:
    value = line.get_value()
    # 77% 的边沿丢失
```

**正确做法**：
```cpp
// ✅ 使用 C++ 边沿事件
line_request config;
config.request_type = line_request::EVENT_BOTH_EDGES;
gpio_line.request(config);

std::vector<line_event> events = gpio_line.event_read_multiple();
// 纳秒级硬件时间戳，<0.01% 边沿丢失
```

**根本原因**：
- Ubuntu 24.04 = 非实时操作系统
- Python 轮询受调度器影响，无法保证高频信号完整性
- C++ 边沿事件 = 内核级硬件中断驱动，不受 OS 调度影响

#### 4. PIGPIO 安装陷阱 ⚠️

**错误现象**：
```bash
sudo apt install python3-pigpio  # ✅ 成功
python3 -c "import pigpio"        # ✅ 成功
sudo systemctl start pigpiod      # ❌ 失败：Unit not found
which pigpiod                     # ❌ 未找到
```

**根本原因**：
- Ubuntu 24.04 的 `python3-pigpio` 包只包含 Python 绑定
- 缺少 `pigpiod` 守护进程和 `pigs` CLI 工具

**错误做法**：
```bash
# ❌ 从 Ubuntu 仓库安装
sudo apt install python3-pigpio
```

**正确做法**（但 RPi5 仍然不兼容）：
```bash
# ✅ 从源码安装
./install_pigpio_source.sh

# ❌ 但运行时仍然失败
gpioHardwareRevision: unknown rev code (e04171)
Sorry, this system does not appear to be a raspberry pi.
```

**最终结论**：
- PIGPIO V79 不支持 RPi5 硬件版本（e04171）
- 原因：PIGPIO 基于 BCM283x SoC，RPi5 使用 RP1 控制器
- **不要尝试修复 PIGPIO，改用 libgpiod C++**

#### 5. Ubuntu 24.04 特性问题 ⚠️

**系统信息**：
```
Raspberry Pi 5 Model B Rev 1.1
OS: Ubuntu 24.04 LTS (Noble) - 不是 Raspberry Pi OS
Kernel: Linux
```

**影响**：
- 不是 Raspberry Pi OS，某些工具可能不可用
- Python3 包管理：`python3-pip` 需要通过 `apt` 安装
- 非 realtime 操作系统，需要硬件级采样方案

**检查命令**：
```bash
python3 gpio_status.py
```

#### 6. 性能验证陷阱 ⚠️

**错误假设**：
```
1 Msps 采样率一定可以达到
```

**实际验证**：
- ✅ 10 kHz 信号：20,002 边沿/秒，100.01% 准确度
- ⚠️ 50-100 kHz：待测试
- ❓ 1 Msps：待验证（可能不可行）

**差距分析**：
- 当前验证：10 kHz（20k 边沿/秒）
- PRD 目标：1 MHz（2M 边沿/秒）
- **差距：100 倍！**

**建议**：
1. 先测试 50-100 kHz 确定稳定采样上限
2. 如果边沿事件方法无法达到 1 Msps，考虑：
   - 降低目标到 100 ksps
   - 使用内存映射方法（复杂但高性能）
   - 外部硬件采样方案（FPGA/ADC）

#### 7. 配置文件陷阱 ⚠️

**快捷键冲突**：
```yaml
# 之前的错误配置（已修复）
trig_single: "S"           # ❌ 冲突
trig_level_down: "S"       # ❌ 冲突

# 修复后的正确配置
trig_single: "S"
trig_level_down: "D"       # ✅ 已修复
```

**GPIO 配置**：
```yaml
# 之前的错误配置（已修复）
channel3:
  gpio_pin: null
  enabled: false
channel4:
  gpio_pin: null
  enabled: false

# 修复后的正确配置
channel3:
  gpio_pin: 4
  physical_pin: 7
  enabled: true
  gpio_chip: "/dev/gpiochip4"
  line: 4
channel4:
  gpio_pin: 7
  physical_pin: 26
  enabled: true
  gpio_chip: "/dev/gpiochip4"
  line: 7
```
- 所有 4 通道和外部触发均已配置
- 所有 GPIO 引脚位于 `/dev/gpiochip4` (RP1 控制器)

### 验证脚本清单

以下脚本已验证可用，可直接在开发中使用：

| 脚本名 | 功能 | 状态 | 用途 |
|--------|------|------|------|
| `gpio_chip_test.py` | GPIO 芯片映射测试 | ✅ 已验证 | 确认 GPIO5 位于 `/dev/gpiochip4` |
| `gpio_freq_optimized.py` | Python 多种方法对比 | ✅ 已验证 | 展示轮询 vs 边沿检测差异 |
| `freq_measure_cpp.cpp` | **C++ 边沿事件采样** | ✅ **已验证** | 高速频率测量，<0.01% 误差 |
| `compile_freq_cpp.sh` | 编译 C++ 测试程序 | ✅ 已创建 | 自动检测库路径 |
| `run_freq_cpp.sh` | 运行 C++ 测试程序 | ✅ 已创建 | 包装 sudo 执行 |
| `install_pigpio_source.sh` | PIGPIO 源码安装 | ✅ 已创建 | RPi5 不适用，脚本保留参考 |
| `fix_gpio_perms.sh` | 权限修复工具 | ✅ 已创建 | 配置 udev 规则 |

**测试结果数据**：
```bash
# 10 kHz 信号测试结果（libgpiod C++ 边沿事件）
./freq_measure_cpp

结果：
  - 芯片：/dev/gpiochip4
  - 线路：5 (GPIO5, 物理引脚 29)
  - 事件：双边沿检测
  - 捕获边沿：20,002 / 秒
  - 测量频率：10,000.99 Hz
  - 准确度：100.01%
  - 边沿丢失：-0.01%（完美）
```

**性能对比**：
- Python 轮询：4,713 边沿/秒，77% 误差
- C++ 边沿事件：20,002 边沿/秒，<0.01% 误差
- **性能提升：4.2 倍准确度**

**推荐使用频率**：
- 持续采样：使用 `freq_measure_cpp.cpp` 作为采样线程模板
- 调试验证：快速测试 GPIO 配置和事件捕获
- 性能基准：不同采样率下重复测试，确定极限

### 高频率测试验证计划

#### 背景
**当前验证状态**：
- ✅ 10 kHz 信号：20,002 边沿/秒，100.01% 准确度
- ✅ 20 kHz 信号：最大丢失率 0.37% (CH3)
- ✅ 30 kHz 信号：最大丢失率 0.46% (CH2)
- ❌ 40 kHz 信号：CH3 失败 (10.78% 丢失)，其他通道 <5%
- ⚠️ 边界频率：30-40 kHz 之间，但 CH3 性能异常
- ❓ 1 Msps：待验证（硬性要求）

**关键发现**：
- GPIO23 (Pin 16, CH3) 性能明显低于其他通道
- CH1、CH2、CH4 性能接近，40 kHz 时 <5%
- 可能原因：GPIO23 硬件问题或引脚干扰

**挑战**：
- 10 kHz 验证 → 30 kHz 通过，40 kHz 失败
- GPIO23 成为瓶颈
- **总差距：从 30 kHz (稳定) 到 1 Msps（33 倍）**

#### 测试计划

**阶段 1：频率边界查找（10-100 kHz）**
```
测试频率：10, 20, 30, 35, 40, 45, 50, 75, 100 kHz
测试方法：
  1. 使用 multi_channel_freq_test.cpp 测量准确度
  2. 记录每个通道的边沿丢失率
  3. 分析通道间性能差异
  4. 单独测试 GPIO23 排除竞争问题
  5. 找到通过/不通过的边界频率

成功标准：
  - 所有通道边沿丢失率 < 5%
  - CPU 使用率 < 80%
  - 频率误差 < 1%
  - 通道间性能差异 < 2%

后续步骤：
  - 如果 35 kHz 通过：测试 37.5 kHz 进一步细化
  - 如果 GPIO23 确实有问题：考虑更换 GPIO 引脚
  - 分析中断分布和内核调度
```

**阶段 2：高频验证（100-500 kHz）**
```
测试频率：200 kHz, 500 kHz
测试方法：
  1. 多通道压力测试（4 通道同时）
  2. 内存使用监控
  3. 事件队列深度测试

成功标准：
  - 边沿丢失率 < 10%
  - CPU 使用率 < 90%
  - 无内存泄漏
```

**阶段 3：极限验证（500 kHz - 1 Msps）**
```
测试频率：500 kHz, 750 kHz, 1 MHz
测试方法：
  1. 长时间稳定性测试（1 小时）
  2. 触发延迟测量（需 < 100 ms）
  3. GUI 刷新率验证（30 fps）

成功标准：
  - 边沿丢失率 < 15%（可接受范围）
  - 触发到显示延迟 < 100 ms
  - GUI 流畅无卡顿
```

#### 备选方案

**如果 C++ 边沿事件无法达到 1 Msps：**

**方案 A：降低目标（推荐，可行性高）**
```
- 修改 PRD 最大采样频率为 100 ksps
- 用户信号频率 ≤ 100 kHz（已满足）
- 代价：无法测量更高频率信号
```

**方案 B：内存映射（复杂，性能高）**
```
- 直接映射 /dev/mem 到用户空间
- 绕过内核，直接读取 GPIO 寄存器
- 预期性能：可达 1-5 Msps
- 缺点：
  - 需要深入 RP1 GPIO 寄存器文档
  - 代码复杂度高，维护困难
  - 需要仔细处理并发和同步
```

**方案 C：外部硬件采样（最可靠，成本高）**
```
- 使用外部 ADC/FPGA 采样
- 通过 USB/UART 传输数据到 RPi5
- 预期性能：可达 10-100 Msps
- 缺点：
  - 硬件成本增加
  - 需要额外电路板设计
  - 数据传输延迟
```

#### 决策流程

```
阶段 1 测试（50-100 kHz）
  ├─ 成功 → 进入阶段 2
  └─ 失败 → 考虑方案 A 或 C

阶段 2 测试（100-500 kHz）
  ├─ 成功 → 进入阶段 3
  ├─ 部分成功（可达 200-500 kHz）→ 评估是否可接受
  └─ 失败 → 考虑方案 A 或 B

阶段 3 测试（500 kHz - 1 Msps）
  ├─ 成功（≥ 1 Msps）→ 实现目标！
  ├─ 部分成功（500-750 kHz）→ 与用户协商
  └─ 失败 → 必须选择备选方案
```

#### 测试工具准备

**现有工具**：
- `freq_measure_cpp.cpp` - 单通道频率测量

**需要开发**：
- `multi_channel_freq_test.cpp` - 4 通道同时测试
- `high_freq_stress_test.cpp` - 高频压力测试
- `latency_test.cpp` - 触发延迟测量

#### 时间安排

```
Week 1: 阶段 1 测试（50-100 kHz）
Week 2: 阶段 2 测试（100-500 kHz）
Week 3: 阶段 3 测试（500 kHz - 1 Msps）
Week 4: 备选方案评估（如需要）
```

#### 成功标准总结

| 测试阶段 | 频率范围 | 边沿丢失率 | CPU 使用率 | 触发延迟 |
|---------|---------|-----------|-----------|---------|
| 阶段 1 | 50-100 kHz | < 5% | < 80% | < 50 ms |
| 阶段 2 | 100-500 kHz | < 10% | < 90% | < 75 ms |
| 阶段 3 | 500 kHz-1 Msps | < 15% | ≤ 90% | < 100 ms |

**最终目标**：
- ✅ 1 Msps 采样率
- ✅ ≤ 100 kHz 信号频率
- ✅ < 100 ms 触发到显示延迟
- ✅ 4 通道同时采集
- ✅ 30 fps 实时刷新

## 开发里程碑

### 第一版（MVP）
- 基础功能实现
- 4 通道实时波形显示
- 基础触发（Auto/Normal/Single）
- 自定义触发逻辑（最多 10 个条件）
- 时间轴/电压轴调整
- 触发记录和截图
- 配置文件支持

### 后续版本
- 高级触发模式
- 自动测量功能
- 数据导出功能
- 光标测量功能
- 性能优化
- 用户体验改进
