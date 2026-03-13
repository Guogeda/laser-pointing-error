#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查状态参数值分布"""
import pandas as pd
from pathlib import Path

base_dir = Path(__file__).parent.parent

# 检查 A1-1 的状态参数
print("="*60)
print("A1-1 状态参数分析")
print("="*60)
a11_wide = pd.read_csv(base_dir / 'output/step1-preprocessing/results/31star_pkg_134_wide.csv',
                        parse_dates=[0], index_col=0)
state_col_a11 = [col for col in a11_wide.columns if '激光终端状态' in col][0]
print(f"\nA1-1 状态参数列名: {state_col_a11}")
print(f"\nA1-1 状态参数唯一值:")
print(a11_wide[state_col_a11].value_counts(dropna=False))
print(f"\nA1-1 状态参数时间分布（前 20 个点）:")
print(a11_wide[state_col_a11].head(20))

# 检查 B1 的状态参数
print("\n" + "="*60)
print("B1 状态参数分析")
print("="*60)
b1_wide = pd.read_csv(base_dir / 'output/step1-preprocessing/results/31star_pkg_136_wide.csv',
                       parse_dates=[0], index_col=0)
state_col_b1 = [col for col in b1_wide.columns if '捕跟工作状态' in col][0]
print(f"\nB1 状态参数列名: {state_col_b1}")
print(f"\nB1 状态参数唯一值:")
print(b1_wide[state_col_b1].value_counts(dropna=False))
print(f"\nB1 状态参数时间分布（前 20 个点）:")
print(b1_wide[state_col_b1].head(20))