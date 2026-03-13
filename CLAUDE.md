# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个**激光终端指向误差分析系统**，用于处理卫星遥测数据并计算激光通信终端的指向误差。项目包含完整的数据处理流水线，从原始遥测数据到最终误差统计分析。

## 核心功能

### 数据处理流程

项目遵循严格的三阶段处理流水线：

1. **数据预处理**：按遥测包分流、长格式转宽格式、异常值检测（物理范围+3σ统计+变化率突变）、时间轴有效性图生成（避开时间类参数）、汇总甘特图展示数据覆盖情况
2. **状态筛选**：严格按终端参数表提取参数（包含公共参数）、时间对齐（1Hz整秒时间轴）、有效数据筛选（状态=6）、连续时间段识别、session标记、过渡期丢弃、插值处理（有效session内线性插值+状态值前向填充）、甘特图可视化数据分布（无效数据白色、有效原始数据浅色、插值数据深色）
3. **指向误差计算**：计算方位/俯仰/综合指向误差（含方位角环绕处理）、统计分析、可视化

### 关键技术特点

- 多层异常值检测策略
- 差异化插值方法
- 统一时间轴重采样（1Hz）
- 完整的数据质量评估与报告生成
- 严格的流程控制（不可跳步）

## 项目结构

```
激光指向误差计算/
├── ori-data/              # 原始卫星遥测数据
│   ├── 31star/            # A31星数据
│   ├── 32star/            # A32星数据
│   └── 61star/            # A61星数据
├── src/                   # 处理过程代码
│   ├── check_flags.py
│   ├── debug_full_flow.py
│   ├── debug_outlier.py
│   ├── debug_sessions.py
│   ├── debug_state_values.py
│   ├── debug_step1_data.py
│   ├── debug_step1_keys.py
│   ├── debug_step2.py
│   ├── final_verification.py
│   ├── rerun_step2.py
│   ├── validate_data_consistency.py
│   ├── verify_complete.py
│   ├── verify_step1.py
│   ├── verify_step1_complete.py
│   └── verify_step2_step3.py
├── output/                # 输出结果目录
│   ├── step1-preprocessing/
│   ├── step2-state-filter/
│   └── step3-error-calc/
├── param_mapping_jg01.py   # A27~A36星参数映射
├── param_mapping_jg02.py   # A57~A66星参数映射
├── CLAUDE.md               # 项目文档
└── 需求文档-new.md         # 详细需求文档和执行规范
```

## 参数映射文件

### param_mapping_jg01.py - A27~A36星参数映射

包含213个遥测参数的详细映射，分为：
- 热控温度类（DBF本体、射频单元、相控阵温度等）
- SADA参数（A/B轴角速度、角度等）
- 姿轨控制（星敏感器数据、反作用轮转速、姿态角等）
- 轨道数据（轨道位置、速度、六根数等）
- 激光A参数（激光终端状态、电机位置、温度等）
- 激光B1/B2参数（捕跟工作状态、角误差耦合器等）

### param_mapping_jg02.py - A57~A66星参数映射

包含220个遥测参数的详细映射，激光A参数前缀从"A3慢"改为"A1慢3"，新增激光A2相关参数（TMJA8000系列）。

## 激光终端配置

### 终端参数对应关系

| 终端 | 关键状态参数 | 有效状态值 | 参数来源包 |
|------|-------------|-----------|-----------|
| A1-1 | TMJA3115    | 6         | 0x134     |
| A1-2 | TMJA3239    | 6         | 0x134     |
| B1   | TMJB3031    | 6         | 0x136     |
| B2   | TMJB4031    | 6         | 0x138     |

### 公共参数

所有终端均需包含的温度参数（按实际来源包）：
- TMR137-TMR139：DBF本体及安装面温度（来自packageCode = 0x81）
- TMR185-TMR193：L射频单元温度（来自packageCode = 0x82）
- TMR200-TMR201：Ka接收相控阵温度（来自packageCode = 0x82）

### 可视化标准

#### Step 1 图表规范

- **时间轴图**：
  - 参数选择：避开时间类参数（当前轨道时间秒、微秒、卫星时间秒值、毫秒值、星上时间秒、毫秒）
  - 颜色方案：物理量值（蓝色）、异常值区域（红色）
  - 输出文件：`{star}_pkg_{pkg_code}_timeline.png`

- **汇总甘特图**：
  - 目的：展示各遥测包的数据覆盖情况
  - 颜色方案：无数据（白色）、有数据（蓝色）
  - 输出文件：`summary_packages_gantt.png`

#### Step 2 甘特图规范

