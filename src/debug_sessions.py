#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试 session 识别逻辑
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

OUTPUT_DIR = Path(__file__).parent.parent / 'output'
STEP1_OUTPUT = OUTPUT_DIR / 'step1-preprocessing' / 'results'
STEP2_OUTPUT = OUTPUT_DIR / 'step2-state-filter' / 'results'

# 配置常量
VALID_STATE_VALUE = '6'
CONTINUITY_GAP_SEC = 10
SESSION_TRANSIENT_DROP = 10
RESAMPLE_FREQ = '1S'

# 终端配置
TERMINALS = {
    'B1': {
        'package': '136',
        'state_param': 'TMJB3031',
        'state_name': 'B1慢-捕跟工作状态',
    },
    'B2': {
        'package': '138',
        'state_param': 'TMJB4031',
        'state_name': 'B2慢-捕跟工作状态',
    },
    'A1-1': {
        'package': '134',
        'state_param': 'TMJA3115',
        'state_name': 'A3慢-1-激光终端状态',
    },
    'A1-2': {
        'package': '134',
        'state_param': 'TMJA3239',
        'state_name': 'A3慢-2-激光终端状态',
    },
}

def load_step1_data(pkg_code):
    """加载 Step 1 数据"""
    file = STEP1_OUTPUT / f'31star_pkg_{pkg_code}_wide.csv'
    if not file.exists():
        return None
    return pd.read_csv(file, parse_dates=['satelliteTime'], index_col='satelliteTime')

def load_common_params():
    """加载公共参数"""
    for pkg_code in ['82', '81']:
        file = STEP1_OUTPUT / f'31star_pkg_{pkg_code}_wide.csv'
        if file.exists():
            return pd.read_csv(file, parse_dates=['satelliteTime'], index_col='satelliteTime')
    return None

def analyze_terminal(terminal, config):
    """分析单个终端的 session"""
    print(f"\n{'='*60}")
    print(f"分析终端: {terminal}")
    print(f"{'='*60}")

    # 加载数据
    df = load_step1_data(config['package'])
    if df is None:
        print(f"未找到包 {config['package']} 的数据")
        return

    common_df = load_common_params()

    # 合并公共参数
    if common_df is not None:
        df = df.merge(common_df, how='left', left_index=True, right_index=True)

    state_name = config['state_name']
    if state_name not in df.columns:
        print(f"未找到状态参数 {state_name}")
        return

    # 时间对齐到1Hz
    start_time = df.index.min().floor('S')
    end_time = df.index.max().ceil('S')
    unified_index = pd.date_range(start=start_time, end=end_time, freq=RESAMPLE_FREQ)
    df_aligned = df.reindex(unified_index, method='nearest', tolerance=pd.Timedelta('500ms'))

    print(f"\n时间对齐后: {len(df_aligned)} 行")
    print(f"时间范围: {start_time} 到 {end_time}")

    # 标记有效性
    df_processed = df_aligned.copy()
    df_processed['is_valid'] = (
        (df_processed[state_name] == VALID_STATE_VALUE) |
        (pd.to_numeric(df_processed[state_name], errors='coerce') == 6)
    )

    df_valid = df_processed[df_processed['is_valid']].copy()
    print(f"\n有效数据点: {len(df_valid)} 行")

    if len(df_valid) == 0:
        return

    # 识别连续时间段
    df_valid = df_valid.sort_index()
    time_diff = df_valid.index.to_series().diff()

    print(f"\n时间差统计:")
    print(f"  最小值: {time_diff.min()}")
    print(f"  最大值: {time_diff.max()}")
    print(f"  均值: {time_diff.mean()}")
    print(f"  大于 {CONTINUITY_GAP_SEC} 秒的间隔数: {(time_diff > pd.Timedelta(seconds=CONTINUITY_GAP_SEC)).sum()}")

    # 显示前几个时间差
    print(f"\n前20个时间差:")
    for i, (t, td) in enumerate(time_diff.head(20).items()):
        print(f"  {i+1}. {t}: {td}")

    gap_mask = time_diff > pd.Timedelta(seconds=CONTINUITY_GAP_SEC)
    df_valid['period_id'] = gap_mask.cumsum()

    print(f"\nperiod_id 唯一值: {df_valid['period_id'].unique()}")
    print(f"period 数量: {df_valid['period_id'].nunique()}")

    # 显示每个 period 的信息
    print(f"\n各 period 详细信息:")
    for period_id in df_valid['period_id'].unique():
        period_data = df_valid[df_valid['period_id'] == period_id]
        print(f"\n  period {period_id}:")
        print(f"    开始时间: {period_data.index[0]}")
        print(f"    结束时间: {period_data.index[-1]}")
        print(f"    数据点数: {len(period_data)}")
        print(f"    时长: {(period_data.index[-1] - period_data.index[0]).total_seconds()} 秒")

        # 分配 session_id
        cutoff_time = period_data.index[0] + pd.Timedelta(seconds=SESSION_TRANSIENT_DROP)
        session_mask = period_data.index >= cutoff_time
        print(f"    过渡期截止时间: {cutoff_time}")
        print(f"    session 数据点数: {session_mask.sum()}")

def main():
    print("="*60)
    print("调试 Session 识别逻辑")
    print("="*60)

    for terminal, config in TERMINALS.items():
        analyze_terminal(terminal, config)

    print("\n" + "="*60)
    print("完成!")
    print("="*60)

if __name__ == '__main__':
    main()
