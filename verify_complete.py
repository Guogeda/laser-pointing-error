#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合验证脚本 - 完整三阶段处理流程
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

sys.path.insert(0, str(Path(__file__).parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

# 配置常量
OUTLIER_SIGMA = 3
VALID_STATE_VALUE = '6'  # 注意：状态值是字符串类型
CONTINUITY_GAP_SEC = 10
SESSION_TRANSIENT_DROP = 10
RESAMPLE_FREQ = '1S'

# 终端配置
TERMINALS = {
    'B1': {
        'package': '136',
        'state_param': 'TMJB3031',
        'state_name': 'B1慢-捕跟工作状态',
        'error_params': {
            'A_t': 'TMJB3212', 'A_r': 'TMJB3079',
            'E_t': 'TMJB3213', 'E_r': 'TMJB3080',
        }
    },
    'B2': {
        'package': '138',
        'state_param': 'TMJB4031',
        'state_name': 'B2慢-捕跟工作状态',
        'error_params': {
            'A_t': 'TMJB4212', 'A_r': 'TMJB4079',
            'E_t': 'TMJB4213', 'E_r': 'TMJB4080',
        }
    },
    'A1-1': {
        'package': '134',
        'state_param': 'TMJA3115',
        'state_name': 'A3慢-1-激光终端状态',
        'error_params': {
            'A_t': 'TMJA3148', 'A_r': 'TMJA3147',
            'E_t': 'TMJA3150', 'E_r': 'TMJA3149',
        }
    },
    'A1-2': {
        'package': '134',
        'state_param': 'TMJA3239',
        'state_name': 'A3慢-2-激光终端状态',
        'error_params': {
            'A_t': 'TMJA3272', 'A_r': 'TMJA3271',
            'E_t': 'TMJA3274', 'E_r': 'TMJA3273',
        }
    },
}

def cleanup_and_create_dirs():
    """创建输出目录（不删除已有目录，避免文件占用问题）"""
    base_dir = Path(__file__).parent / 'output'

    for step in ['step1-preprocessing', 'step2-state-filter', 'step3-error-calc']:
        for subdir in ['reports', 'plots', 'results']:
            (base_dir / step / subdir).mkdir(parents=True, exist_ok=True)

    return base_dir

def step1_preprocessing(csv_path, base_dir):
    """Step 1: 数据预处理"""
    print("\n" + "="*60)
    print("Step 1: 数据预处理")
    print("="*60)

    df = pd.read_csv(csv_path, parse_dates=['satelliteTime'])
    print(f"原始数据: {len(df)} 行")

    package_groups = df.groupby('packageCode')
    print(f"发现 {len(package_groups)} 个遥测包")

    results = {}
    for pkg_code, df_pkg in package_groups:
        # 长格式转宽格式
        df_wide = df_pkg.pivot_table(
            index='satelliteTime',
            columns='paramCode',
            values='parsedValue',
            aggfunc='last'
        )

        # 将所有数值列转换为数值类型
        numeric_columns = []
        for col in df_wide.columns:
            # 尝试转换为 float 类型
            try:
                numeric_series = pd.to_numeric(df_wide[col], errors='coerce')
                # 如果转换成功且至少有一个非 NaN 值
                if numeric_series.notna().any():
                    df_wide[col] = numeric_series
                    numeric_columns.append(col)
            except:
                pass  # 转换失败则保留为原始类型

        # 异常值检测（三层，严格按照需求文档）
        OUTLIER_MIN_SEGMENT = 5  # 连续异常段最小长度
        for col in numeric_columns:
            flag_col = f"{col}_标记"
            # 明确设置标记列为 object (字符串) 类型
            df_wide[flag_col] = pd.Series([np.nan] * len(df_wide), index=df_wide.index, dtype='object')

            # 层1：物理范围检测（根据参数类型设置合理范围）
            col_min, col_max = -180, 180  # 默认角度范围
            param_name = get_param_name(col)
            if '温度' in param_name:
                col_min, col_max = -20, 100  # 温度范围
            elif '俯仰' in param_name:
                col_min, col_max = -90, 90  # 俯仰角范围
            elif '耦合误差' in param_name:
                col_min, col_max = -10, 10  # 耦合误差范围（单位：μrad）

            mask_range = (df_wide[col] < col_min) | (df_wide[col] > col_max)
            df_wide.loc[mask_range, flag_col] = 'out_of_range'

            # 层2：3σ 统计检测（滑动窗口 60 点）
            rolling_mean = df_wide[col].rolling(window=60, min_periods=10).mean()
            rolling_std = df_wide[col].rolling(window=60, min_periods=10).std()
            mask_stat = (df_wide[col] - rolling_mean).abs() > OUTLIER_SIGMA * rolling_std
            df_wide.loc[mask_stat & df_wide[flag_col].isna(), flag_col] = 'stat_outlier'

            # 层3：变化率突变检测
            diff = df_wide[col].diff().abs()
            threshold = diff.quantile(0.99)  # 取99分位数作为阈值
            mask_spike = diff > threshold
            df_wide.loc[mask_spike & df_wide[flag_col].isna(), flag_col] = 'spike'

            # 连续异常段合并规则
            if not df_wide[flag_col].isna().all():
                outlier_mask = df_wide[flag_col].notna()
                consecutive_groups = (outlier_mask.diff() != 0).cumsum()
                outlier_groups = df_wide[outlier_mask].groupby(consecutive_groups)

                for group_id, group_data in outlier_groups:
                    if len(group_data) > OUTLIER_MIN_SEGMENT:
                        df_wide.loc[group_data.index, flag_col] = 'invalid'

        # 列名替换为中文
        rename_map = {}
        for col in df_wide.columns:
            if col.endswith('_标记'):
                original = col[:-3]
                rename_map[col] = f"{get_param_name(original)}_标记"
            else:
                rename_map[col] = get_param_name(col)
        df_wide = df_wide.rename(columns=rename_map)

        # 保存
        out_file = base_dir / 'step1-preprocessing' / 'results' / f'31star_pkg_{pkg_code}_wide.csv'
        df_wide.to_csv(out_file, encoding='utf-8-sig')
        results[pkg_code] = df_wide
        print(f"包 {pkg_code}: {df_wide.shape[1]} 列 → {out_file.name}")

    # 生成预处理报告
    generate_preprocessing_report(results, base_dir)

    # 生成时间轴有效性图
    generate_timeline_plots(results, base_dir)

    return results

def step2_state_filter(step1_data, base_dir):
    """Step 2: 状态筛选与数据处理（严格按照需求文档）"""
    print("\n" + "="*60)
    print("Step 2: 状态筛选与数据处理")
    print("="*60)

    terminal_data = {}

    # 公共参数（来自温度包 packageCode=0x82）
    COMMON_PARAMS = {
        'TMR137': 'RM15-DBF本体',
        'TMR138': 'RM16-DBF安装面1(+Z)',
        'TMR139': 'RM17-DBF安装面2(-Z)',
        'TMR185': 'RM83-L射频单元本体（-Y3-X1）',
        'TMR191': 'RM89-L射频单元本体（-Y1+X3）',
        'TMR192': 'RM90-L射频单元本体（-Y3+X4）',
        'TMR193': 'RM91-L射频单元（-Y1）',
        'TMR200': 'RM99-Ka接收相控阵主散热面1(+X)',
        'TMR201': 'RM100-Ka接收相控阵主散热面2(-X)',
    }

    # 终端专属参数表（严格按照需求文档）
    TERMINAL_PARAMS = {
        'A1-1': {
            **COMMON_PARAMS,
            'TMJA3051': 'A3慢-通信1 锁频信号幅值',
            'TMJA3052': 'A3慢-通信1 频差',
            'TMJA3115': 'A3慢-1-激光终端状态',
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
        },
        'A1-2': {
            **COMMON_PARAMS,
            'TMJA3071': 'A3慢-通信2 锁频信号幅值',
            'TMJA3072': 'A3慢-通信2 频差',
            'TMJA3239': 'A3慢-2-激光终端状态',
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
        },
        'B1': {
            **COMMON_PARAMS,
            'TMJB3031': 'B1慢-捕跟工作状态',
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
        },
        'B2': {
            **COMMON_PARAMS,
            'TMJB4031': 'B2慢-捕跟工作状态',
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
        },
    }

    # 提取公共参数
    temp_df = None
    temp_pkg_codes = ['82', '83']  # 温度包代码
    for temp_pkg in temp_pkg_codes:
        if temp_pkg in step1_data:
            temp_df = step1_data[temp_pkg].copy()
            print(f"从包 '{temp_pkg}' 提取公共参数")
            break

    for terminal, config in TERMINALS.items():
        pkg_code = config['package']
        if pkg_code not in step1_data:
            print(f"{terminal}: 找不到包 {pkg_code}，跳过")
            continue

        df = step1_data[pkg_code].copy()
        state_name = config['state_name']

        if state_name not in df.columns:
            print(f"{terminal}: 找不到状态参数 {state_name}，跳过")
            continue

        # 合并公共参数
        if temp_df is not None:
            df = df.merge(temp_df, how='left', left_index=True, right_index=True)

        # 主动添加所有公共参数列（严格按照需求文档，确保列存在）
        terminal_param_dict = TERMINAL_PARAMS[terminal]
        for param_code, param_name in COMMON_PARAMS.items():
            if param_name not in df.columns:
                df[param_name] = 0  # 用0补齐
                print(f"{terminal}: 主动添加公共参数列 '{param_name}'，用0初始化")

        # 严格按照需求文档中的参数表提取当前终端的参数

        # 提取参数：只保留参数表中明确列出的参数（中文名称）
        # 以及对应的标记列（中文名称_标记）
        cols_to_keep = []
        for col in df.columns:
            # 检查是否是参数表中的中文名称列
            if col in terminal_param_dict.values():
                cols_to_keep.append(col)
            # 检查是否是参数表中中文名称对应的标记列
            elif col.endswith('_标记') and col[:-3] in terminal_param_dict.values():
                cols_to_keep.append(col)

        # 添加状态参数（如果不在参数表中）
        if state_name not in cols_to_keep:
            cols_to_keep.append(state_name)

        # 确保没有重复的列
        cols_to_keep = list(dict.fromkeys(cols_to_keep))

        df = df[cols_to_keep]

        # 处理公共参数：如果公共参数列全为NaN，用0补齐（严格按照需求文档）
        terminal_param_dict = TERMINAL_PARAMS[terminal]
        for param_code, param_name in COMMON_PARAMS.items():
            if param_name in df.columns:
                if df[param_name].isna().all():
                    df[param_name] = 0
                    print(f"{terminal}: 公共参数 '{param_name}' 全为NaN，已用0补齐")
                # 填充部分NaN值（可选，需求文档未明确要求，但为了数据完整性）
                # df[param_name] = df[param_name].fillna(0)

        # 时间对齐到1Hz（整秒）
        start_time = df.index.min().floor('S')  # 向下取整到整秒
        end_time = df.index.max().ceil('S')     # 向上取整到整秒
        unified_index = pd.date_range(start=start_time, end=end_time, freq=RESAMPLE_FREQ)
        df_aligned = df.reindex(unified_index, method='nearest', tolerance=pd.Timedelta('500ms'))

        # 保存未筛选数据
        raw_file = base_dir / 'step2-state-filter' / 'results' / f'{terminal}_raw.csv'
        df_aligned.to_csv(raw_file, encoding='utf-8-sig')

        # 在完整1Hz时间轴上进行处理（保留所有时间点）
        df_processed = df_aligned.copy()

        # 先标记所有数据点的有效性
        df_processed['is_valid'] = (
            (df_processed[state_name] == VALID_STATE_VALUE) |
            (pd.to_numeric(df_processed[state_name], errors='coerce') == 6)
        )

        # 筛选出有效数据用于识别连续时间段
        df_valid = df_processed[df_processed['is_valid']].copy()

        if len(df_valid) == 0:
            print(f"{terminal}: 没有有效数据，跳过")
            continue

        # 识别连续时间段
        df_valid = df_valid.sort_index()
        time_diff = df_valid.index.to_series().diff()
        gap_mask = time_diff > pd.Timedelta(seconds=CONTINUITY_GAP_SEC)
        df_valid['period_id'] = gap_mask.cumsum()

        # 分配session_id并标记过渡期
        df_valid['session_id'] = pd.NA
        for period_id in df_valid['period_id'].unique():
            period_data = df_valid[df_valid['period_id'] == period_id]
            cutoff_time = period_data.index[0] + pd.Timedelta(seconds=SESSION_TRANSIENT_DROP)
            session_mask = period_data.index >= cutoff_time
            df_valid.loc[period_data.index[session_mask], 'session_id'] = f"{period_id}_0"

        # 将period_id和session_id合并回完整数据框
        df_processed['period_id'] = pd.NA
        df_processed['session_id'] = pd.NA
        for t in df_valid.index:
            df_processed.loc[t, 'period_id'] = df_valid.loc[t, 'period_id']
            df_processed.loc[t, 'session_id'] = df_valid.loc[t, 'session_id']

        # 只在有效session内进行插值
        valid_session_times = df_processed[df_processed['session_id'].notna()].index

        # 插值（严格按照需求文档，添加_interp标记列）
        for col in df_processed.columns:
            if '_标记' in col or 'period_id' in col or 'session_id' in col or col == 'is_valid' or col.endswith('_interp'):
                continue

            # 保存原始值掩码（用于标记插值）
            original_mask = df_processed[col].notna()

            # 创建临时列用于插值：非有效session内的数据设为NaN
            temp_col = df_processed[col].copy()
            # 将非有效session内的数据设为NaN，这样插值只会在有效session内进行
            temp_col[~df_processed.index.isin(valid_session_times)] = np.nan

            if col == state_name:
                # 状态参数前向填充
                temp_col = temp_col.ffill()
            elif pd.api.types.is_numeric_dtype(df_processed[col]):
                # 数值参数线性插值
                temp_col = temp_col.interpolate(method='linear', limit_area='inside')

            # 将插值后的值赋回原列
            df_processed[col] = temp_col

            # 添加插值标记列（只在有效session内标记）
            interp_col = f"{col}_interp"
            df_processed[interp_col] = False
            # 只在有效session内且原始值为NaN的标记为插值
            df_processed.loc[valid_session_times, interp_col] = ~original_mask.loc[valid_session_times]

        # 保存处理后的数据（包含完整1Hz时间轴）
        processed_file = base_dir / 'step2-state-filter' / 'results' / f'{terminal}_processed.csv'
        df_processed.to_csv(processed_file, encoding='utf-8-sig')

        # 返回完整的处理后数据（包含完整1Hz时间轴）
        # 同时在数据中标记有效数据以便后续使用
        terminal_data[terminal] = df_processed.copy()
        valid_count = df_processed['session_id'].notna().sum()
        print(f"{terminal}: 原始 {len(df_aligned)} → 有效 {valid_count} 行（总 {len(df_processed)} 行）→ {processed_file.name}")

    # 生成状态筛选报告
    generate_state_filter_report(step1_data, terminal_data, base_dir)

    # 生成有效数据分布图表
    generate_valid_distribution_plots(step1_data, terminal_data, base_dir)

    return terminal_data

def step3_error_calc(terminal_data, base_dir):
    """Step 3: 指向误差计算（从 Step 2 处理后文件读取，使用插值好的数据，保持 1Hz 采样率一致）"""
    print("\n" + "="*60)
    print("Step 3: 指向误差计算")
    print("="*60)

    all_errors = {}
    stats_report = []

    for terminal, config in TERMINALS.items():
        # 从 Step 2 处理后文件读取完整数据（包含完整 1Hz 时间轴和插值好的参数）
        processed_file = base_dir / 'step2-state-filter' / 'results' / f'{terminal}_processed.csv'
        if not processed_file.exists():
            print(f"{terminal}: 未找到处理后文件，跳过")
            continue

        df = pd.read_csv(processed_file, parse_dates=[0], index_col=0)
        config = TERMINALS[terminal]
        error_params = config['error_params']

        # 获取参数中文名称
        A_t_name = get_param_name(error_params['A_t'])
        A_r_name = get_param_name(error_params['A_r'])
        E_t_name = get_param_name(error_params['E_t'])
        E_r_name = get_param_name(error_params['E_r'])

        # 获取 Step 2 中已经插值好的参数值
        A_t = df[A_t_name]
        A_r = df[A_r_name]
        E_t = df[E_t_name]
        E_r = df[E_r_name]

        # 在完整时间轴上计算误差（只要参数有值就计算，使用 Step 2 插值好的数据）
        delta_A = (A_t - A_r + 180) % 360 - 180  # 方位角环绕处理
        delta_E = E_t - E_r
        theta_error = np.sqrt((delta_A * np.cos(np.radians(E_r)))**2 + delta_E**2)

        df['delta_A'] = delta_A
        df['delta_E'] = delta_E
        df['theta_error'] = theta_error

        # 保存误差数据（包含完整 1Hz 时间轴，以及 session_id 列）
        error_file = base_dir / 'step3-error-calc' / 'results' / f'error_{terminal}.csv'
        df[['delta_A', 'delta_E', 'theta_error', 'session_id']].to_csv(error_file, encoding='utf-8-sig')

        # 统计指标（只使用有效 session 内的数据计算）
        valid_mask = df['session_id'].notna()
        stats = {
            '终端': terminal,
            '数据点数': valid_mask.sum(),
            '方位误差_均值': delta_A[valid_mask].mean() if valid_mask.any() else np.nan,
            '方位误差_标准差': delta_A[valid_mask].std() if valid_mask.any() else np.nan,
            '方位误差_RMS': np.sqrt((delta_A[valid_mask]**2).mean()) if valid_mask.any() else np.nan,
            '方位误差_P95': delta_A[valid_mask].quantile(0.95) if valid_mask.any() else np.nan,
            '方位误差_P99': delta_A[valid_mask].quantile(0.99) if valid_mask.any() else np.nan,
            '俯仰误差_均值': delta_E[valid_mask].mean() if valid_mask.any() else np.nan,
            '俯仰误差_标准差': delta_E[valid_mask].std() if valid_mask.any() else np.nan,
            '俯仰误差_RMS': np.sqrt((delta_E[valid_mask]**2).mean()) if valid_mask.any() else np.nan,
            '俯仰误差_P95': delta_E[valid_mask].quantile(0.95) if valid_mask.any() else np.nan,
            '俯仰误差_P99': delta_E[valid_mask].quantile(0.99) if valid_mask.any() else np.nan,
            '综合误差_均值': theta_error[valid_mask].mean() if valid_mask.any() else np.nan,
            '综合误差_RMS': np.sqrt((theta_error[valid_mask]**2).mean()) if valid_mask.any() else np.nan,
            '综合误差_P95': theta_error[valid_mask].quantile(0.95) if valid_mask.any() else np.nan,
            '综合误差_P99': theta_error[valid_mask].quantile(0.99) if valid_mask.any() else np.nan,
        }
        stats_report.append(stats)
        all_errors[terminal] = df

        print(f"{terminal}: 平均综合误差 {stats['综合误差_均值']:.4f}° → {error_file.name}")
        print(f"  有效session内数据点数: {valid_mask.sum()}, 总时间点数: {len(df)}")

        # 误差时间序列图
        plot_error_timeseries(df, terminal, base_dir)
        # 误差分布直方图
        plot_error_histograms(df, terminal, base_dir)

    # 生成统计报告
    stats_df = pd.DataFrame(stats_report)
    report_file = base_dir / 'step3-error-calc' / 'reports' / 'error_statistics.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 指向误差统计报告\n\n")
        f.write(stats_df.to_markdown(index=False))
    print(f"\n统计报告 → {report_file.name}")

    # 终端对比箱线图
    if len(all_errors) > 1:
        plot_terminal_comparison(all_errors, base_dir)

    return all_errors

def plot_error_timeseries(df, terminal, base_dir):
    """绘制误差时间序列图"""
    fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=True)

    axes[0].plot(df.index, df['delta_A'], color='blue', linewidth=0.5, label='方位误差')
    axes[0].set_ylabel('误差 (°)')
    axes[0].set_title(f'{terminal} - 方位误差')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(df.index, df['delta_E'], color='green', linewidth=0.5, label='俯仰误差')
    axes[1].set_ylabel('误差 (°)')
    axes[1].set_title(f'{terminal} - 俯仰误差')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(df.index, df['theta_error'], color='red', linewidth=0.5, label='综合误差')
    axes[2].set_xlabel('时间')
    axes[2].set_ylabel('误差 (°)')
    axes[2].set_title(f'{terminal} - 综合指向误差')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    plt.xticks(rotation=45)

    plot_file = base_dir / 'step3-error-calc' / 'plots' / f'{terminal}_error_timeseries.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close()

def plot_terminal_comparison(all_errors, base_dir):
    """绘制终端对比箱线图"""
    # 方位误差箱线图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    azimuth_data = [df['delta_A'].dropna() for df in all_errors.values()]
    ax1.boxplot(azimuth_data, labels=all_errors.keys())
    ax1.set_ylabel('方位误差 (°)')
    ax1.set_title('各终端方位误差对比')
    ax1.grid(True, alpha=0.3)

    elevation_data = [df['delta_E'].dropna() for df in all_errors.values()]
    ax2.boxplot(elevation_data, labels=all_errors.keys())
    ax2.set_ylabel('俯仰误差 (°)')
    ax2.set_title('各终端俯仰误差对比')
    ax2.grid(True, alpha=0.3)

    plot_file1 = base_dir / 'step3-error-calc' / 'plots' / 'comparison_azimuth_boxplot.png'
    plot_file2 = base_dir / 'step3-error-calc' / 'plots' / 'comparison_elevation_boxplot.png'
    plt.savefig(plot_file1, dpi=150, bbox_inches='tight')
    plt.savefig(plot_file2, dpi=150, bbox_inches='tight')
    plt.close()

def plot_error_histograms(df, terminal, base_dir):
    """绘制误差分布直方图（按需求文档）"""
    from scipy.stats import norm

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 方位误差直方图
    ax1 = axes[0]
    delta_A_clean = df['delta_A'].dropna()
    if len(delta_A_clean) > 1:
        # 绘制直方图
        n, bins, patches = ax1.hist(delta_A_clean, bins=50, density=True, alpha=0.6, color='blue', label='直方图')

        # 绘制正态拟合曲线
        mu, sigma = delta_A_clean.mean(), delta_A_clean.std()
        x = np.linspace(bins[0], bins[-1], 100)
        ax1.plot(x, norm.pdf(x, mu, sigma), 'r-', lw=2, label=f'正态拟合: μ={mu:.4f}, σ={sigma:.4f}')

        ax1.set_xlabel('方位误差 (°)')
        ax1.set_ylabel('概率密度')
        ax1.set_title(f'{terminal} - 方位误差分布')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

    # 俯仰误差直方图
    ax2 = axes[1]
    delta_E_clean = df['delta_E'].dropna()
    if len(delta_E_clean) > 1:
        # 绘制直方图
        n, bins, patches = ax2.hist(delta_E_clean, bins=50, density=True, alpha=0.6, color='green', label='直方图')

        # 绘制正态拟合曲线
        mu, sigma = delta_E_clean.mean(), delta_E_clean.std()
        x = np.linspace(bins[0], bins[-1], 100)
        ax2.plot(x, norm.pdf(x, mu, sigma), 'r-', lw=2, label=f'正态拟合: μ={mu:.4f}, σ={sigma:.4f}')

        ax2.set_xlabel('俯仰误差 (°)')
        ax2.set_ylabel('概率密度')
        ax2.set_title(f'{terminal} - 俯仰误差分布')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

    plot_file = base_dir / 'step3-error-calc' / 'plots' / f'{terminal}_error_distribution.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close()


def generate_preprocessing_report(step1_data, base_dir):
    """生成 Step 1 预处理报告"""
    report_file = base_dir / 'step1-preprocessing' / 'reports' / 'preprocessing_report.md'

    report = []
    report.append("# 数据预处理报告\n")
    report.append(f"**生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**处理数据**: 31star 原始遥测数据\n")
    report.append(f"**处理包数量**: {len(step1_data)}\n")
    report.append("\n")
    report.append("## 各包详细信息\n")
    report.append("| 包编号 | 列数 | 行数 | 有效时间跨度 | 异常值检测列 | 数据有效性 |\n")
    report.append("|--------|------|------|------------|-----------|-----------|\n")

    for pkg_code, df in step1_data.items():
        start_time = df.index.min()
        end_time = df.index.max()
        duration = (end_time - start_time).total_seconds() / 3600
        flag_cols = [col for col in df.columns if col.endswith('_标记')]
        valid_ratio = (df.shape[0] - df[flag_cols].notna().any(axis=1).sum()) / df.shape[0]

        report.append(f"| {pkg_code} | {df.shape[1]} | {df.shape[0]} | {start_time} - {end_time} ({duration:.2f}h) | {len(flag_cols)} | {valid_ratio:.2%} |\n")

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(''.join(report))

    print(f"预处理报告 → {report_file.name}")


def generate_timeline_plots(step1_data, base_dir):
    """生成 Step 1 时间轴有效性图"""
    # 定义需要避开的时间类参数
    TIME_PARAM_KEYWORDS = ['时间', '秒', '毫秒', '微秒']

    for pkg_code, df in step1_data.items():
        # 找到数值列中数据最完整的列（避开时间类参数）
        numeric_cols = [col for col in df.columns if col not in [f"{c}_标记" for c in df.columns]]

        # 过滤掉时间类参数
        valid_cols = []
        for col in numeric_cols:
            # 检查列名是否包含时间类关键词
            is_time_param = any(keyword in col for keyword in TIME_PARAM_KEYWORDS)
            if not is_time_param:
                valid_cols.append((col, df[col].notna().sum()))

        valid_cols.sort(key=lambda x: x[1], reverse=True)

        if valid_cols:
            plot_col = valid_cols[0][0]
        else:
            # 如果没有找到非时间类参数，使用第一个数值列
            if numeric_cols:
                plot_col = numeric_cols[0]
            else:
                continue

        plot_file = base_dir / 'step1-preprocessing' / 'plots' / f'31star_pkg_{pkg_code}_timeline.png'

        # 绘图
        fig, ax1 = plt.subplots(figsize=(16, 6))

        ax1.plot(df.index, df[plot_col], color='blue', linewidth=1, label=f'{plot_col}')
        ax1.set_ylabel('物理量值', fontsize=12)
        ax1.set_xlabel('时间', fontsize=12)
        ax1.set_title(f'包 {pkg_code} - {plot_col} 时间轴与异常值检测', fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # 绘制异常值区域
        flag_col = f"{plot_col}_标记"
        if flag_col in df.columns:
            invalid_mask = df[flag_col].notna()
            invalid_times = df.index[invalid_mask]

            if not invalid_times.empty:
                # 创建临时的无效数据区域
                ax2 = ax1.twinx()
                ax2.set_ylabel('异常值检测', fontsize=12, color='red')
                ax2.set_ylim(0, 1)
                ax2.plot(df.index, df[flag_col].notna().astype(int), color='red', alpha=0.3, label='异常值')
                ax2.legend(loc='upper right')

        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"时间轴图 → 31star_pkg_{pkg_code}_timeline.png")

    # 生成汇总甘特图
    generate_summary_gantt(step1_data, base_dir)


def generate_summary_gantt(step1_data, base_dir):
    """生成 Step 1 汇总甘特图，展示各遥测包的数据覆盖情况"""
    print("\n生成各遥测包数据覆盖汇总甘特图...")

    plot_file = base_dir / 'step1-preprocessing' / 'plots' / 'summary_packages_gantt.png'

    # 定义需要避开的时间类参数
    TIME_PARAM_KEYWORDS = ['时间', '秒', '毫秒', '微秒']

    # 找到所有包的时间范围
    all_packages = []
    t_min_all = None
    t_max_all = None

    for pkg_code, df in step1_data.items():
        # 找到数据最完整的非时间类参数
        numeric_cols = [col for col in df.columns if not col.endswith('_标记')]

        # 过滤掉时间类参数
        valid_cols = []
        for col in numeric_cols:
            is_time_param = any(keyword in col for keyword in TIME_PARAM_KEYWORDS)
            if not is_time_param:
                valid_cols.append((col, df[col].notna().sum()))

        valid_cols.sort(key=lambda x: x[1], reverse=True)

        if valid_cols:
            plot_col = valid_cols[0][0]
        else:
            if numeric_cols:
                plot_col = numeric_cols[0]
            else:
                continue

        # 找到该参数有数据的时间点
        data_mask = df[plot_col].notna()

        t_min = df.index.min()
        t_max = df.index.max()

        if t_min_all is None or t_min < t_min_all:
            t_min_all = t_min
        if t_max_all is None or t_max > t_max_all:
            t_max_all = t_max

        all_packages.append({
            'code': pkg_code,
            'data_mask': data_mask,
            'df': df,
            't_min': t_min,
            't_max': t_max
        })

    if not all_packages:
        return

    # 创建统一时间轴
    unified_index = pd.date_range(
        start=t_min_all.floor('S'),
        end=t_max_all.ceil('S'),
        freq=RESAMPLE_FREQ
    )

    # 为每个包创建状态标记
    pkg_status = {}
    for pkg in all_packages:
        status = pd.Series([0]*len(unified_index), index=unified_index)

        # 标记有数据的点
        for t in pkg['df'].index[pkg['data_mask']]:
            dt = unified_index - t
            abs_dt = np.abs(dt.total_seconds())
            min_dt_idx = abs_dt.argmin()
            if abs_dt[min_dt_idx] <= 0.5:  # 500ms容差
                status.iloc[min_dt_idx] = 1

        pkg_status[pkg['code']] = status

    # 绘图
    n_pkgs = len(all_packages)
    fig, ax = plt.subplots(figsize=(16, max(6, n_pkgs * 0.6)))

    # 定义颜色
    colors = {
        0: 'white',
        1: '#4A90D9'
    }
    labels = {
        0: '无数据',
        1: '有数据'
    }

    y_positions = list(range(n_pkgs))
    pkg_codes = [pkg['code'] for pkg in all_packages]

    # 绘制每个包的数据覆盖区间
    for i, pkg in enumerate(all_packages):
        status = pkg_status[pkg['code']]

        # 找到连续相同状态的区间
        if len(status) > 0:
            current_status = status.iloc[0]
            start_time = status.index[0]

            for j in range(1, len(status)):
                if status.iloc[j] != current_status:
                    # 绘制区间
                    if current_status == 1:
                        ax.axvspan(
                            start_time,
                            status.index[j-1],
                            ymin=(i - 0.4) / n_pkgs,
                            ymax=(i + 0.4) / n_pkgs,
                            color=colors[current_status],
                            alpha=0.8
                        )
                    current_status = status.iloc[j]
                    start_time = status.index[j]

            # 绘制最后一个区间
            if current_status == 1:
                ax.axvspan(
                    start_time,
                    status.index[-1],
                    ymin=(i - 0.4) / n_pkgs,
                    ymax=(i + 0.4) / n_pkgs,
                    color=colors[current_status],
                    alpha=0.8
                )

    # 设置y轴
    ax.set_yticks(y_positions)
    ax.set_yticklabels([f'包 {code}' for code in pkg_codes])
    ax.set_ylim(-0.5, n_pkgs - 0.5)

    # 设置x轴
    ax.set_xlabel('时间', fontsize=12)
    ax.set_title('各遥测包数据覆盖情况汇总（甘特图）', fontsize=14)
    ax.grid(True, alpha=0.3, axis='x')

    # 创建图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=colors[0], edgecolor='black', label=labels[0]),
        Patch(facecolor=colors[1], edgecolor='black', label=labels[1])
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"汇总甘特图 → summary_packages_gantt.png")


