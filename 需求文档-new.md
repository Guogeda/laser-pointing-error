# AI 执行规范：激光终端指向误差分析

> **适用对象**：AI Agent  
> **执行原则**：严格按步骤顺序执行，不得跳步或合并；所有可配置参数在代码顶部以常量定义；所有输出文件落盘后再进入下一步。  
> **Claude.md 及 plan 文件必须在本项目目录下生成。**

---

## 0. 全局约定

### 0.1 目录结构
```
project_root/
├── ori-data/
│   └── {XXstar}/          # 各卫星原始 CSV（只读）
├── config/
│   ├── param_mapping_jg01.py   # A27~A36 星参数映射（只读）
│   └── param_mapping_jg02.py   # A57~A66 星参数映射（只读）
└── output/
    ├── step1-preprocessing/
    ├── step2-state-filter/
    └── step3-error-calc/
```

### 0.2 卫星分组规则
```python
STAR_GROUP = {
    'jg01': ['A27', 'A28', 'A29', 'A30', 'A31', 'A32', 'A33', 'A34', 'A35', 'A36'],
    'jg02': ['A57', 'A58', 'A59', 'A60', 'A61', 'A62', 'A63', 'A64', 'A65', 'A66'],
}
PARAM_MAPPING_FILE = {
    'jg01': 'config/param_mapping_jg01.py',
    'jg02': 'config/param_mapping_jg02.py',
}

# 终端编号规则
TERMINAL_MAP = {
    'jg01': {'01': 'B1', '02': 'A1-2', '03': 'B2', '04': 'A1-1'},
    'jg02': {'01': 'A1-1', '02': 'A2-1', '03': 'A2-2', '04': 'A1-2'},
}
```

### 0.3 原始数据 Schema（长格式）
| 字段名 | 类型 | 说明 | 是否关键 |
|--------|------|------|---------|
| `satelliteTime` | datetime(ms) | 星上采样时间戳 | ✅ 索引列 |
| `packageCode` | hex string | 遥测帧标识 | ✅ 分流依据 |
| `paramCode` | string | 遥测参数代号 | ✅ |
| `parsedValue` | numeric/string | 解析后物理量 | ✅ |
| `translateValue` | string | 枚举/状态中文翻译 | 辅助 |
| 其余列 | — | 忽略 | 否 |

### 0.4 可配置参数（代码顶部统一定义）
```python
# ── 异常值检测 ──
OUTLIER_SIGMA           = 3      # σ 倍数阈值
OUTLIER_MIN_SEGMENT     = 5      # 连续异常段最小长度（点数），超过则整段标 invalid

# ── 状态筛选 ──
CONTINUITY_GAP_SEC      = 10     # 秒，超过此间隔视为不连续
SESSION_TRANSIENT_DROP  = 10     # 秒，状态切换到=6 后丢弃的过渡期时长

# ── 目标状态值 ──
VALID_STATE_VALUE       = 6
STATE_PARAMS = {
    'B1':   'TMJB3031',
    'B2':   'TMJB4031',
    'A1-1': 'TMJA3115',
    'A1-2': 'TMJA3239',
}

# ── 统一时间轴 ──
RESAMPLE_FREQ           = '1S'   # 1Hz，1秒一个时间戳
```

### 0.5 CSV 列头规则（全局）
- **第一行（列名）统一使用遥测中文名称，不使用遥测代号**
- 内部处理时保留代号映射，输出文件前做列名替换

---

## Step 1：数据预处理

### 前置条件
- `ori-data/{XXstar}/` 下存在原始 CSV 文件

### 执行流程

#### 1-A：按 packageCode 分流 → pivot 宽格式
```python
# 对每颗卫星的每个 CSV 文件：
for csv_file in glob('ori-data/{star}/*.csv'):
    df = pd.read_csv(csv_file, parse_dates=['satelliteTime'])
    for pkg_code, df_pkg in df.groupby('packageCode'):
        df_wide = df_pkg.pivot_table(
            index='satelliteTime',
            columns='paramCode',
            values='parsedValue',
            aggfunc='last'          # 同时刻同参数取最新值
        )
        # 后续异常检测在 df_wide 上操作
```

