#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试状态列的实际值
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

csv_path = Path(__file__).parent / 'ori-data' / '31star' / 'CSCN-A0031_TelPlatformParsed_20260307070624_1.csv'

df = pd.read_csv(csv_path, parse_dates=['satelliteTime'])

print("="*70)
print("调试状态列的实际值")
print("="*70)

# 先看一下TMJB3031（B1状态参数）的原始数据
print("\n--- B1 状态参数 TMJB3031 ---")
b1_state = df[df['paramCode'] == 'TMJB3031']
print(f"原始数据行数: {len(b1_state)}")
if len(b1_state) > 0:
    print(f"parsedValue 的唯一值: {b1_state['parsedValue'].unique()}")
    print(f"parsedValue 的数据类型: {b1_state['parsedValue'].dtype}")
    print(f"前10个值:")
    print(b1_state[['satelliteTime', 'parsedValue', 'translateValue']].head(10))

# 看看是否有translateValue
print(f"\ntranslateValue 的唯一值: {b1_state['translateValue'].unique() if 'translateValue' in b1_state.columns else 'N/A'}")

# 检查数据类型
print(f"\n--- 数据类型检查 ---")
sample_value = b1_state['parsedValue'].iloc[0] if len(b1_state) > 0 else None
print(f"样本值: {sample_value}")
print(f"样本值类型: {type(sample_value)}")

# 检查它是不是等于6
if sample_value is not None:
    print(f"sample_value == 6: {sample_value == 6}")
    print(f"sample_value == '6': {sample_value == '6'}")
    print(f"int(sample_value) == 6: {int(sample_value) == 6 if pd.notna(sample_value) else 'N/A'}")
