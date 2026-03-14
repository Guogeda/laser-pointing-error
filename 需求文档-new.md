# 激光指向误差分析系统 - 需求文档与执行规范

## 版本历史
- v1.0 - 初始版本
- v1.1 (2026-03-14) - 更新多星数据处理流程，增加jg02组卫星支持，增加链路分析功能

## 一、项目概述

本项目用于处理卫星遥测数据并计算激光通信终端的指向误差，支持多星分组处理、链路配对分析、温度与误差关系分析等功能。

## 二、卫星分组与配置

### 2.1 卫星分组规则

```python
STAR_GROUP = {
    'jg01': ['A27', 'A28', 'A29', 'A30', 'A31', 'A32', 'A33', 'A34', 'A35', 'A36'],
    'jg02': ['A57', 'A58', 'A59', 'A60', 'A61', 'A62', 'A63', 'A64', 'A65', 'A66'],
}
```

### 2.2 参数映射文件

- `param_mapping_jg01.py` - jg01组卫星参数映射（A27~A36）
- `param_mapping_jg02.py` - jg02组卫星参数映射（A57~A66）

### 2.3 终端配置

#### jg01组终端配置
| 终端 | 包代码 | 状态参数 | 状态名称 |
|------|--------|---------|---------|
| B1 | 136 | TMJB3031 | B1慢-捕跟工作状态 |
| B2 | 138 | TMJB4031 | B2慢-捕跟工作状态 |
| A1-1 | 134 | TMJA3115 | A3慢-1-激光终端状态 |
| A1-2 | 134 | TMJA3239 | A3慢-2-激光终端状态 |

#### jg02组终端配置
| 终端 | 包代码 | 状态参数 | 状态名称 |
|------|--------|---------|---------|
| A1-1 | 13B | TMJA3115 | A1慢3-1-激光终端状态 |
| A2-1 | 13F | TMJA8115 | A2慢3-1-激光终端状态 |
| A2-2 | 13F | TMJA8239 | A2慢3-2-激光终端状态 |
| A1-2 | 13B | TMJA3239 | A1慢3-2-激光终端状态 |

## 三、数据处理流程

### 3.1 整体流程架构

```
原始CSV (长格式)
    ↓
[Step 1] 数据预处理：按packageCode分流 → pivot宽格式 → 异常值检测标记 → 列名中文化
    ↓
{star}_pkg_{pkgCode}_wide.csv
    ↓
[Step 2] 状态筛选：终端参数提取 → 时间对齐→ 状态筛选(状态=6) → 插值(1Hz)
    ↓
{terminal}_raw.csv, {terminal}_processed.csv
    ↓
[Step 3] 指向误差计算：delta_A/delta_E/theta_error → 统计分析 → 可视化
    ↓
error_{terminal}.csv, error_statistics.md, *.png
    ↓
[Step 4] 链路分析：链路配对 → 时间对齐 → 误差与温度关系分析 → 报告生成
    ↓
link_analysis_report.md, 链路分析可视化
```

### 3.2 Step 1: 数据预处理

#### 3.2.1 输入数据
- 位置：`ori-data/{star_name}/`
- 格式：CSV长格式，包含字段：origin, satName, addressCode, inTimeOrDelay, satelliteTime, receiveTime, packageCode, paramCode, originalValue, parsedValue, translateValue

#### 3.2.2 处理步骤
1. **按packageCode分流**：将原始数据按遥测包代码分组
2. **长格式转宽格式**：使用pivot_table，以satelliteTime为索引，paramCode为列，parsedValue为值
3. **数值类型转换**：将所有数值列转换为float类型
4. **异常值检测（三层）**：
   - 层1：物理范围检测（温度-20~100℃，俯仰角-90~90°等）
   - 层2：3σ统计检测（滑动窗口60点）
   - 层3：变化率突变检测（99分位数阈值）
5. **连续异常段合并**：连续异常段长度>5点标记为'invalid'
6. **列名中文化**：将paramCode替换为中文名称
7. **输出落盘**：保存为`{star_name}_pkg_{pkg_code}_wide.csv`

