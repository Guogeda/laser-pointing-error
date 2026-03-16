# 激光指向误差分析系统 - 需求文档与执行规范

## 版本历史
- v1.0 - 初始版本
- v1.1 (2026-03-14) - 更新多星数据处理流程，增加jg02组卫星支持
- v1.2 (2026-03-14) - 删除链路配对分析章节，优化终端配置
- v1.3 (2026-03-15) - 增加温度与误差关系分析功能
- v1.4 (2026-03-17) - 增加热形变分离分析功能，使用单个遥测量


## 卫星在轨链路拓扑图
对于A27~A36卫星，每颗卫星有四个终端：01为B1， 02为A1-2， 03为B2， 04为A1-1
对于A57~66卫星，每个卫星的四个终端对应如下：01为A1-1， 02为A2-1， 03为A2-2，04为A1-2

卫星实际在轨的链路拓扑为：
A2701-A2803
A3401-A3503
A3601-A2703
A2804-A2902
A2904-A3004
A3002-A3102
A3104-A3204
A3304-A3402
A3504-A3602
A3302-A3201
A2702-A0703
A2802-A0803
A3502-A1503
A5802-A5704
A5902-A5804
A6002-A5904
A6102-A6004
A5803-A2801
A5903-A2901
A6003-A3001
A6103-A3101
A5703-A2704


## 一、项目概述

本项目用于处理卫星遥测数据并计算激光通信终端的指向误差，支持多星分组处理、链路配对分析、温度与误差关系分析等功能。

### 核心分析目标
- **激光指向误差计算**：计算各终端的方位误差、俯仰误差和综合指向误差
- **温度与误差关系分析**：分析指向误差与在轨温度的关系，包括：
  - 与轨道周期有关的温度（前光路、后光路温度）
  - 与载荷温度有关的温度（DBF、L、Ka载荷温度平均值）
- **载荷开关机分析**：分析三个载荷（DBF、L、Ka）开关机时间段与指向误差的关系，用不同颜色区域表示
- **链路分析**：分析32-31和31-61两条链路的误差关系

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

#### jg01组终端配置（通用）
| 终端 | 包代码 | 状态参数 | 状态名称 |
|------|--------|---------|---------|
| B1 | 136 | TMJB3031 | B1慢-捕跟工作状态 |
| B2 | 138 | TMJB4031 | B2慢-捕跟工作状态 |
| A1-1 | 134 | TMJA3115 | A3慢-1-激光终端状态 |
| A1-2 | 134 | TMJA3239 | A3慢-2-激光终端状态 |

#### jg01组32star特殊配置
| 终端 | 包代码 | 状态参数 | 状态名称 |
|------|--------|---------|---------|
| A1-1 | 13B | TMJA3115 | A3慢-1-激光终端状态 |
| A1-2 | 13B | TMJA3239 | A3慢-2-激光终端状态 |

**重要说明**：32star属于jg01组，但激光A终端使用包代码13B，而不是通用的134。

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

## 四、温度与误差关系分析

### 4.1 分析目标
分析激光指向误差与在轨温度的关系，温度来源分为两方面：
- **与轨道周期有关**：来源于太阳的热量，影响激光终端前后光路的温度
- **与载荷温度有关**：取 DBF、L、Ka载荷温度遥测的平均值

### 4.2 分析方法
1. **Pearson相关性分析**：计算温度与误差的线性相关系数
2. **滞后相关性分析**：分析温度变化对误差的延迟影响（最佳滞后时间）
3. **温度变化率分析**：分析dT/dt与误差的关系
4. **频谱分析**：验证温度和误差的轨道周期特征（主周期约120分钟）
5. **温度梯度分析**：分析前光路-后光路温度差与误差的关系
6. **多元线性回归**：同时考虑多温度因素的组合影响
7. **热形变分离分析**：使用120分钟移动平均分离周期性和随机性热形变成分
   - 周期性热形变：太阳辐照度、前后光路温度（120分钟轨道周期）
   - 随机性热形变：载荷温度变化率（设备状态影响）

### 4.3 温度参数配置

#### jg01组温度参数
| 终端 | 前光路温度 | 后光路温度 | 载荷温度（平均值） |
|------|----------|----------|------------------|
| A1-1 | TMJA3188  | TMJA3185  | DBF+L+Ka平均值   |
| A1-2 | TMJA3312  | TMJA3309  | DBF+L+Ka平均值   |
| B1   | TMJB3236  | TMJB3244-3247平均值 | DBF+L+Ka平均值 |
| B2   | TMJB4236  | TMJB4244-4247平均值 | DBF+L+Ka平均值 |

