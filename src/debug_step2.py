#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Step2：为什么没有找到有效数据
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

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

base_dir = Path(__file__).parent.parent / 'output' / 'step1-preprocessing' / 'results'

print("="*70)
print("调试 Step2：状态筛选")
print("="*70)

for terminal, config in TERMINALS.items():
    pkg_code = config['package']
    csv_file = base_dir / f'31star_pkg_{pkg_code}_wide.csv'

    print(f"\n--- {terminal} ---")
    print(f"检查文件: {csv_file.name}")

    if not csv_file.exists():
        print(f"  错误：文件不存在！")
        continue

    df = pd.read_csv(csv_file, parse_dates=['satelliteTime'], index_col='satelliteTime')
    state_name = config['state_name']

    print(f"  列名: {list(df.columns)}")
    print(f"  状态列名: {state_name}")

    if state_name not in df.columns:
        print(f"  错误：找不到状态参数！")
        continue

    print(f"  状态值唯一值: {df[state_name].unique()}")
    print(f"  状态值数量: {len(df[state_name].dropna())}")
    print(f"  状态==6的数量: {len(df[df[state_name] == 6])}")

    # 显示一些状态==6的行
    valid_data = df[df[state_name] == 6]
    if len(valid_data) > 0:
        print(f"  有效数据时间范围: {valid_data.index.min()} 到 {valid_data.index.max()}")
        print(f"  前5个有效数据点:")
        print(valid_data[[state_name]].head())