#### 3.2.3 输出文件
- `output/{star_name}/step1-preprocessing/results/{star_name}_pkg_{pkg_code}_wide.csv`
- `output/{star_name}/step1-preprocessing/reports/preprocessing_report.md`
- `output/{star_name}/step1-preprocessing/plots/{star_name}_pkg_{pkg_code}_timeline.png`
- `output/{star_name}/step1-preprocessing/plots/summary_packages_gantt.png`

### 3.3 Step 2: 状态筛选与数据处理

#### 3.3.1 输入数据
- Step 1处理后的宽格式CSV文件

#### 3.3.2 处理步骤
1. **提取公共参数**：从温度包（packageCode=0x82或0x81）提取温度参数
2. **终端参数提取**：根据终端配置提取对应参数
3. **时间对齐到1Hz**：
   - 创建整秒时间轴
   - 使用reindex配合method='nearest'，tolerance=500ms
4. **有效性标记**：状态=6标记为有效数据
5. **识别连续时间段**：时间间隙>10秒认为是新的period
6. **过渡期丢弃**：每个period前10秒数据丢弃
7. **插值处理**：
   - 状态参数：前向填充（ffill）
   - 数值参数：线性插值（interpolate）
   - 只在有效session内插值
8. **标记插值数据**：添加`_interp`标记列

#### 3.3.3 公共温度参数（所有终端共用）
- TMR137: RM15-DBF本体
- TMR138: RM16-DBF安装面1(+Z)
- TMR139: RM17-DBF安装面2(-Z)
- TMR185: RM83-L射频单元本体（-Y3-X1）
- TMR191: RM89-L射频单元本体（-Y1+X3）
- TMR192: RM90-L射频单元本体（-Y3+X4）
- TMR193: RM91-L射频单元（-Y1）
- TMR200: RM99-Ka接收相控阵主散热面1(+X)
- TMR201: RM100-Ka接收相控阵主散热面2(-X)

#### 3.3.4 输出文件
- `output/{star_name}/step2-state-filter/results/{terminal}_raw.csv`
- `output/{star_name}/step2-state-filter/results/{terminal}_processed.csv`
- `output/{star_name}/step2-state-filter/reports/state_filter_report.md`
- `output/{star_name}/step2-state-filter/plots/{terminal}_valid_distribution.png`

### 3.4 Step 3: 指向误差计算

#### 3.4.1 输入数据
- Step 2处理后的`{terminal}_processed.csv`文件

#### 3.4.2 误差计算公式
```python
# 方位角环绕处理（跨0°/360°时避免假误差）
delta_A = (A_t - A_r + 180) % 360 - 180  # 归一化到 [-180°, 180°)

# 俯仰误差
delta_E = E_t - E_r

# 综合指向误差
theta_error = sqrt((delta_A * cos(radians(E_r)))**2 + delta_E**2)
```

其中：
- A_t: 方位电机目标位置（或理论方位角）
- A_r: 方位电机当前位置（或实时方位轴角）
- E_t: 俯仰电机目标位置（或理论俯仰角）
- E_r: 俯仰电机当前位置（或实时俯仰轴角）

#### 3.4.3 统计指标
- 均值
- 标准差
- RMS（均方根）
- P95（95分位数）
- P99（99分位数）

#### 3.4.4 输出文件
- `output/{star_name}/step3-error-calc/results/error_{terminal}.csv`
- `output/{star_name}/step3-error-calc/reports/error_statistics.md`
- `output/{star_name}/step3-error-calc/plots/{terminal}_error_timeseries.png`
- `output/{star_name}/step3-error-calc/plots/{terminal}_error_distribution.png`
- `output/{star_name}/step3-error-calc/plots/comparison_azimuth_boxplot.png`
- `output/{star_name}/step3-error-calc/plots/comparison_elevation_boxplot.png`

### 3.5 Step 4: 链路配对分析

#### 3.5.1 链路配对配置
```python
LINK_PAIRS = [
    ('32star', 'B1', '31star', 'A1-1'),  # 32-31链路
    ('31star', 'A1-1', '61star', 'A2-1'),  # 31-61链路
]
```

