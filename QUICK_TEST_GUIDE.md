# 快速测试指南

## 使用说明

所有测试程序现在支持**每次只测试一个频率**，让您有足够的时间设置信号发生器。

## 运行方式

### 方式1：交互式选择（推荐）

直接运行程序，程序会列出所有可用频率，让您选择：

```bash
# Stage 1: 多通道测试
sudo ./multi_channel_freq_test

# Stage 2: 压力测试
sudo ./high_freq_stress_test

# Stage 3: 延迟测试
sudo ./latency_test
```

**测试流程：**
1. 程序显示可用频率列表
2. 输入要测试的频率编号（例如：1）
3. 程序显示："请设置信号发生器频率: XXX Hz"
4. 手动设置信号发生器到指定频率
5. 按回车键开始测试
6. 等待测试完成，查看结果
7. 重新运行程序测试下一个频率

### 方式2：命令行参数

```bash
# 列出所有可用频率
sudo ./multi_channel_freq_test --list

# 通过索引指定频率
sudo ./multi_channel_freq_test 1        # 选择索引1（50 kHz）

# 通过频率值指定
sudo ./multi_channel_freq_test 50000    # 直接指定50 kHz

# Stage 2 压力测试
sudo ./high_freq_stress_test 1          # 选择200 kHz
sudo ./high_freq_stress_test 200000     # 直接指定200 kHz

# Stage 3 延迟测试
sudo ./latency_test 2                    # 选择1 MHz
sudo ./latency_test 1000000             # 直接指定1 MHz
```

## 测试频率清单

### Stage 1: 多通道测试
```
[0] 10 kHz (baseline)  - 基准测试 ✅ PASS
[1] 20 kHz             - 频率边界 ✅ PASS
[2] 30 kHz             - 频率边界 ✅ PASS
[3] 35 kHz             - 细化边界 ⏳ 待测试（优先级1）
[4] 40 kHz             - 边界测试 ❌ FAIL (CH3: 10.78%)
[5] 45 kHz             - 验证边界 ⏳ 待测试
[6] 50 kHz             - 失败 ❌ FAIL
[7] 75 kHz             - 高频测试 ⏳ 待测试
[8] 100 kHz            - 高频测试 ⏳ 待测试
```

### Stage 2: 压力测试
```
[0] 100 kHz  - 60秒测试
[1] 200 kHz  - 60秒测试
[2] 500 kHz  - 60秒测试
```

### Stage 3: 延迟测试
```
[0] 500 kHz  - 验证<100ms延迟
[1] 750 kHz  - 高频延迟
[2] 1 Msps   - 最高频率
```

## 完整测试流程示例

### 步骤1：Stage 1 多通道测试

**重要**：10-30 kHz 通过，40 kHz 失败（CH3: 10.78%），需要找到边界。

```bash
# 测试 35 kHz（优先级1 - 细化边界）
sudo ./multi_channel_freq_test
# 选择 3
# 设置信号发生器为 35 kHz
# 按回车，等待结果
# 观察通道3 (GPIO23) 的表现

# 如果 35 kHz 通过，继续测试更高频率
# 测试 45 kHz
sudo ./multi_channel_freq_test
# 选择 5
# 设置信号发生器为 45 kHz
# 按回车，等待结果
```

### 步骤2：Stage 2 压力测试

```bash
# 测试 100 kHz（60秒）
sudo ./high_freq_stress_test
# 选择 0
# 设置信号发生器为 100 kHz
# 按回车，等待60秒

# 测试 200 kHz（60秒）
sudo ./high_freq_stress_test
# 选择 1
# 设置信号发生器为 200 kHz
# 按回车，等待60秒

# 测试 500 kHz（60秒）
sudo ./high_freq_stress_test
# 选择 2
# 设置信号发生器为 500 kHz
# 按回车，等待60秒
```

### 步骤3：Stage 3 延迟测试

```bash
# 测试 500 kHz
sudo ./latency_test
# 选择 0
# 设置信号发生器为 500 kHz
# 按回车

# 测试 750 kHz
sudo ./latency_test
# 选择 1
# 设置信号发生器为 750 kHz
# 按回车

# 测试 1 Msps
sudo ./latency_test
# 选择 2
# 设置信号发生器为 1000 kHz (1 MHz)
# 按回车
```

## 通过标准

### Stage 1 通过标准
- 所有4个通道边沿丢失率 < 5%
- 测量频率与设置频率误差 < 1%

### Stage 2 通过标准
- 边沿丢失率 < 10%
- CPU 使用率 < 90%
- 性能稳定（波动 < 20%）

### Stage 3 通过标准
- 触发到显示延迟 < 100 ms

## 快速参考

```bash
# 查看所有可用频率
sudo ./multi_channel_freq_test --list

# 快速测试10 kHz
sudo ./multi_channel_freq_test 0

# 快速测试100 kHz
sudo ./multi_channel_freq_test 3

# 快速测试500 kHz压力
sudo ./high_freq_stress_test 2

# 快速测试1 MHz延迟
sudo ./latency_test 2
```

## 注意事项

1. **重要**：所有4个通道必须接在同一信号源上
2. 每次测试前，请确保信号发生器已设置到正确的频率
3. 测试过程中请勿更改信号频率
4. Stage 2 每个频率测试60秒，请耐心等待
5. 如果需要取消测试，按 Ctrl+C

## 故障排除

### 程序没有提示设置频率
- 确保使用的是最新编译的程序
- 运行 `./compile_multi_channel_test.sh` 重新编译

### 看不到可用频率列表
- 确保使用 `--list` 参数
- 检查程序编译是否成功

### 测试结果全部为0
- 检查信号发生器是否开启
- 检查接线是否正确
- 确认已设置为指定频率

### CPU使用率过高
- 关闭其他后台程序
- 检查是否有其他GPIO程序运行

## 常用命令速查

```bash
# Stage 1 - 频率边界查找
sudo ./multi_channel_freq_test 0      # 10 kHz ✅ PASS
sudo ./multi_channel_freq_test 1      # 20 kHz ✅ PASS
sudo ./multi_channel_freq_test 2      # 30 kHz ✅ PASS
sudo ./multi_channel_freq_test 3      # 35 kHz ⏳ PENDING (优先级1)
sudo ./multi_channel_freq_test 4      # 40 kHz ❌ FAIL (CH3: 10.78%)
sudo ./multi_channel_freq_test 5      # 45 kHz ⏳ PENDING
sudo ./multi_channel_freq_test 6      # 50 kHz ❌ FAIL
sudo ./multi_channel_freq_test 7      # 75 kHz ⏳ PENDING
sudo ./multi_channel_freq_test 8      # 100 kHz ⏳ PENDING

# Stage 2
sudo ./high_freq_stress_test 0        # 100 kHz
sudo ./high_freq_stress_test 1        # 200 kHz
sudo ./high_freq_stress_test 2        # 500 kHz

# Stage 3
sudo ./latency_test 0                 # 500 kHz
sudo ./latency_test 1                 # 750 kHz
sudo ./latency_test 2                 # 1 MHz
```
