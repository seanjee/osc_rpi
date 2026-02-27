# Raspberry Pi 5 数字示波器 — SPEC（系统 + 模块）

本文档基于 `PRD.md` / `config/osc_config.yaml` / `config/trigger_conditions.yaml` 与现有硬件测试代码（libgpiod C++）整理，用于后续生成“可维护、可测试、模块化”的完整应用程序。

目标：
- 模块边界清晰；Bug/需求变更能定位到单模块
- 每个模块都有独立单元测试（不依赖真实GPIO/GUI，除非标注为集成测试）
- 关键硬件约束显式化（Raspberry Pi 5 RP1 GPIO：`/dev/gpiochip4`）

---

## 1. 系统 SPEC

### 1.1 运行环境与约束

- 硬件：Raspberry Pi 5
- OS：Ubuntu 24.04 LTS（来自 `PRD.md:6`）
- GPIO：所有示波器输入通道位于 `/dev/gpiochip4`（RP1 控制器）（来自 `PRD.md:48` 与 `config/osc_config.yaml`）
- 输入信号：方波为主，幅度 **不超过 3.3V**（来自 `TEST_WIRING.md:31-36`）

### 1.2 关键性能指标（来自 PRD）

来自 `PRD.md:12-19`：
- 最大采样频率：1 Msps（⚠需高频验证，先按目标设计）
- 测量信号频率：≤ 100 kHz
- 采样深度：100k 点
- 实时刷新率：30 fps（左上区域）
- 触发到显示延迟：< 100 ms（不包括 PNG/CSV 保存，保存异步）
- CPU/GPU 负载限制：≤ 90%

### 1.3 功能范围（MVP 必须实现）

依据 `PRD.md`：

#### 1.3.1 多通道采样
- 4 通道 + 外部触发（配置中存在）（`PRD.md:40-48`, `config/osc_config.yaml`）
- 采样频率自动调整策略（见 1.4）

#### 1.3.2 触发系统
- 模式：Auto / Normal / Single（`PRD.md:151-155`）
- 触发源：CH1-CH4 或外部触发（`PRD.md:156-159`）
- 触发电平：0-5V，精度 1mV（`PRD.md:160-163`）
- 边沿类型：Rising / Falling / Both（`PRD.md:165-168`）
- Holdoff：10 μs - 10 s（`PRD.md:170-173`）
- 自定义触发逻辑：文本表达式（选项B），支持 AND/OR/NOT 与 `within X ms/us after/before`（`PRD.md:175-216`；示例见 `trigger_conditions.yaml`）

#### 1.3.3 GUI（2x2 四区）
- 左上：实时波形 + 当前采样频率（`PRD.md:54-64`）
- 左下：设置按钮 + CPU/GPU 状态（`PRD.md:65-70`）
- 右上：触发快照 + 时间戳 `YYYY-MM-DD HH:MM:SS.mmm`，自动保存 PNG（`PRD.md:71-76`）
- 右下：触发记录滚动文本（最近 100 条）+ 同步记录 CSV（`PRD.md:77-82`）

#### 1.3.4 配置
- 从 `config/osc_config.yaml` 加载：通道映射、采样参数、显示参数、触发默认值、快捷键、性能限制。
- 从 `config/trigger_conditions.yaml` 加载：预定义触发表达式 + 当前激活条件。

### 1.4 采样频率自动调整（来自 PRD）

依据 `PRD.md:28-35`：
- 自动调整：随时间轴跨度变化自动计算
- 计算公式（安全系数 1.2）：
  - `fs = depth / (time_span * divs * 1.2)`
- 采样频率限制：1 kHz - 1 Msps
- 使用固定档位表提高稳定性：`1k, 2k, 5k, 10k, 20k, 50k, 100k, 200k, 500k, 1M`

注：PRD没有明确“time_span”的单位与与 `μs/div` 的换算方式；实现时按 GUI 的 timebase 表（`PRD.md:131-135`）定义每档 `μs/div ... s/div`，`time_span = seconds_per_div`。

### 1.5 数据与持久化

来自 `config/osc_config.yaml:45-51` 与 `PRD.md:71-82`：
- 截图路径：`./screenshots/`
- 触发日志 CSV：`./logs/trigger_log.csv`
- 触发记录最多 100 条（配置：`display.trigger_record_max`）

要求：
- PNG/CSV 保存必须异步，不应阻塞触发到显示路径（`PRD.md:23`）。

### 1.6 系统架构（模块化与可测试性）

采用分层架构：

1) **Domain/Core（纯逻辑，可100%单测）**
- 触发表达式解析与评估
- 采样频率规划器（timebase → fs 档位）
- 波形数据结构与降采样/显示数据准备
- 事件/记录格式化

2) **Adapters/Drivers（硬件/OS 依赖，可用mock替代）**
- GPIO采样器（真实：libgpiod/或pigpio；单测用 FakeGPIOEdgeSource）
- 性能监控（真实读取系统指标；单测用 FakeMetricsProvider）
- 存储（PNG/CSV写入；单测用 InMemoryWriter）