#### jg02组温度参数
| 终端 | 前光路温度 | 后光路温度 | 载荷温度（平均值） |
|------|----------|----------|------------------|
| A1-1 | TMJA3188  | TMJA3185  | DBF+L+Ka平均值   |
| A1-2 | TMJA3312  | TMJA3309  | DBF+L+Ka平均值   |
| A2-1 | TMJA8188  | TMJA8185  | DBF+L+Ka平均值   |
| A2-2 | TMJA8312  | TMJA8309  | DBF+L+Ka平均值   |

#### 载荷温度参数（使用单个遥测量）
- DBF温度：仅使用 RM16-DBF安装面1(+Z)（TMR138）
- L射频单元温度：仅使用 RM83-L射频单元本体（-Y3-X1）（TMR185）
- Ka接收相控阵温度：仅使用 RM99-Ka接收相控阵主散热面1(+X)（TMR200）

**重要说明**：载荷温度不再使用多个遥测量的平均值，而是严格使用单个指定的遥测量进行分析。

### 4.4 分析结果
通过热形变分离分析，我们得出以下主要结论：

#### 周期性热形变影响（120分钟轨道周期）
- **主要影响因素**：
  - 太阳辐照度（solar_irradiance）：相关系数约为±0.22（极显著）
  - 后光路温度均值：相关系数约为0.23（极显著）
  - 前光路温度：相关系数约为0.22（极显著）
- **影响机制**：太阳辐照度周期性变化导致温度波动，进而引起激光终端结构热形变
- **特征周期**：约120分钟（轨道周期）

#### 随机热形变影响（载荷温度变化）
- **主要影响因素**：
  - L载荷温度变化率：相关系数约为0.10（极显著）
  - Ka载荷温度变化率：相关系数约为0.09（极显著）
  - DBF载荷温度变化率：相关系数约为0.07（极显著）
- **影响机制**：载荷设备开关机和运行状态变化导致温度快速变化
- **时间尺度**：分钟级到小时级

#### 建模可行性
可以建立指向误差与热形变的关系模型，但需要分成分建模：
- 周期性误差模型：使用太阳辐照度、前后光路温度的周期性成分
- 随机性误差模型：使用DBF、L、Ka载荷温度的变化率
- 推荐模型：分成分建模 + 时间序列模型（LSTM/ARIMA）

### 4.5 输出结果
分析结果保存于 `output/temperature_analysis/` 目录：
- `reports/`：综合分析报告和各终端报告
- `data/`：各终端的分析数据CSV文件
- `plots/`：增强分析图表（温度变化率、频谱分析、温度梯度等）

#### 新增图表文件
热形变分析新增的图表文件：
- `{star}_{terminal}_thermal_deformation_effects.png`：热形变与指向误差关系图
- `{star}_{terminal}_前光路温度_periodic_random.png`：前光路温度周期性/随机性成分分离图
- `{star}_{terminal}_后光路温度均值_periodic_random.png`：后光路温度均值周期性/随机性成分分离图
- `{star}_{terminal}_太阳辐照度_periodic_random.png`：太阳辐照度周期性/随机性成分分离图
- `{star}_{terminal}_综合误差_periodic_random.png`：综合误差周期性/随机性成分分离图

## 五、载荷开关机与指向误差关系分析

### 5.1 分析目标
分析激光指向误差与三个载荷（DBF、L、Ka）开关机状态的关系，通过温度变化识别载荷开机时间段，并在时间序列图中用不同颜色的区域面积表示。

### 5.2 载荷温度使用的遥测量

直接使用您指定的三个特定遥测量，不需要取平均值：

#### DBF载荷温度
- **RM16-DBF安装面1(+Z)** （单个遥测量，直接使用）

#### L载荷温度
- **RM83-L射频单元本体（-Y3-X1）** （单个遥测量，直接使用）

#### Ka载荷温度
- **RM99-Ka接收相控阵主散热面1(+X)** （单个遥测量，直接使用）

### 5.3 开关机状态识别方法
采用**状态机时间窗口温变速率检测**方法：

#### 5.3.1 核心参数
- **时间窗口**：20秒（计算温度变化率的窗口大小）
- **阈值倍数**：1.5倍标准差（动态阈值）
- **最小持续时间**：10分钟（有效时间段的最小长度）
- **目标持续时间**：20分钟（每个开机时间段的目标长度）

#### 5.3.2 状态机检测逻辑
1. **第一阶段：检测开机（温度上升）**
   - 当温变速率 > 1.5倍正标准差时，标记为开机上升阶段
   - 开机开始时间：从当前窗口回溯到窗口开始

2. **第二阶段：等待关机**
   - 开机上升阶段结束后，进入"等待关机"状态
   - 持续监控温度变化率

