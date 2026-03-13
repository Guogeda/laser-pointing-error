#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查标记列是否被填充了值
"""
import pandas as pd
import numpy as np
from pathlib import Path

csv_file = Path(__file__).parent.parent / 'output' / 'step1-preprocessing' / 'results' / '31star_pkg_136_wide.csv'
df = pd.read_csv(csv_file)

print("="*70)
print("检查标记列是否被填充了值")
print("="*70)

flag_cols = [col for col in df.columns if col.endswith('_标记')]
print(f"\n标记列数量: {len(flag_cols)}")
print(f"标记列: {flag_cols}")

for col in flag_cols:
    non_nan_count = df[col].notna().sum()
    unique_values = df[col].dropna().unique()
    if len(unique_values) > 0:
        print(f"\n{col}:")
        print(f"  非空值数量: {non_nan_count}")
        print(f"  唯一值: {unique_values}")
    else:
        print(f"\n{col}: 全空")