3) **Application/Use-cases（业务编排，可用mock单测）**
- 采样线程管理、触发流程、状态机
- 数据流：采样 → 触发判定 → UI更新 → 异步保存/记录

4) **UI（GUI框架依赖，尽量薄；以集成测试为主）**
- 2x2布局与控件绑定

### 1.7 线程与实时性约束

- 采样/触发判定必须与GUI渲染解耦（PRD强调刷新与采样权衡，且保存异步）。
- 推荐线程模型：
  - Thread A：GPIO采样/事件采集（高优先）
  - Thread B：触发引擎（消费采样数据，输出“触发发生 + 波形窗口”）
  - Thread C：GUI主线程（30fps渲染/交互）
  - Thread D：异步IO（PNG/CSV写入）

线程间通信：
- 使用无锁/低锁队列或有界队列；明确背压策略（超过队列容量时丢弃“非触发实时数据”，但不丢触发事件）。

### 1.8 错误处理与可诊断性

- 所有模块必须返回结构化错误（错误码 + 可读信息）。
- 触发表达式解析错误必须能定位到具体 token/位置。
- 运行时必须能显示/记录：当前采样率、触发模式/源/电平/边沿、GPIO芯片路径与line映射。

### 1.9 测试策略（必须）

- 单元测试：Core + Use-case + Adapters 的 mock 版本
- 集成测试：
  - “无硬件”集成：FakeGPIO事件流驱动整套触发/记录/保存（不含真实GUI或使用headless）
  - “有硬件”验收：沿用现有 `multi_channel_freq_test.cpp` / `high_freq_stress_test.cpp` / `latency_test.cpp` 作为外部验证工具（不纳入单元测试）

---

## 2. 模块 SPEC

以下模块是建议的最终应用程序代码组织（目录名/语言可调整，但边界与接口要求必须保持）。

### 2.1 `config` — 配置加载与校验

**职责**
- 读取 `config/osc_config.yaml` 与 `config/trigger_conditions.yaml`
- 提供强类型配置对象（channels/sampling/display/trigger/hotkeys/performance）
- 做静态校验：必填字段、范围、快捷键冲突、路径合法性

**输入/输出**
- 输入：YAML 文件路径
- 输出：
  - `OscConfig`
  - `TriggerConditionsConfig`

**关键规则（来自现有文件）**
- 默认GPIO chip：`/dev/gpiochip4`（`osc_config.yaml`）
- trigger日志路径：`./logs/trigger_log.csv`（`osc_config.yaml:50-51`）

**单元测试**
- 正常加载：给定最小配置样例可生成对象
- 校验失败：
  - channel line重复
  - hotkeys重复（PRD提过冲突风险）
  - sampling.max_frequency 超过1e6 或小于1e3

---

### 2.2 `sampling.planner` — 采样频率规划器

**职责**
- 根据 timebase（如 `μs/div`）与 `depth` 计算目标采样率
- 应用安全系数1.2（`PRD.md:31-33`）
- 量化到固定档位表（`PRD.md:34`）
- 限幅到 [1k, 1M]

**接口**
- `plan_sample_rate(depth_points, seconds_per_div, divs=10) -> SamplePlan{requested_fs, quantized_fs}`

**单元测试**
- 给定一组 timebase 档位，验证输出落在固定档位表
- 边界：极小/极大 timebase 时正确夹紧

---

### 2.3 `drivers.gpio` — GPIO 采样驱动抽象层

**职责**
- 为上层提供统一的采样/事件流接口

**抽象接口（必须可mock）**
- `IGpioEdgeSource`：
  - `start()` / `stop()`
  - `read_events(timeout) -> list[EdgeEvent]`
- `EdgeEvent` 包含：channel_id、timestamp（高精度单调时钟）、edge_type（R/F）或 level变化

**实现要求（观察到的可行方式）**
- libgpiod C++ 的事件读取模式：`EVENT_BOTH_EDGES` + `event_read_multiple()`（见 `multi_channel_freq_test.cpp`、`high_freq_stress_test.cpp`）

**单元测试**
- 用 `FakeGpioEdgeSource` 生成确定性边沿序列
- 驱动适配层的单测只测“事件转换/时间戳单位/通道映射”逻辑，不依赖真实 `/dev/gpiochip4`

---

### 2.4 `core.waveform` — 波形数据模型与显示准备

**职责**
- 维护每通道的采样缓冲区（长度=depth）
- 提供“显示用降采样/抽取”的纯函数

**数据结构**
- `WaveformBuffer[channel]`：环形缓冲
- `DisplayTrace`：与像素宽度对应的点列（每列取 min/max 或取代表点）

**单元测试**
- 环形缓冲边界：写满后覆盖正确
- 降采样：输入已知波形（方波/脉冲），输出 min/max 保留边沿

---

### 2.5 `core.trigger.dsl` — 触发表达式 DSL（解析）

**职责**
- 解析 PRD 指定的文本触发语法（选项B）
- 输出 AST

