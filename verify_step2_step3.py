#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证脚本 - Step 2 & Step 3: 状态筛选与误差计算
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

STEP1_OUTPUT = Path(__file__).parent / 'output' / 'step1-preprocessing' / 'results'
STEP2_OUTPUT = Path(__file__).parent / 'output' / 'step2-state-filter'
STEP3_OUTPUT = Path(__file__).parent / 'output' / 'step3-error-calc'

for dir_path in [STEP2_OUTPUT, STEP3_OUTPUT]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 可配置参数
VALID_STATE_VALUE = 6
CONTINUITY_GAP_SEC = 10
SESSION_TRANSIENT_DROP = 10
RESAMPLE_FREQ = '1S'

# 终端配置
TERMINAL_CONFIGS = {
    'B1': {
        'package_code': '136',
        'key_state_param': 'B1慢-捕跟工作状态',
        'error_params': {
            'A_t': 'B1慢-捕跟伺服理论方位角',
            'A_r': 'B1慢-捕跟伺服实时方位轴角',
            'E_t': 'B1慢-捕跟伺服理论俯仰角',
            'E_r': 'B1慢-捕跟伺服实时俯仰轴角',
        }
    },
    'B2': {
        'package_code': '138',
        'key_state_param': 'B2慢-捕跟工作状态',
        'error_params': {
            'A_t': 'B2慢-捕跟伺服理论方位角',
            'A_r': 'B2慢-捕跟伺服实时方位轴角',
            'E_t': 'B2慢-捕跟伺服理论俯仰角',
            'E_r': 'B2慢-捕跟伺服实时俯仰轴角',
        }
    },
    'A1-1': {
        'package_code': '134',
        'key_state_param': 'A3慢-1-激光终端状态',
        'error_params': {
            'A_t': 'A3慢-1-方位电机目标位置',
            'A_r': 'A3慢-1-方位电机当前位置',
            'E_t': 'A3慢-1-俯仰电机目标位置',
            'E_r': 'A3慢-1-俯仰电机当前位置',
        }
    },
    'A1-2': {
        'package_code': '134',
        'key_state_param': 'A3慢-2-激光终端状态',
        'error_params': {
            'A_t': 'A3慢-2-方位电机目标位置',
            'A_r': 'A3慢-2-方位电机当前位置',
            'E_t': 'A3慢-2-俯仰电机目标位置',
            'E_r': 'A3慢-2-俯仰电机当前位置',
        }
    },
}


def load_wide_data(package_code):
    """加载Step 1输出的宽格式数据"""
    file_path = STEP1_OUTPUT / f'31star_pkg_{package_code}_wide.csv'
    if not file_path.exists():
        return None
    df = pd.read_csv(file_path, parse_dates=['satelliteTime'], index_col='satelliteTime')
    return df


def filter_valid_sessions(df, key_state_param):
    """Step 2: 筛选有效数据段"""
    df = df.copy()

    # 步骤A: 识别连续时间段
    df = df.sort_index()
    valid_state_mask = df[key_state_param].notna()
    time_diff = df.index.to_series().diff()
    gap_mask = time_diff > pd.Timedelta(seconds=CONTINUITY_GAP_SEC)

    # 分配period_id
    df['period_id'] = (gap_mask & valid_state_mask).cumsum()

    # 步骤B: 筛选有效状态
    df_filtered = df[df[key_state_param] == VALID_STATE_VALUE].copy()

    if len(df_filtered) == 0:
        return pd.DataFrame()

    # 步骤C: 过渡期丢弃
    df_filtered = df_filtered.sort_index()
    sessions = []
    for period_id in df_filtered['period_id'].unique():
        period_data = df_filtered[df_filtered['period_id'] == period_id]
        cutoff_time = period_data.index[0] + pd.Timedelta(seconds=SESSION_TRANSIENT_DROP)
        session_data = period_data[period_data.index >= cutoff_time]
        if len(session_data) > 0:
            sessions.append(session_data)

    if len(sessions) == 0:
        return pd.DataFrame()

    result = pd.concat(sessions)
    return result


def interpolate_data(df):
    """插值处理"""
    df = df.copy()
    for col in df.columns:
        if col in ['period_id']:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].interpolate(method='linear')
    return df


def calculate_pointing_error(df, terminal_name, config):
    """Step 3: 计算指向误差"""
    df = df.copy()
    params = config['error_params']

    A_t = df[params['A_t']]
    A_r = df[params['A_r']]
    E_t = df[params['E_t']]
    E_r = df[params['E_r']]

    # 方位角环绕处理
    delta_A = (A_t - A_r + 180) % 360 - 180
    delta_E = E_t - E_r

    # 综合指向误差
    theta_error = np.sqrt(
        (delta_A * np.cos(np.radians(E_r)))**2 +
        delta_E**2
    )

    df['delta_A'] = delta_A
    df['delta_E'] = delta_E
    df['theta_error'] = theta_error

    return df


def calculate_statistics(df, terminal_name):
    """计算误差统计指标"""
    stats = {}
    for col in ['delta_A', 'delta_E', 'theta_error']:
        if col not in df.columns:
            continue
        data = df[col].dropna()
        if len(data) == 0:
            continue

        stats[col] = {
            'mean': data.mean(),
            'std': data.std(),
            'rms': np.sqrt((data**2).mean()),
            'p95': data.quantile(0.95),
            'p99': data.quantile(0.99),
            'count': len(data),
        }
    return stats


def main():
    print("开始处理 Step 2 & Step 3...")

    all_stats = {}

    for terminal_name, config in TERMINAL_CONFIGS.items():
        print(f"\n处理终端: {terminal_name}")

        # 加载数据
        df = load_wide_data(config['package_code'])
        if df is None:
            print(f"  跳过: 未找到包 {config['package_code']} 的数据")
            continue

        if config['key_state_param'] not in df.columns:
            print(f"  跳过: 未找到关键参数 {config['key_state_param']}")
            continue

        # Step 2: 筛选有效数据
        df_filtered = filter_valid_sessions(df, config['key_state_param'])
        if len(df_filtered) == 0:
            print(f"  无有效数据")
            continue

        # 插值
        df_interp = interpolate_data(df_filtered)

        # 保存Step 2结果
        step2_file = STEP2_OUTPUT / f'{terminal_name}_processed.csv'
        df_interp.to_csv(step2_file, encoding='utf-8-sig')
        print(f"  Step 2 保存: {step2_file}")

        # Step 3: 计算误差
        df_error = calculate_pointing_error(df_interp, terminal_name, config)

        # 保存Step 3结果
        step3_file = STEP3_OUTPUT / f'error_{terminal_name}.csv'
        df_error.to_csv(step3_file, encoding='utf-8-sig')
        print(f"  Step 3 保存: {step3_file}")

        # 统计
        stats = calculate_statistics(df_error, terminal_name)
        all_stats[terminal_name] = stats
        print(f"  有效数据点数: {len(df_error)}")

    # 保存统计报告
    if all_stats:
        report_file = STEP3_OUTPUT / 'error_statistics.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 指向误差统计报告\n\n")
            for terminal, stats in all_stats.items():
                f.write(f"## {terminal}\n\n")
                for col, col_stats in stats.items():
                    f.write(f"### {col}\n")
                    for key, value in col_stats.items():
                        f.write(f"- {key}: {value:.6f}\n")
                    f.write("\n")
        print(f"\n统计报告: {report_file}")

    print("\n完成!")


if __name__ == '__main__':
    main()
