# Raspberry Pi 5 数字示波器 PRD

## 项目概述

使用当前 Raspberry Pi 5 制作一个可以自定义触发条件的数字示波器，用于捕捉特定的输入信号模式是否发生。

## 性能指标

| 参数 | 规格 |
|------|------|
| 最大采样频率 | 1 Msps |
| 测量信号频率 | 100 kHz |
| 采样深度 | 100k 点 |
| 实时刷新率 | 30 fps (左上区域) |
| 触发后画面更新延迟 | < 100 ms |
| CPU/GPU 负载限制 | ≤ 90% |

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

| 通道 | GPIO 编号 | 物理引脚 | 默认配置 | 备注 |
|------|-----------|----------|----------|------|
| 通道1 | GPIO5 | 29脚 | 已配置 | 通用 GPIO |
| 通道2 | GPIO6 | 31脚 | 已配置 | 通用 GPIO |
| 通道3 | - | - | 待配置 | 配置文件中指定 |
| 通道4 | - | - | 待配置 | 配置文件中指定 |
| 外部触发 | - | - | 待配置 | 配置文件中指定 |

**注意**：通道 1 和 2 为默认配置，通道 3 和 4 需在配置文件中设置。

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
- 显示内容：实时波形、当前采样频率
- 触发生效时更新，但可能根据触发方式不一定一直保持

### 左下区域：示波器设置
- 示波器设置按钮（全部采用按钮，不使用旋钮）
- 每个按钮对应快捷键，按键名以小字显示在按钮旁边
- 快捷键在配置文件中定义
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
- `Y Scale Up`：增加电压轴范围（放大波形）
- `Y Scale Down`：减小电压轴范围（缩小波形）
- `Y Position Up`：向上移动波形
- `Y Position Down`：向下移动波形

### 触发设置
- `Trig Auto`：自动触发模式
- `Trig Normal`：正常触发模式
- `Trig Single`：单次触发模式
- `Trig Level Up`：增加触发电平
- `Trig Level Down`：降低触发电平
- `Holdoff`：触发保持时间设置

**注意**：触发电平调整有两个按钮（增加/降低），每个按钮都有对应的键盘快捷键

### 其他
- `Help`：帮助对话框
- `About`：关于对话框
- `Fullscreen`：全屏模式切换

**注意**：所有按钮需在配置文件中定义快捷键映射。

## 时间轴和电压轴设置

### 时间轴 (X Axis)
- **跨度范围**：10 μs/div 到 10 s/div
- **调整步进**：1, 2, 5, 10（与 Y 轴相同）
- **Div 数**：固定为 10 div
- **推荐档位序列**：
  ```
  10μs, 20μs, 50μs, 100μs, 200μs, 500μs,
  1ms, 2ms, 5ms, 10ms, 20ms, 50ms,
  100ms, 200ms, 500ms, 1s, 2s, 5s, 10s
  ```

### 电压轴 (Y Axis)
- **范围**：0 - 5V（树莓派 GPIO 可接受范围）
- **显示预留空间**：上下各预留约 10% 空间
- **调整步进**：1, 2, 5, 10
- **推荐档位序列**：0.1V/div, 0.2V/div, 0.5V/div, 1V/div, 2V/div, 5V/div
- **所有通道共用**：所有通道共用 Y 轴和 X 轴设置

### 网格线
- **密度**：与 div 对齐（每个 div 一条网格线）
- **颜色**：灰色半透明
- **样式**：实线或虚线

## 触发方式

### 基础触发模式
- **Auto**：自动触发（无触发条件时自动触发）
- **Normal**：正常触发（必须满足触发条件）
- **Single**：单次触发（触发一次后停止）

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
| 文件 | CSV | 所有触发记录 | 无限制 |
| 文件 | PNG | 最近 100 次触发截图 | 100 张 |

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
  y_scale_up: "Up"
  y_scale_down: "Down"
  x_position_up: "Shift+Right"
  x_position_down: "Shift+Left"
  y_position_up: "Shift+Up"
  y_position_down: "Shift+Down"
  trig_auto: "A"
  trig_normal: "N"
  trig_single: "S"
  trig_level_up: "W"
  trig_level_down: "S"
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
- **GUI 框架**：PyQt6 / PySide6
- **GPIO 控制**：Pigpio（DMA 模式）
- **绘图库**：PyQtGraph（高性能实时绘图）
- **配置管理**：PyYAML
- **数据存储**：CSV, PNG

### 性能优化
- 使用 DMA 进行高速采样（1 Msps）
- 多线程架构（采样线程 + GUI 主线程）
- 缓存优化，减少重复计算
- OpenGL 硬件加速绘图

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