def generate_state_filter_report(step1_data, terminal_data, base_dir):
    """生成 Step 2 状态筛选报告"""
    report_file = base_dir / 'step2-state-filter' / 'reports' / 'state_filter_report.md'

    report = []
    report.append("# 状态筛选与数据处理报告\n")
    report.append(f"**生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**处理数据**: 31star 遥测数据\n")
    report.append(f"**有效终端数量**: {len(terminal_data)}\n")
    report.append("\n")
    report.append("## 各终端详细信息\n")
    report.append("| 终端 | period数量 | session数量 | 原始行数 | 有效数据点数 | 丢弃行数 | 有效数据时长 | 丢弃原因统计 |\n")
    report.append("|------|-----------|-----------|---------|-----------|---------|-----------|-----------|\n")

    for terminal, config in TERMINALS.items():
        if terminal in terminal_data:
            df = terminal_data[terminal]
            pkg_code = config['package']
            state_name = config['state_name']

            # 从step1_data获取原始数据
            if pkg_code in step1_data:
                raw_df = step1_data[pkg_code]
                raw_length = len(raw_df)

            # 统计period和session数量
            period_count = df['period_id'].nunique()
            session_count = df['session_id'].nunique()
            valid_length = len(df)
            discarded = raw_length - valid_length
            duration = (df.index.max() - df.index.min()).total_seconds() / 60

            # 丢弃原因统计
            discard_reasons = "过渡丢弃"

            report.append(f"| {terminal} | {period_count} | {session_count} | {raw_length} | {valid_length} | {discarded} | {duration:.1f}分钟 | {discard_reasons} |\n")

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(''.join(report))

    print(f"状态筛选报告 → state_filter_report.md")


