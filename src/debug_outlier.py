#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试异常值检测为什么没有生效
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

csv_path = Path(__file__).parent.parent / 'ori-data' / '31star' / 'CSCN-A0031_TelPlatformParsed_20260307070624_1.csv'
df = pd.read_csv(csv_path, nrows=10000, parse_dates=['satelliteTime'])

# 只处理136包
df_pkg = df[df['packageCode'] == '136'].copy()

# pivot成宽格式
df_wide = df_pkg.pivot_table(
    index='satelliteTime',
    columns='paramCode',
    values='parsedValue',
    aggfunc='last'
)

print("pivot后的列名:")
print(list(df_wide.columns))

# 将所有数值列转换为数值类型
numeric_columns = []
for col in df_wide.columns:
    try:
        numeric_series = pd.to_numeric(df_wide[col], errors='coerce')
        if numeric_series.notna().any():
            df_wide[col] = numeric_series
            numeric_columns.append(col)
    except:
        pass

print(f"\nnumeric_columns: {numeric_columns}")

# 测试异常值检测
col = 'TMJB3079'  # 选择一个数值列
if col in numeric_columns:
    print(f"\n测试列: {col} = {get_param_name(col)}")
    print(f"值范围: {df_wide[col].min()} 到 {df_wide[col].max()}")
    print(f"样本值: {df_wide[col].head(10).values}")

    # 检查3σ检测
    rolling_mean = df_wide[col].rolling(window=60, min_periods=10).mean()
    rolling_std = df_wide[col].rolling(window=60, min_periods=10).std()
    mask_stat = (df_wide[col] - rolling_mean).abs() > 3 * rolling_std
    print(f"3σ检测到的异常值数量: {mask_stat.sum()}")

    # 检查变化率检测
    diff = df_wide[col].diff().abs()
    threshold = diff.quantile(0.99)
    mask_spike = diff > threshold
    print(f"变化率检测到的异常值数量: {mask_spike.sum()} (阈值: {threshold})")
