#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证数据点数减少的原因"""
import pandas as pd
from pathlib import Path

base_dir = Path(__file__).parent.parent

print("="*60)
print("A1-1 数据点数详细分析")
print("="*60)

# 读取 Step 1 宽格式数据
a11_wide = pd.read_csv(base_dir / 'output/step1-preprocessing/results/31star_pkg_134_wide.csv',
                        parse_dates=[0], index_col=0)
state_col_a11 = [col for col in a11_wide.columns if '激光终端状态' in col][0]

print(f"\nStep 1 数据:")
print(f"  总行数: {len(a11_wide)}")
print(f"  状态为6的行数: {(a11_wide[state_col_a11] == 6).sum()}")
print(f"  时间范围: {a11_wide.index.min()} 到 {a11_wide.index.max()}")
print(f"  总时长: {(a11_wide.index.max() - a11_wide.index.min()).total_seconds() / 3600:.2f} 小时")

# 读取 Step 2 原始数据（时间对齐后）
a11_raw = pd.read_csv(base_dir / 'output/step2-state-filter/results/A1-1_raw.csv',
                       parse_dates=[0], index_col=0)
print(f"\nStep 2 时间对齐后数据:")
print(f"  总行数: {len(a11_raw)}")
print(f"  时间范围: {a11_raw.index.min()} 到 {a11_raw.index.max()}")
print(f"  总时长: {(a11_raw.index.max() - a11_raw.index.min()).total_seconds() / 3600:.2f} 小时")

# 读取 Step 2 处理后数据
a11_processed = pd.read_csv(base_dir / 'output/step2-state-filter/results/A1-1_processed.csv',
                             parse_dates=[0], index_col=0)
print(f"\nStep 2 处理后数据:")
print(f"  总行数: {len(a11_processed)}")
print(f"  is_valid为True的行数: {a11_processed['is_valid'].sum()}")
print(f"  session_id不为空的行数: {a11_processed['session_id'].notna().sum()}")
print(f"  session数量: {a11_processed['session_id'].nunique()}")

# 检查时间对齐过程中的数据丢失
print(f"\n时间对齐过程分析:")
print(f"  Step 1 状态为6的时间点数量: {(a11_wide[state_col_a11] == 6).sum()}")
print(f"  Step 2 时间对齐后 is_valid 为 True 的数量: {a11_processed['is_valid'].sum()}")

# 查看前几个 session_id 不为空的时间点
print(f"\n前 20 个有效 session 时间点:")
valid_points = a11_processed[a11_processed['session_id'].notna()].head(20)
print(valid_points[['A3慢-1-激光终端状态', 'is_valid', 'session_id']])

# 检查数据分布
print(f"\n数据分布:")
print(f"  每小时平均点数 (Step 1): {len(a11_wide) / ((a11_wide.index.max() - a11_wide.index.min()).total_seconds() / 3600):.2f}")
print(f"  每小时平均点数 (Step 2 有效): {a11_processed['session_id'].notna().sum() / ((a11_processed.index.max() - a11_processed.index.min()).total_seconds() / 3600):.2f}")

# 检查 B1 作为对比
print("\n" + "="*60)
print("B1 数据点数详细分析（对比）")
print("="*60)

b1_wide = pd.read_csv(base_dir / 'output/step1-preprocessing/results/31star_pkg_136_wide.csv',
                       parse_dates=[0], index_col=0)
state_col_b1 = [col for col in b1_wide.columns if '捕跟工作状态' in col][0]

print(f"\nStep 1 数据:")
print(f"  总行数: {len(b1_wide)}")
print(f"  状态为6的行数: {(b1_wide[state_col_b1] == 6).sum()}")
print(f"  时间范围: {b1_wide.index.min()} 到 {b1_wide.index.max()}")
print(f"  总时长: {(b1_wide.index.max() - b1_wide.index.min()).total_seconds() / 3600:.2f} 小时")

b1_processed = pd.read_csv(base_dir / 'output/step2-state-filter/results/B1_processed.csv',
                            parse_dates=[0], index_col=0)
print(f"\nStep 2 处理后数据:")
print(f"  总行数: {len(b1_processed)}")
print(f"  is_valid为True的行数: {b1_processed['is_valid'].sum()}")
print(f"  session_id不为空的行数: {b1_processed['session_id'].notna().sum()}")
print(f"  session数量: {b1_processed['session_id'].nunique()}")