#### 1-B：异常值检测（三层，按序执行，标记 flag 列）

```python
# 对 df_wide 的每一个数值列 col：

# 层1：物理范围检测
#   从 param_mapping 读取 [min_valid, max_valid]
#   超出范围 → flag = 'out_of_range'

# 层2：3σ 统计检测（滑动窗口 60 点）
#   |value - rolling_mean| > OUTLIER_SIGMA * rolling_std → flag = 'stat_outlier'

# 层3：变化率突变检测
#   |diff()| > diff().abs().quantile(0.99) → flag = 'spike'

# 连续异常段合并规则：
#   同列连续 flag 非空的点 > OUTLIER_MIN_SEGMENT → 整段改为 flag = 'invalid'

# 输出：每个数值列 col 对应增加 col_flag 列
# 注意：标记异常，保留原值（不删除、不插值）
```

#### 1-C：列名替换为中文名称后输出

```python
# 读取 param_mapping 中 {paramCode: 中文名} 映射，对 df_wide 列名做 rename
# 输出到 output/step1-preprocessing/{star}_pkg_{pkg_code}_wide.csv
```

### 可视化改进

#### 时间轴有效性图生成
- **参数选择**：避开时间类参数（当前轨道时间秒、当前轨道时间微秒、卫星时间秒值、卫星时间毫秒值、星上时间秒、星上时间毫秒）
- **策略**：选择每个遥测包中数据最完整的非时间类参数进行可视化
- **效果**：蓝色线表示物理量值，红色区域表示异常值检测结果

#### 汇总甘特图（新增）
- **目的**：展示所有遥测包的数据覆盖情况
- **实现**：
  - 创建统一时间轴（1Hz）
  - 标记每个时间点的数据状态（无数据=白色，有数据=蓝色）
  - 按遥测包纵向排列，直观展示数据覆盖区间
- **文件**：`summary_packages_gantt.png`

### 输出（存入 `output/step1-preprocessing/`）
| 文件 | 内容 |
|------|------|
| `{star}_pkg_{pkg_code}_wide.csv` | 每颗星每个 packageCode 的宽格式 CSV，列名为中文，含 `_flag` 列 |
| `preprocessing_report.md` | 各包：行数、时间跨度、异常点数量/占比、有效率 |
| `{star}_pkg_{pkg_code}_timeline.png` | 各 packageCode 选取一个代表性参数绘制时间轴有效性图（有效/无效区间标色）|

---

## Step 2：状态识别与数据筛选

> **核心原则：先筛选，后插值。**

### 前置条件
- Step 1 完成，`output/step1-preprocessing/` 下宽格式 CSV 存在

### 各终端重要遥测参数表

#### 公共参数：4 个终端均需包含（按参数实际来源包）
```python
COMMON_PARAMS = {
    # packageCode = 0x81
    'TMR137': 'RM15-DBF本体',
    'TMR138': 'RM16-DBF安装面1(+Z)',
    'TMR139': 'RM17-DBF安装面2(-Z)',

    # packageCode = 0x82
    'TMR185': 'RM83-L射频单元本体（-Y3-X1）',
    'TMR191': 'RM89-L射频单元本体（-Y1+X3）',
    'TMR192': 'RM90-L射频单元本体（-Y3+X4）',
    'TMR193': 'RM91-L射频单元（-Y1）',
    'TMR200': 'RM99-Ka接收相控阵主散热面1(+X)',
    'TMR201': 'RM100-Ka接收相控阵主散热面2(-X)',
}
```

