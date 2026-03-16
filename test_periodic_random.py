#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试周期性和随机性成分分离功能
"""

import sys
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from temperature_analysis import TemperatureAnalyzer
import pandas as pd
import numpy as np

print("=" * 60)
print("测试周期性和随机性成分分离功能")
print("=" * 60)

# 创建分析器
analyzer = TemperatureAnalyzer('output')

# 加载一个终端的数据
star_name = '31star'
terminal_name = 'A1-1'

print(f"\n加载数据: {star_name} - {terminal_name}")
data = analyzer.load_analysis_data(star_name, terminal_name)

if data is not None:
    print(f"数据形状: {data.shape}")
    print(f"列名: {list(data.columns)}")

    # 测试太阳辐照度的分离
    if 'solar_irradiance' in data.columns:
        print(f"\n测试太阳辐照度分离...")
        signal = data['solar_irradiance'].dropna()
        periodic, random = analyzer.separate_periodic_random(signal)

        print(f"  原信号长度: {len(signal)}")
        print(f"  周期性成分: {periodic.notna().sum()} 有效点")
        print(f"  随机性成分: {random.notna().sum()} 有效点")
        print(f"  原信号均值: {signal.mean():.6f}")
        print(f"  周期性均值: {periodic.mean():.6f}")
        print(f"  随机性均值: {random.mean():.6f}")

    # 测试综合误差的分离
    if '综合误差' in data.columns:
        print(f"\n测试综合误差分离...")
        signal = data['综合误差'].dropna()
        periodic, random = analyzer.separate_periodic_random(signal)

        print(f"  原信号长度: {len(signal)}")
        print(f"  周期性成分: {periodic.notna().sum()} 有效点")
        print(f"  随机性成分: {random.notna().sum()} 有效点")
        print(f"  原信号均值: {signal.mean():.6f}")
        print(f"  周期性均值: {periodic.mean():.6f}")
        print(f"  随机性均值: {random.mean():.6f}")

    print(f"\n测试成功！")
else:
    print("未能加载数据")

print("\n" + "=" * 60)
