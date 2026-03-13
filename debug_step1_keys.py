#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Step1：检查packageCode的格式
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

csv_path = Path(__file__).parent / 'ori-data' / '31star' / 'CSCN-A0031_TelPlatformParsed_20260307070624_1.csv'

df = pd.read_csv(csv_path, nrows=100)

print("="*70)
print("调试 Step1：检查packageCode格式")
print("="*70)

print(f"\n原始数据前5行:")
print(df[['packageCode', 'paramCode']].head())

print(f"\npackageCode 唯一值: {df['packageCode'].unique()}")
print(f"packageCode 类型: {type(df['packageCode'].iloc[0])}")

# 检查是否是字符串格式，如果是，看看是否是十六进制
first_pkg_code = df['packageCode'].iloc[0]
print(f"\n第一个packageCode: {first_pkg_code}")
print(f"是否是字符串: {isinstance(first_pkg_code, str)}")
if isinstance(first_pkg_code, str):
    print(f"是否包含'0x': {'0x' in first_pkg_code.lower()}")
    try:
        print(f"尝试转为十进制: {int(first_pkg_code, 16) if '0x' in first_pkg_code.lower() else int(first_pkg_code)}")
    except:
        pass