#### A1-1 专属参数（packageCode = 0x134）
```python
A1_1_PARAMS = {
    **COMMON_PARAMS,
    'TMJA3051': 'A3慢-通信1 锁频信号幅值',
    'TMJA3052': 'A3慢-通信1 频差',
    'TMJA3115': 'A3慢-1-激光终端状态',          # ← 关键参数（状态筛选依据）
    'TMJA3147': 'A3慢-1-方位电机当前位置',
    'TMJA3148': 'A3慢-1-方位电机目标位置',
    'TMJA3149': 'A3慢-1-俯仰电机当前位置',
    'TMJA3150': 'A3慢-1-俯仰电机目标位置',
    'TMJA3151': 'A3慢-1-精跟FSM方位采样位置(主)',
    'TMJA3152': 'A3慢-1-精跟FSM方位采样位置(备)',
    'TMJA3153': 'A3慢-1-精跟FSM俯仰采样位置(主)',
    'TMJA3154': 'A3慢-1-精跟FSM俯仰采用位置(备)',
    'TMJA3185': 'A3慢-1-后光学基板温度(主)',
    'TMJA3186': 'A3慢-1-后光学基板温度(备)',
    'TMJA3188': 'A3慢-1-主镜筒温度(主)',
    'TMJA3189': 'A3慢-1-主镜筒温度(备)',
    'TMJA3195': 'A3慢-1-框架温度(℃)',
    'TMJA3219': 'A3慢-1-相机光斑质心X',
    'TMJA3220': 'A3慢-1-相机光斑质心Y',
    'TMJA3221': 'A3慢-1-相机光斑幅值均值',
    'TMJA3235': 'A3慢-1-跟踪点X',
    'TMJA3236': 'A3慢-1-跟踪点Y',
}
```

#### A1-2 专属参数（packageCode = 0x134）
```python
A1_2_PARAMS = {
    **COMMON_PARAMS,
    'TMJA3071': 'A3慢-通信2 锁频信号幅值',
    'TMJA3072': 'A3慢-通信2 频差',
    'TMJA3239': 'A3慢-2-激光终端状态',          # ← 关键参数
    'TMJA3271': 'A3慢-2-方位电机当前位置',
    'TMJA3272': 'A3慢-2-方位电机目标位置',
    'TMJA3273': 'A3慢-2-俯仰电机当前位置',
    'TMJA3274': 'A3慢-2-俯仰电机目标位置',
    'TMJA3275': 'A3慢-2-精跟FSM方位采样位置(主)',
    'TMJA3276': 'A3慢-2-精跟FSM方位采样位置(备)',
    'TMJA3277': 'A3慢-2-精跟FSM俯仰采样位置(主)',
    'TMJA3278': 'A3慢-2-精跟FSM俯仰采用位置(备)',
    'TMJA3279': 'A3慢-2-超前FSM方位采样位置',
    'TMJA3309': 'A3慢-2-后光学基板温度(主)',
    'TMJA3310': 'A3慢-2-后光学基板温度(备)',
    'TMJA3312': 'A3慢-2-主镜筒温度(主)',
    'TMJA3313': 'A3慢-2-主镜筒温度(备)',
    'TMJA3319': 'A3慢-2-框架温度(℃)',
    'TMJA3343': 'A3慢-2-相机光斑质心X',
    'TMJA3344': 'A3慢-2-相机光斑质心Y',
    'TMJA3345': 'A3慢-2-相机光斑幅值均值',
    'TMJA3359': 'A3慢-2-跟踪点X',
    'TMJA3360': 'A3慢-2-跟踪点Y',
}
```

#### B1 专属参数（packageCode = 0x136）
```python
B1_PARAMS = {
    **COMMON_PARAMS,
    'TMJB3031': 'B1慢-捕跟工作状态',             # ← 关键参数
    'TMJB3079': 'B1慢-捕跟伺服实时方位轴角',
    'TMJB3080': 'B1慢-捕跟伺服实时俯仰轴角',
    'TMJB3097': 'B1慢-角误差耦合器能量值',
    'TMJB3101': 'B1慢-角误差耦合探测增益',
    'TMJB3142': 'B1慢-耦合误差X',
    'TMJB3145': 'B1慢-耦合误差Y',
    'TMJB3212': 'B1慢-捕跟伺服理论方位角',
    'TMJB3213': 'B1慢-捕跟伺服理论俯仰角',
    'TMJB3216': 'B1慢-当前太阳角',
    'TMJB3236': 'B1慢-热控通道02反馈温度值_望远镜筒',
    'TMJB3243': 'B1慢-热控通道09反馈温度值_库德镜3(℃)',
    'TMJB3244': 'B1慢-热控通道10反馈温度值_后光路1A',
    'TMJB3245': 'B1慢-热控通道11反馈温度值_后光路1B',
    'TMJB3246': 'B1慢-热控通道12反馈温度值_后光路2A',
    'TMJB3247': 'B1慢-热控通道13反馈温度值_后光路2B',
}
```

