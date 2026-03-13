#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试完整流程：检查为什么step2没有找到有效数据
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

# 配置常量
OUTLIER_SIGMA = 3
VALID_STATE_VALUE = 6
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

csv_path = Path(__file__).parent.parent / 'ori-data' / '31star' / 'CSCN-A0031_TelPlatformParsed_20260307070624_1.csv'

print("="*70)
print("调试完整流程")
print("="*70)

# Step 1: 模拟数据预处理
df = pd.read_csv(csv_path, parse_dates=['satelliteTime'])
package_groups = df.groupby('packageCode')

step1_data = {}
for pkg_code, df_pkg in package_groups:
    # 长格式转宽格式
    df_wide = df_pkg.pivot_table(
        index='satelliteTime',
        columns='paramCode',
        values='parsedValue',
        aggfunc='last'
    )

    # 列名替换为中文
    rename_map = {}
    for col in df_wide.columns:
        rename_map[col] = get_param_name(col)
    df_wide = df_wide.rename(columns=rename_map)

    step1_data[pkg_code] = df_wide

print(f"\nStep1 完成，包含 {len(step1_data)} 个包")
print(f"Step1 键列表: {list(step1_data.keys())}")

# Step 2: 模拟状态筛选
print(f"\n--- Step 2 调试 ---")

for terminal, config in TERMINALS.items():
    pkg_code = config['package']
    print(f"\n{terminal}:")
    print(f"  配置的 package code: '{pkg_code}'")

    if pkg_code not in step1_data:
        print(f"  [错误] 在 step1_data 中找不到包 '{pkg_code}'！")
        print(f"  可用的包: {list(step1_data.keys())}")
        continue

    print(f"  [OK] 找到包 '{pkg_code}'")

    df = step1_data[pkg_code].copy()
    state_name = config['state_name']

    print(f"  状态参数名: '{state_name}'")

    if state_name not in df.columns:
        print(f"  [错误] 找不到状态参数 '{state_name}'！")
        print(f"  可用的列: {list(df.columns)}")
        continue

    print(f"  [OK] 找到状态参数 '{state_name}'")

    # 筛选有效数据: 状态 == 6
    df_valid = df[df[state_name] == VALID_STATE_VALUE].copy()
    print(f"  状态值 == 6 的数据点数: {len(df_valid)}")

    if len(df_valid) == 0:
        print(f"  [错误] 没有有效数据！")
        continue

    print(f"  [OK] 找到 {len(df_valid)} 个有效数据点")

    # 显示一些基本信息
    print(f"  有效数据时间范围: {df_valid.index.min()} 到 {df_valid.index.max()}")