def generate_valid_distribution_plots(step1_data, terminal_data, base_dir):
    """生成 Step 2 有效数据分布图表（甘特图效果）"""
    for terminal, config in TERMINALS.items():
        pkg_code = config['package']
        state_name = config['state_name']

        plot_file = base_dir / 'step2-state-filter' / 'plots' / f'{terminal}_valid_distribution.png'

        if pkg_code in step1_data and terminal in terminal_data:
            # 获取原始数据和处理后的数据
            raw_df = step1_data[pkg_code]
            processed_df = terminal_data[terminal]

            # 构建完整的时间轴（从原始数据到处理后数据的完整范围）
            if len(raw_df) > 0 and len(processed_df) > 0:
                t_min = min(raw_df.index.min(), processed_df.index.min())
                t_max = max(raw_df.index.max(), processed_df.index.max())
            elif len(raw_df) > 0:
                t_min, t_max = raw_df.index.min(), raw_df.index.max()
            else:
                t_min, t_max = processed_df.index.min(), processed_df.index.max()

            # 创建统一1Hz时间轴（整秒）
            full_index = pd.date_range(start=t_min.floor('S'), end=t_max.ceil('S'), freq=RESAMPLE_FREQ)

            # 标记每个时间点的状态
            # 0: 无效数据（白色）
            # 1: 有效数据（原始值，浅色）
            # 2: 插值数据（深色）
            status = pd.Series([0]*len(full_index), index=full_index)

            # 第一步：标记原始数据中存在的点（未筛选前）
            if len(raw_df) > 0:
                # 先将所有原始数据时间点标记为有效（临时）
                for t in raw_df.index:
                    # 找到最近的统一时间轴点（500ms容差）
                    dt = full_index - t
                    abs_dt = np.abs(dt.total_seconds())
                    min_dt_idx = abs_dt.argmin()
                    if abs_dt[min_dt_idx] <= 0.5:  # 500ms
                        status.iloc[min_dt_idx] = 1  # 临时标记为有原始数据

            # 第二步：标记处理后的有效数据
            if len(processed_df) > 0:
                # 找到一个有_interp标记的列（数值列）
                interp_col = None
                for col in processed_df.columns:
                    if col.endswith('_interp'):
                        interp_col = col
                        break

                for t in processed_df.index:
                    dt = full_index - t
                    abs_dt = np.abs(dt.total_seconds())
                    min_dt_idx = abs_dt.argmin()
                    if abs_dt[min_dt_idx] <= 0.5:  # 500ms
                        if interp_col and interp_col in processed_df.columns:
                            # 检查是否是插值数据
                            if processed_df.loc[t, interp_col]:
                                status.iloc[min_dt_idx] = 2  # 插值数据（深色）
                            else:
                                status.iloc[min_dt_idx] = 1  # 原始有效数据（浅色）
                        else:
                            status.iloc[min_dt_idx] = 1  # 默认标记为有效数据

            # 找到连续相同状态的区间
            intervals = []
            if len(status) > 0:
                current_status = status.iloc[0]
                start_time = status.index[0]

                for i in range(1, len(status)):
                    if status.iloc[i] != current_status:
                        intervals.append((start_time, status.index[i-1], current_status))
                        current_status = status.iloc[i]
                        start_time = status.index[i]

                # 添加最后一个区间
                intervals.append((start_time, status.index[-1], current_status))

            # 绘图
            fig, ax = plt.subplots(figsize=(16, 5))

            # 定义颜色：0-白色，1-蓝色，2-红色（对比度更高）
            colors = {
                0: 'white',
                1: '#87CEEB',  # 浅蓝
                2: '#FF6B6B'   # 红色
            }
            labels = {
                0: '无效数据',
                1: '有效数据（原始）',
                2: '有效数据（插值）'
            }

            # 绘制每个区间
            for start, end, s in intervals:
                ax.axvspan(start, end, color=colors[s], alpha=0.8)

            # 创建图例
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor=colors[0], edgecolor='black', label=labels[0]),
                Patch(facecolor=colors[1], edgecolor='black', label=labels[1]),
                Patch(facecolor=colors[2], edgecolor='black', label=labels[2])
            ]
            ax.legend(handles=legend_elements, loc='upper right')

            ax.set_yticks([])  # 隐藏y轴刻度
            ax.set_xlabel('时间', fontsize=12)
            ax.set_title(f'{terminal} - 有效数据分布（甘特图）', fontsize=14)
            ax.grid(True, alpha=0.3, axis='x')

            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(plot_file, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"有效数据分布图 → {terminal}_valid_distribution.png")

def main():
    csv_file = Path(__file__).parent / 'ori-data' / '31star' / 'CSCN-A0031_TelPlatformParsed_20260312063411_1.csv'

    if not csv_file.exists():
        print(f"文件不存在: {csv_file}")
        sys.exit(1)

    base_dir = cleanup_and_create_dirs()

    # Step 1: 数据预处理
    step1_data = step1_preprocessing(csv_file, base_dir)

    # Step 2: 状态筛选
    terminal_data = step2_state_filter(step1_data, base_dir)

    # Step 3: 误差计算
    step3_error_calc(terminal_data, base_dir)

    print("\n" + "="*60)
    print("验证完成! 输出目录:", base_dir)
    print("="*60)

if __name__ == '__main__':
    main()