#### B2 专属参数（packageCode = 0x138）
```python
B2_PARAMS = {
    **COMMON_PARAMS,
    'TMJB4031': 'B2慢-捕跟工作状态',             # ← 关键参数
    'TMJB4079': 'B2慢-捕跟伺服实时方位轴角',
    'TMJB4080': 'B2慢-捕跟伺服实时俯仰轴角',
    'TMJB4097': 'B2慢-角误差耦合器能量值',
    'TMJB4101': 'B2慢-角误差耦合探测增益',
    'TMJB4142': 'B2慢-耦合误差X',
    'TMJB4145': 'B2慢-耦合误差Y',
    'TMJB4212': 'B2慢-捕跟伺服理论方位角',
    'TMJB4213': 'B2慢-捕跟伺服理论俯仰角',
    'TMJB4216': 'B2慢-当前太阳角',
    'TMJB4236': 'B2慢-热控通道02反馈温度值_望远镜筒',
    'TMJB4243': 'B2慢-热控通道09反馈温度值_库德镜3-离棱镜最近(℃)',
    'TMJB4244': 'B2慢-热控通道10反馈温度值_后光路1A',
    'TMJB4245': 'B2慢-热控通道11反馈温度值_后光路1B',
    'TMJB4246': 'B2慢-热控通道12反馈温度值_后光路2A',
    'TMJB4247': 'B2慢-热控通道13反馈温度值_后光路2B',
}
```

### 执行流程（严格按顺序，4 个终端独立执行）

```
数据处理逻辑（对每个终端独立执行）：

Step1 输出 CSV
    ↓
① 按终端提取所属 packageCode 的参数列 + 公共参数列
    ↓
② 时间对齐（最近邻对齐）
    ↓
③ 生成【未筛选】宽格式 CSV（列名=中文名）
    ↓
④ 有效数据筛选（见筛选规则）
    ↓
⑤ 插值处理（统一 1Hz 时间轴、见插值规则）
    ↓
⑥ 生成【处理后】宽格式 CSV（列名=中文名）
```

#### ① 参数提取规则
- 从 Step 1 输出的对应 packageCode 宽格式 CSV 中，**仅保留当前终端参数表中列出的 paramCode 列**
- 公共参数（`COMMON_PARAMS`）从两个温度包中提取：
  - `TMR137-TMR139` 从 packageCode = 0x81 中提取
  - `TMR185-TMR193`、`TMR200-TMR201` 从 packageCode = 0x82 中提取
- 列名：paramCode → 对应中文名（输出文件用中文名）

#### ② 时间对齐规则
```python
# 各参数来自不同包，采样率不同（1s / 3s）
# 统一到完整1Hz时间轴（整秒时间戳）：
t_min = df_merged.index.min().floor('S')
t_max = df_merged.index.max().ceil('S')
unified_index = pd.date_range(start=t_min, end=t_max, freq=RESAMPLE_FREQ)
df_aligned = df_merged.reindex(unified_index, method='nearest', tolerance=pd.Timedelta('500ms'))
# tolerance 说明：若最近邻点超过 500ms，则该时刻置 NaN（不强行对齐噪声数据）
```

#### ③ 生成【未筛选】CSV
- 输出 `output/step2-state-filter/{terminal}_raw.csv`，含所有时间戳，NaN 保留

#### ④ 有效数据筛选（在未筛选 CSV 上执行）

