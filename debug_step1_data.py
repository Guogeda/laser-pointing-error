#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试 step1_data 的键格式
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

csv_path = Path(__file__).parent / 'ori-data' / '31star' / 'CSCN-A0031_TelPlatformParsed_20260307070624_1.csv'

df = pd.read_csv(csv_path, parse_dates=['satelliteTime'])

package_groups = df.groupby('packageCode')
print("="*70)
print("调试 step1_data 的键格式")
print("="*70)

print(f"\n分组键类型:")
for pkg_code, df_pkg in package_groups:
    print(f"  键值: {pkg_code}, 类型: {type(pkg_code)}")

print(f"\n分组键列表:")
print(list(package_groups.groups.keys()))
