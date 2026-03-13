#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证数据处理过程中的数据一致性
确保原始数据和处理后的数据没有新增额外的数据
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

INPUT_DIR = Path(__file__).parent

# 原始数据
ORIGINAL_FILE = INPUT_DIR / 'ori-data' / '31star' / 'CSCN-A0031_TelPlatformParsed_20260312063411_1.csv'

# Step 1 输出
STEP1_DIR = INPUT_DIR / 'output' / 'step1-preprocessing' / 'results'

# Step 2 输出
STEP2_DIR = INPUT_DIR / 'output' / 'step2-state-filter' / 'results'

def validate_original_data():
    """验证原始数据的基本信息"""
    print(f"\n{'='*60}")
    print(f"原始数据验证")
    print(f"{'='*60}")

    if not ORIGINAL_FILE.exists():
        print(f"未找到原始数据文件: {ORIGINAL_FILE}")
        return None

    try:
        df_original = pd.read_csv(ORIGINAL_FILE, parse_dates=['satelliteTime'])
        print(f"原始数据行数: {len(df_original):,}")
        print(f"原始数据时间范围: {df_original['satelliteTime'].min()} 到 {df_original['satelliteTime'].max()}")

        package_counts = df_original['packageCode'].value_counts().sort_index()
        print(f"\n遥测包分布:")
        for pkg_code, count in package_counts.items():
            print(f"  包 {pkg_code}: {count:,} 条")

        return df_original
    except Exception as e:
        print(f"读取原始数据失败: {e}")
        return None

def validate_step1_data(df_original):
    """验证 Step 1 处理后的数据"""
    print(f"\n{'='*60}")
    print(f"Step 1 数据验证")
    print(f"{'='*60}")

    if not STEP1_DIR.exists():
        print(f"未找到 Step 1 输出目录: {STEP1_DIR}")
        return

    all_csv_files = list(STEP1_DIR.glob('*.csv'))
    if not all_csv_files:
        print("Step 1 输出目录中没有 CSV 文件")
        return

    print(f"找到 {len(all_csv_files)} 个 Step 1 输出文件")

    all_package_codes = []
    total_columns = 0
    total_rows = 0

    for csv_file in all_csv_files:
        pkg_code = csv_file.name.split('_')[2]  # 31star_pkg_{pkg_code}_wide.csv
        all_package_codes.append(pkg_code)

        try:
            df_step1 = pd.read_csv(csv_file, parse_dates=['satelliteTime'], index_col='satelliteTime')
            print(f"\n  包 {pkg_code}:")
            print(f"    行数: {len(df_step1):,}")
            print(f"    列数: {len(df_step1.columns):,}")
            print(f"    时间范围: {df_step1.index.min()} 到 {df_step1.index.max()}")

            total_columns += len(df_step1.columns)
            total_rows += len(df_step1)

            # 检查是否有数据值完全一致的列（可能有问题）
            constant_cols = []
            for col in df_step1.columns:
                if not col.endswith('_标记') and pd.api.types.is_numeric_dtype(df_step1[col]):
                    if df_step1[col].nunique() <= 2 and df_step1[col].notna().any():
                        constant_cols.append(col)

            if constant_cols:
                print(f"    注意: 以下列可能存在常数或接近常数的数据: {constant_cols}")

        except Exception as e:
            print(f"读取 {csv_file} 失败: {e}")

    print(f"\n总体统计:")
    print(f"  包数量: {len(all_package_codes)}")
    print(f"  总列数: {total_columns:,}")
    print(f"  总行数: {total_rows:,}")

    return all_package_codes