```python
# Step A：连续时间段识别
#   对关键参数列（STATE_PARAMS[terminal]），找出所有非 NaN 的时间戳
#   若相邻两个有效时间戳间隔 <= CONTINUITY_GAP_SEC，则归为同一连续段（period_id）
#   间隔 > CONTINUITY_GAP_SEC → 新开 period_id

# Step B：有效状态识别（仅在连续段内执行）
#   在每个 period_id 内，筛选 关键参数 == VALID_STATE_VALUE (=6) 的行
#   连续 state=6 的片段 → 分配 session_id（同 period_id 内递增）

# Step C：过渡期丢弃
#   每个 session_id 的前 SESSION_TRANSIENT_DROP 秒数据丢弃
#   丢弃后 session 时长为 0 → 该 session 整体丢弃

# 最终筛选结果：只保留通过 Step C 的行
# 新增列：period_id（int），session_id（int）
```

#### ⑤ 插值处理（在完整1Hz时间轴上，只在有效session内执行）

```python
# 关键原则：XXX_processed.csv 包含完整的1Hz时间轴，无效数据段保留，但只在有效session内插值

# 步骤：
# 1. 先标记所有数据点的有效性（is_valid列）
# 2. 识别连续时间段和session
# 3. 将period_id和session_id合并到完整时间轴
# 4. 只在session_id不为空的时间段内进行插值

# 数值型参数：
#   仅在有效session内（session_id非空），对 NaN 做线性插值（limit_area='inside'，不外推）
#   非有效session内的数据保持NaN

# 枚举/状态类参数（含关键参数列）：
#   仅在有效session内前向填充（ffill）
#   非有效session内的数据保持原值

# 所有插值列增加标记：<col>_interp = True/False
#   True 表示该值由插值产生，原始值为 NaN
#   仅在有效session内标记插值
```

### 输出（存入 `output/step2-state-filter/`）

| 文件 | 内容 |
|------|------|
| `A1-1_raw.csv` | A1-1 未筛选宽格式，列名中文，含 1Hz 时间轴 |
| `A1-2_raw.csv` | A1-2 未筛选 |
| `B1_raw.csv` | B1 未筛选 |
| `B2_raw.csv` | B2 未筛选 |
| `A1-1_processed.csv` | A1-1 筛选+插值后，含 period_id / session_id / `_interp` / `_transient` 列 |
| `A1-2_processed.csv` | A1-2 处理后 |
| `B1_processed.csv` | B1 处理后 |
| `B2_processed.csv` | B2 处理后 |
| `state_filter_report.md` | 各终端：period 数量、session 数量、有效数据时长、丢弃原因统计 |
| `{terminal}_valid_distribution.png` | 各终端有效数据分布甘特图：
  - 白色：无效数据
  - 浅蓝色：有效数据（原始值）
  - 红色：有效数据（插值值）
  横轴为时间，清晰展示数据分布和插值情况 |

---

## Step 3：指向误差计算

### 前置条件
- Step 2 完成，`output/step2-state-filter/{terminal}_processed.csv` 共 4 个文件存在

### 参数对应表（代码中以常量定义）
```python
ERROR_PARAMS = {
    'B1': {
        'A_t': 'B1慢-捕跟伺服理论方位角',    # TMJB3212
        'A_r': 'B1慢-捕跟伺服实时方位轴角',   # TMJB3079
        'E_t': 'B1慢-捕跟伺服理论俯仰角',     # TMJB3213
        'E_r': 'B1慢-捕跟伺服实时俯仰轴角',   # TMJB3080
        'track_err_x': 'B1慢-耦合误差X',      # TMJB3142，单位 μrad
        'track_err_y': 'B1慢-耦合误差Y',      # TMJB3145，单位 μrad
    },
    'B2': {
        'A_t': 'B2慢-捕跟伺服理论方位角',
        'A_r': 'B2慢-捕跟伺服实时方位轴角',
        'E_t': 'B2慢-捕跟伺服理论俯仰角',
        'E_r': 'B2慢-捕跟伺服实时俯仰轴角',
        'track_err_x': 'B2慢-耦合误差X',
        'track_err_y': 'B2慢-耦合误差Y',
    },
    'A1-1': {
        'A_t': 'A3慢-1-方位电机目标位置',
        'A_r': 'A3慢-1-方位电机当前位置',
        'E_t': 'A3慢-1-俯仰电机目标位置',
        'E_r': 'A3慢-1-俯仰电机当前位置',
        'track_err_x': None,                   # A 类无精跟踪误差
        'track_err_y': None,
    },
    'A1-2': {
        'A_t': 'A3慢-2-方位电机目标位置',
        'A_r': 'A3慢-2-方位电机当前位置',
        'E_t': 'A3慢-2-俯仰电机目标位置',
        'E_r': 'A3慢-2-俯仰电机当前位置',
        'track_err_x': None,
        'track_err_y': None,
    },
}
```