- **数据分布甘特图**：
  - 颜色方案：
    - 无效数据：白色
    - 有效数据（原始值）：浅蓝色 (#87CEEB)
    - 有效数据（插值值）：红色 (#FF6B6B)
  - 时间轴：完整1Hz时间轴
  - 输出文件：`{terminal}_valid_distribution.png`

## 需求文档要点

### 需求文档-new.md

这是项目的核心执行规范，包含：
- 详细的三阶段处理流程
- 可配置参数定义
- 数据筛选和插值规则
- 误差计算公式（含方位角环绕处理）
- 输出文件格式和内容要求
- 快速错误排查指南

### 关键公式

**方位角环绕处理（跨0°/360°时避免假误差）：**
```python
delta_A = (A_t - A_r + 180) % 360 - 180  # 归一化到 [-180°, 180°)
```

**综合指向误差：**
```python
theta_error = sqrt((delta_A * cos(radians(E_r)))**2 + delta_E**2)
```

## 执行规范

### 严格执行原则

1. 所有步骤按顺序执行，不得跳步或合并
2. 可配置参数在代码顶部以常量定义
3. 所有输出文件落盘后再进入下一步
4. 列名统一使用遥测中文名称（输出文件）
5. 内部处理时保留参数代号映射
6. 参数提取严格按照需求文档中的参数表执行，确保完整性
7. 插值处理只在有效session内进行，标记插值数据

### 可配置参数

```python
# 异常值检测
OUTLIER_SIGMA = 3              # σ 倍数阈值
OUTLIER_MIN_SEGMENT = 5        # 连续异常段最小长度（点数）

# 状态筛选
CONTINUITY_GAP_SEC = 10        # 时间间隙阈值（秒）
SESSION_TRANSIENT_DROP = 10    # 状态切换后丢弃的过渡期时长

# 统一时间轴
RESAMPLE_FREQ = '1S'           # 目标采样率（1Hz）
VALID_STATE_VALUE = '6'        # 有效状态值
```

## 输出目录结构

```
output/
├── step1-preprocessing/       # 预处理输出
│   ├── reports/              # 数据分析报告
│   ├── plots/                # 可视化图表
│   └── results/              # 宽格式CSV文件
├── step2-state-filter/       # 状态筛选输出
│   ├── reports/              # 筛选报告
│   ├── plots/                # 有效数据分布图表
│   └── results/              # 终端处理后CSV文件
└── step3-error-calc/         # 误差计算输出
    ├── reports/              # 误差统计报告
    ├── plots/                # 误差可视化图表
    └── results/              # 误差计算结果CSV文件
```

## 快速错误排查

| 症状 | 可能原因 | 检查点 |
|------|---------|--------|
| 宽格式CSV列数异常 | paramCode未在映射中找到 | 检查参数映射文件加载（jg01 vs jg02）|
| 方位误差~360°峰值 | 未做环绕处理 | 确认使用正确的delta_A计算公式 |
| 有效数据量为零 | 状态参数从未等于6 | 检查状态参数唯一值和配置 |
| 插值导致长段填充 | 连续NaN段过长 | 检查CONTINUITY_GAP_SEC配置 |
| 公共参数全为NaN | 温度包未正确merge | 确认从packageCode=0x82或0x83提取 |

## 常用命令

### 完整流程运行

```bash
# 运行完整三阶段处理流程（推荐）
python src/verify_complete.py

# 仅使用已有数据验证结果
python src/final_verification.py
```

### 分步验证

```bash
# Step 1: 仅预处理
python src/verify_step1.py

# Step 1（完整版）: 预处理带完整报告
python src/verify_step1_complete.py

# Step 2 & 3: 状态筛选和误差计算
python src/verify_step2_step3.py
```

## 代码架构

### 核心脚本说明

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `src/verify_complete.py` | 完整三阶段流水线 | ori-data/* 原始CSV | output/ 完整输出 |
| `src/final_verification.py` | 利用已有Step1数据验证Step2+3 | output/step1-preprocessing/ | output/step3-error-calc/ |
| `src/verify_step1.py` | 仅Step1预处理示例 | ori-data/* | output/step1-preprocessing/ |
| `param_mapping_jg01.py` | A27~A36星参数映射 | - | PARAM_MAPPING字典 |
| `param_mapping_jg02.py` | A57~A66星参数映射 | - | PARAM_MAPPING字典 |

### 数据流转架构

```
原始CSV (长格式)
    ↓
[Step 1] 按packageCode分流 → pivot宽格式 → 异常检测标记 → 列名中文化
    ↓
{star}_pkg_{pkgCode}_wide.csv
    ↓
[Step 2] 终端参数提取 → 时间对齐(1Hz) → 状态筛选(状态=6) → 插值
    ↓
{terminal}_raw.csv, {terminal}_processed.csv
    ↓
[Step 3] 指向误差计算(delta_A/delta_E/theta_error) → 统计分析 → 可视化
    ↓
error_{terminal}.csv, error_statistics.md, *.png
```

### 关键函数入口

- `verify_complete.py:step1_preprocessing()` - 预处理入口
- `verify_complete.py:step2_state_filter()` - 状态筛选入口
- `verify_complete.py:step3_error_calc()` - 误差计算入口
- `final_verification.py:main()` - 快速验证入口

### 卫星分组规则

```python
STAR_GROUP = {
    'jg01': ['A27', 'A28', 'A29', 'A30', 'A31', 'A32', 'A33', 'A34', 'A35', 'A36'],
    'jg02': ['A57', 'A58', 'A59', 'A60', 'A61', 'A62', 'A63', 'A64', 'A65', 'A66'],
}
```

## 开发指南

### 添加新卫星处理

1. 根据卫星编号选择参数映射文件（jg01或jg02）
2. 将原始CSV放入 `ori-data/{XXstar}/` 目录
3. 修改验证脚本中的输入路径
4. 运行 `verify_complete.py`

### 调试单个步骤

1. 先运行 `verify_step1.py` 确认预处理正确
2. 再运行 `verify_step2_step3.py` 或 `final_verification.py`
3. 检查 `output/` 各子目录下的中间结果

### 参数配置

所有可配置参数在各脚本顶部以常量定义：
- `OUTLIER_SIGMA = 3` - 异常值σ阈值
- `VALID_STATE_VALUE = 6` - 有效状态值
- `CONTINUITY_GAP_SEC = 10` - 时间间隙阈值
- `SESSION_TRANSIENT_DROP = 10` - 过渡期丢弃时长
- `RESAMPLE_FREQ = '1S'` - 重采样频率

## 注意事项

1. 严格按照需求文档的执行顺序进行开发
2. 所有可配置参数在代码顶部统一定义
3. 输出文件列名使用遥测中文名称
4. 处理过程中保留完整的中间结果落盘
5. 各阶段输出目录结构清晰且规范