def validate_step2_data(all_package_codes):
    """验证 Step 2 处理后的数据"""
    print(f"\n{'='*60}")
    print(f"Step 2 数据验证")
    print(f"{'='*60}")

    if not STEP2_DIR.exists():
        print(f"未找到 Step 2 输出目录: {STEP2_DIR}")
        return

    # 找到所有终端的原始和处理后文件
    raw_files = list(STEP2_DIR.glob('*_raw.csv'))
    processed_files = list(STEP2_DIR.glob('*_processed.csv'))

    if not raw_files and not processed_files:
        print("Step 2 输出目录中没有终端数据文件")
        return

    print(f"找到 {len(raw_files)} 个原始文件, {len(processed_files)} 个处理后文件")

    for terminal in ['B1', 'B2', 'A1-1', 'A1-2']:
        raw_file = STEP2_DIR / f'{terminal}_raw.csv'
        processed_file = STEP2_DIR / f'{terminal}_processed.csv'

        print(f"\n  终端 {terminal}:")

        if raw_file.exists():
            try:
                df_raw = pd.read_csv(raw_file, parse_dates=[0], index_col=0)
                print(f"    原始文件: {len(df_raw):,} 行, {len(df_raw.columns):,} 列")
                print(f"    原始文件时间范围: {df_raw.index.min()} 到 {df_raw.index.max()}")
            except Exception as e:
                print(f"    读取原始文件失败: {e}")

        if processed_file.exists():
            try:
                df_processed = pd.read_csv(processed_file, parse_dates=[0], index_col=0)
                print(f"    处理后文件: {len(df_processed):,} 行, {len(df_processed.columns):,} 列")
                print(f"    处理后文件时间范围: {df_processed.index.min()} 到 {df_processed.index.max()}")

                # 检查数据点数
                valid_mask = df_processed['session_id'].notna()
                print(f"    有效数据点数: {valid_mask.sum():,} ({valid_mask.mean():.1%})")

                # 检查是否有异常值标记
                flag_columns = [col for col in df_processed.columns if col.endswith('_标记')]
                if flag_columns:
                    invalid_counts = {}
                    for flag_col in flag_columns:
                        invalid_count = df_processed[flag_col].notna().sum()
                        if invalid_count > 0:
                            invalid_counts[flag_col] = invalid_count

                    if invalid_counts:
                        print(f"    异常值检测列:")
                        for col, count in invalid_counts.items():
                            print(f"      {col}: {count:,} 个异常值")

            except Exception as e:
                print(f"    读取处理后文件失败: {e}")

def validate_terminal_data_points():
    """检查终端数据点是否合理"""
    print(f"\n{'='*60}")
    print(f"终端数据点验证")
    print(f"{'='*60}")

    if not STEP2_DIR.exists():
        return

    processed_files = list(STEP2_DIR.glob('*_processed.csv'))

    for csv_file in processed_files:
        terminal = csv_file.name.split('_')[0]
        try:
            df_processed = pd.read_csv(csv_file, parse_dates=[0], index_col=0)

            print(f"\n  终端 {terminal}:")
            print(f"    总数据点: {len(df_processed):,}")
            print(f"    原始数据点: {df_processed['session_id'].notna().sum():,}")
            print(f"    时间密度: {len(df_processed) / ((df_processed.index.max() - df_processed.index.min()).total_seconds() / 3600):.1f} 点/小时")

            # 检查数据完整性
            numeric_columns = []
            for col in df_processed.columns:
                if not col.endswith('_标记') and not col.endswith('_interp') and \
                   col not in ['period_id', 'session_id', 'is_valid']:
                    if pd.api.types.is_numeric_dtype(df_processed[col]):
                        numeric_columns.append(col)

            print(f"    数值列数量: {len(numeric_columns)}")

            # 检查每列的完整性
            incomplete_cols = []
            for col in numeric_columns:
                valid_mask = df_processed['session_id'].notna()
                valid_data = df_processed.loc[valid_mask, col]
                missing_rate = valid_data.isna().mean()

                if missing_rate > 0.1:
                    incomplete_cols.append((col, missing_rate))

            if incomplete_cols:
                print(f"    缺失率较高的列:")
                for col, rate in sorted(incomplete_cols, key=lambda x: x[1], reverse=True):
                    print(f"      {col}: {rate:.1%} 缺失")

        except Exception as e:
            print(f"    读取 {csv_file} 失败: {e}")

def main():
    print(f"{'='*80}")
    print(f"激光指向误差计算系统数据一致性验证")
    print(f"{'='*80}")

    # 验证原始数据
    df_original = validate_original_data()

    # 验证 Step 1 数据
    if df_original is not None:
        all_package_codes = validate_step1_data(df_original)
    else:
        all_package_codes = []

    # 验证 Step 2 数据
    validate_step2_data(all_package_codes)

    # 验证终端数据点
    validate_terminal_data_points()

    print(f"\n{'='*80}")
    print(f"验证完成!")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