3. **第三阶段：检测关机（温度下降）**
   - 当温变速率 < -1.5倍负标准差时，标记为关机下降阶段
   - 关机开始时间：从当前窗口回溯到窗口开始

4. **第四阶段：完整周期**
   - 当温变速率回复到正常范围时，结束关机阶段
   - 完整时间段 = 开机开始 到 关机结束
   - 如果持续时间 ≥ 10分钟，则保留该时间段（最多取20分钟）

#### 5.3.3 技术实现
- 使用中值滤波平滑温度变化率
- 动态阈值基于温度变化率的标准差计算
- 状态机管理四个检测阶段的状态转换

### 5.4 可视化方法
- 横坐标：时间（整秒时间轴）
- 纵坐标：方位误差、俯仰误差、综合误差
- 载荷温度：右侧Y轴
- 开机时间段：不同颜色的区域面积表示
  - DBF载荷：黄色区域（α=0.2）
  - L载荷：紫色区域（α=0.2）
  - Ka载荷：青色区域（α=0.2）

### 5.5 执行命令
```bash
# 运行载荷开关机分析（需要先完成三阶段处理）
python src/payload_power_analysis.py
```

### 5.6 输出结果
分析结果保存于 `output/payload_power_analysis/` 目录：
- `reports/payload_power_analysis_report.md`：综合分析报告，包含遥测量说明和时间段统计
- `data/*.csv`：包含误差数据和三个载荷温度的详细数据文件
- `plots/*.png`：指向误差时间序列图，带三个载荷开关机区域标注

## 五、数据质量说明

### 5.1 32star数据特征
经过对原始数据的分析，确认32star原始数据本身就存在大量连续重复值，不是Step 1插值造成的。

具体数据特征：
- 包13B (激光A) 中 TMJA3359：100% 的连续相同值
- 包13B 中 TMJA3309：97.6% 的连续相同值
- 包13B 中 TMJA3147：80.3% 的连续相同值
- 包81 (温度包) 中 TMR139：75.4% 的连续相同值

这是32star原始遥测数据的固有特征，与31star和61star的数据特征有所不同。



## 六、执行命令

### 6.1 完整流程处理单星

### 6.2 温度与误差关系分析
```bash
# 运行温度与误差关系分析（需要先完成三阶段处理）
python src/temperature_analysis.py
```
```bash
# 处理jg01组卫星（如31star、32star）
python src/verify_complete.py jg01 31star
python src/verify_complete.py jg01 32star

# 处理jg02组卫星（如61star）
python src/verify_complete.py jg02 61star
```


## 七、关键修复说明

### 7.1 find_column 函数参数匹配修复

**问题描述**：
- A1-1和A1-2终端的参数列名相似，导致find_column函数无法正确区分
- 出现误差值全部为0的情况，原因是A_t（目标位置）和A_r（当前位置）匹配到了同一列

**根本原因**：
- 同一数据包（如134包）中包含多个终端的参数
- 参数代码后缀相似（如TMJA3147和TMJA3271都以'47'结尾）
- 原始匹配逻辑仅依赖参数代码后缀匹配，容易混淆

**修复方案**：
修改了find_column函数的参数匹配逻辑，采用多级匹配策略：

1. **精确匹配**：首先尝试精确匹配参数代码
2. **关键字优先匹配**：优先匹配包含"目标"或"当前"关键字的列名
3. **终端名称匹配**：优先匹配包含终端名称关键字的列
4. **后缀匹配**：最后考虑参数代码后缀匹配

**关键代码逻辑**：
```python
def find_column(df, param_code, param_type='', terminal_name=''):
    # 1. 精确匹配
    for col in df.columns:
        if param_code in col or col in param_code:
            return col

    # 2. 关键字优先匹配
    if param_type == 'A_t':
        # 方位目标位置：优先匹配包含'目标'的列
        for col in candidates_by_terminal:
            if '方位' in col and '目标' in col:
                return col
    elif param_type == 'A_r':
        # 方位当前位置：优先匹配包含'当前'的列
        for col in candidates_by_terminal:
            if '方位' in col and '当前' in col:
                return col
```

**验证结果**：
- 修复后A1-1和A1-2终端的误差计算正常
- delta_A、delta_E、theta_error不再全部为0
- 参数匹配正确率显著提高

## 七、输出目录结构

```
激光指向误差计算/
├── ori-data/                  # 原始卫星遥测数据
│   ├── 31star/
│   ├── 32star/
│   └── 61star/
├── src/                       # 处理过程代码
│   ├── config/
│   │   └── satellite_groups.py    # 卫星分组配置
│   ├── verify_complete.py         # 完整三阶段处理流程
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
| 32star数据处理慢 | 原始数据量大 | 32star有100万行数据，处理时间较长 |