#### 3.5.2 处理步骤
1. **加载各星处理结果**：读取31star、32star、61star的Step 3误差数据
2. **自动查找可用终端**：检查各星可用的终端
3. **链路数据配对**：
   - 时间对齐到公共时间轴
   - 使用merge按时间对齐
   - 容差：500ms
4. **误差关系分析**：
   - 本端误差与本端温度相关性
   - 本端误差与对端温度相关性
   - 对端误差与对端温度相关性
   - 对端误差与本端温度相关性
5. **统计分析**：Pearson相关系数、p值显著性检验
6. **可视化生成**：散点图、时间序列对比图、热力图

#### 3.5.3 输出文件
- `output/step3-error-calc/reports/link_analysis_report.md`
- `output/step3-error-calc/plots/link_*_scatter.png`
- `output/step3-error-calc/plots/link_*_timeseries.png`
- `output/step3-error-calc/plots/link_*_correlation_heatmap.png`

## 四、可配置参数

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

## 五、数据质量说明

### 5.1 32star数据特征
经过对原始数据的分析，确认32star原始数据本身就存在大量连续重复值，不是Step 1插值造成的。

具体数据特征：
- 包13B (激光A) 中 TMJA3359：100% 的连续相同值
- 包13B 中 TMJA3309：97.6% 的连续相同值
- 包13B 中 TMJA3147：80.3% 的连续相同值
- 包81 (温度包) 中 TMR139：75.4% 的连续相同值

这是32star原始遥测数据的固有特征，与31star和61star的数据特征有所不同。

### 5.2 数据量统计
- 32star：13B包31万行，136/32A/138包各14万行
- 31star：数据量适中
- 61star：数据量适中

## 六、执行命令

### 6.1 完整流程处理单星
```bash
# 处理jg01组卫星（如31star、32star）
python src/verify_complete.py jg01 31star
python src/verify_complete.py jg01 32star

# 处理jg02组卫星（如61star）
python src/verify_complete.py jg02 61star
```

### 6.2 链路配对分析
```bash
# 运行链路分析模块
python src/link_analysis.py
```

## 七、输出目录结构

```
激光指向误差计算/
├── ori-data/                  # 原始卫星遥测数据
│   ├── 31star/
│   ├── 32star/
│   └── 61star/
├── src/                       # 处理过程代码
│   ├── config/
│   │   ├── satellite_groups.py    # 卫星分组配置
│   │   └── link_topology.py       # 链路拓扑配置
│   ├── verify_complete.py         # 完整三阶段处理流程
│   ├── link_analysis.py           # 链路分析模块
│   └── ...
├── output/                    # 输出结果目录
│   ├── 31star/
│   │   ├── step1-preprocessing/
│   │   ├── step2-state-filter/
│   │   └── step3-error-calc/
│   ├── 32star/
│   │   ├── step1-preprocessing/
│   │   ├── step2-state-filter/
│   │   └── step3-error-calc/
│   ├── 61star/
│   │   ├── step1-preprocessing/
│   │   ├── step2-state-filter/
│   │   └── step3-error-calc/
│   └── step3-error-calc/
│       └── reports/link_analysis_report.md
├── param_mapping_jg01.py     # jg01组参数映射
├── param_mapping_jg02.py     # jg02组参数映射
└── 需求文档-new.md           # 本文档
```

## 八、快速错误排查

| 症状 | 可能原因 | 检查点 |
|------|---------|--------|
| 宽格式CSV列数异常 | paramCode未在映射中找到 | 检查参数映射文件加载（jg01 vs jg02）|
| 方位误差~360°峰值 | 未做环绕处理 | 确认使用正确的delta_A计算公式 |
| 有效数据量为零 | 状态参数从未等于6 | 检查状态参数唯一值和配置 |
| 插值导致长段填充 | 连续NaN段过长 | 检查CONTINUITY_GAP_SEC配置 |
| 公共参数全为NaN | 温度包未正确merge | 确认从packageCode=0x82或0x83提取 |
| 链路配对数据为空 | 时间轴无重叠 | 检查各星数据的时间范围 |
| 32star数据处理慢 | 原始数据量大 | 32star有100万行数据，处理时间较长 |