**语法（仅基于已观察内容）**
来自 `PRD.md:185-208` 与 `trigger_conditions.yaml` 示例：
- 基本条件：
  - `CHn Rising` / `CHn Falling` / `CHn Both Edges`
  - `CHn = High`（电平条件）
- 逻辑：`AND` / `OR` / `NOT`
- 括号：`()`, 以及示例里出现的 `[]`（`trigger_conditions.yaml:23`）
- 时间窗口：`within <N><unit> after/before <event>`
  - unit 示例：`ms`, `μs`（PRD文字中出现 `100μs`）

**输出**
- `AstNode`（And/Or/Not/EdgeEvent/LevelCondition/WithinWindow...）

**单元测试**
- 用 `trigger_conditions.yaml` 中每条 expression 做 parser 回归测试
- 语法错误：缺括号、未知token、非法时间单位，必须返回错误位置

---

### 2.6 `core.trigger.engine` — 触发引擎（评估 + 状态机）

**职责**
- 在事件流上评估 DSL 条件
- 支持 Auto/Normal/Single 模式
- 支持 holdoff
- 支持 trigger source（单通道/外部）+ edge type + level

**接口**
- `TriggerEngine.process(events, current_time) -> list[TriggerEvent]`
- `TriggerEvent` 包含：timestamp、触发条件名/表达式、各通道状态摘要

**单元测试**
- Auto：即使不满足条件也周期触发（需定义策略：PRD描述“无触发条件时自动触发”）
- Normal：只有满足条件才触发
- Single：触发一次后停止，直到用户重置
- holdoff：触发后窗口内不再触发
- within after/before：
  - 生成CH1 rising 与 CH2 rising 在 10ms 内的事件序列 → 应触发
  - 超过10ms → 不触发

---

### 2.7 `app.controller` — 应用编排（Use-case 层）

**职责**
- 管理采样线程/驱动生命周期
- 将 TriggerEngine 的 TriggerEvent 转换为 UI 状态更新
- 管理触发记录队列（最多100条，来自 PRD）
- 触发时生成截图/日志写入任务（异步）

**接口**
- `start()` / `stop()`
- `set_timebase(...)`, `set_trigger_mode(...)`, `set_trigger_expression(...)`, `toggle_channel(...)` 等

**单元测试**
- 用 FakeGpioEdgeSource 驱动：触发一次 → 触发记录增加 → 异步写入任务被提交
- 记录上限：>100 条时淘汰最旧

---

### 2.8 `metrics` — CPU/GPU 负载监控

**职责**
- 向 UI 提供 CPU/GPU 使用率（PRD要求显示系统负荷）

**注意**
- 当前 repo 只有 C++ 测试里实现了 CPU/memory 读取（`high_freq_stress_test.cpp` 使用 `/proc/stat` 与 `getrusage`）；GPU 获取方式 PRD 未给出，因此模块需支持“GPU不可用”状态。

**接口**
- `IMetricsProvider.get()` → `{cpu_percent, gpu_percent_or_none, mem_mb, ...}`

**单元测试**
- Fake provider 返回固定值，UI/Controller 显示逻辑正确

---

### 2.9 `storage` — PNG 截图与 CSV 触发日志

**职责**
- 保存右上角触发快照 PNG
- 追加写入 `./logs/trigger_log.csv`

**约束**
- 必须异步，不阻塞触发到显示路径（`PRD.md:23`）

**接口**
- `ISnapshotWriter.write_png(image, timestamp)`
- `ITriggerLogWriter.append(record)`

**单元测试**
- InMemoryWriter：验证写入参数/文件名格式
- CSV：字段顺序与时间戳格式正确（`YYYY-MM-DD HH:MM:SS.mmm`）

---

### 2.10 `ui` — 2x2 GUI（薄层）

**职责**
- 呈现 PRD 的四区布局与交互
- 将按钮/快捷键映射到 Controller
- 30fps 更新左上波形

**输入**
- `OscViewModel`：
  - traces（每通道显示数据）
  - sample_rate
  - trigger status
  - snapshot image
  - trigger log lines
  - cpu/gpu

**测试**
- UI 单测不强制；优先做到：
  - ViewModel mapping 的单测（纯函数）
  - GUI 集成测试（可选/后续）

---

## 3. 模块间依赖规则（为了可维护）

- `core.*` 不允许依赖 `drivers.*`、`ui`、文件系统
- `drivers.*` 不允许依赖 `ui`
- `app.controller` 允许依赖 `core.*`、`drivers.*`、`storage`、`metrics`
- `ui` 仅依赖 `app.controller` 与 `viewmodel`，不直接访问 GPIO/文件

---

## 4. 验收与对齐（与现有验证工具共存）

- 应用程序功能验收：基于 PRD 的 2x2 界面、触发逻辑、记录与截图。
- 性能/硬件验收：继续使用当前目录保留的 C++ 测试工具：
  - `multi_channel_freq_test.cpp`
  - `high_freq_stress_test.cpp`
  - `latency_test.cpp`

这些属于“外部硬件验证”，不作为应用单元测试的一部分。