### 计算公式（严格执行，不得修改）

```python
import numpy as np

def calc_pointing_error(A_t, A_r, E_t, E_r):
    """
    A_t, A_r: 理论/实际方位角（单位：deg）
    E_t, E_r: 理论/实际俯仰角（单位：deg）
    返回：delta_A, delta_E, theta_error（单位均为 deg）
    """
    # 方位角误差：必须做环绕处理，否则跨 0°/360° 时产生 ~360° 假误差
    delta_A = (A_t - A_r + 180) % 360 - 180    # 归一化到 [-180°, 180°)

    # 俯仰误差
    delta_E = E_t - E_r

    # 综合指向误差：方位分量投影到天球面
    theta_error = np.sqrt((delta_A * np.cos(np.radians(E_r)))**2 + delta_E**2)

    return delta_A, delta_E, theta_error
```

### 执行动作

1. **逐终端计算**：读取 `{terminal}_processed.csv`，调用 `calc_pointing_error()`，新增 `delta_A`、`delta_E`、`theta_error` 列，保存为 `error_{terminal}.csv`

2. **统计指标计算**（方位误差、俯仰误差分别统计，按终端分组）：

| 指标 | 计算方式 |
|------|---------|
| 均值 | `mean()` |
| 标准差 | `std()` |
| RMS | `sqrt(mean(x²))` |
| P95 | `quantile(0.95)` |
| P99 | `quantile(0.99)` |

3. **可视化（每个终端各自生成）**：
   - **时间序列图**：`delta_A`、`delta_E`、`theta_error` 三条线，横轴时间，纵轴误差（deg）
   - **误差分布直方图**：`delta_A`、`delta_E` 各一张，含正态拟合曲线，标注 mean ± std
   - **4 终端对比箱线图**：方位误差一张、俯仰误差一张，x轴为终端名，y轴为误差（deg）

### 输出（存入 `output/step3-error-calc/`）

| 文件 | 内容 |
|------|------|
| `error_B1.csv` | 含 `satelliteTime`, `delta_A`, `delta_E`, `theta_error`, `session_id` |
| `error_B2.csv` | 同上 |
| `error_A1-1.csv` | 同上 |
| `error_A1-2.csv` | 同上 |
| `error_statistics.md` | 各终端统计表（方位/俯仰分开），含 mean/std/RMS/P95/P99 |
| `{terminal}_error_timeseries.png` | 各终端误差时间序列图 |
| `{terminal}_error_distribution.png` | 各终端误差分布直方图 |
| `comparison_azimuth_boxplot.png` | 4 终端方位误差对比箱线图 |
| `comparison_elevation_boxplot.png` | 4 终端俯仰误差对比箱线图 |

---

## 附录：快速错误排查

| 症状 | 可能原因 | 检查点 |
|------|---------|--------|
| 宽格式 CSV 列数异常 | paramCode 未在 param_mapping 中找到 | 检查 param_mapping 文件是否加载正确（jg01 vs jg02）|
| 方位误差出现 ~360° 峰值 | 未做环绕处理 | 确认使用 `(A_t - A_r + 180) % 360 - 180` 公式 |
| 有效数据量为零 | 状态参数从未等于 6 | 打印状态参数唯一值，确认 VALID_STATE_VALUE 配置 |
| 插值导致长段填充 | 连续 NaN 段超出合理长度 | 检查 CONTINUITY_GAP_SEC 是否合理，确认 limit_area='inside' |
| 公共参数全为 NaN | 温度包未正确 merge | 确认公共参数从 packageCode=0x82 或者 packageCode=0x83 中提取， 如果找不到数据，则用0 补齐|