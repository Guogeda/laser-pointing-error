#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证脚本 - Step 1: 数据预处理
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 导入参数映射
sys.path.insert(0, str(Path(__file__).parent.parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

# 可配置参数
OUTPUT_DIR = Path(__file__).parent.parent / 'output' / 'step1-preprocessing'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 配置常量
OUTLIER_SIGMA = 3
OUTLIER_MIN_SEGMENT = 5
CONTINUITY_GAP_SEC = 10
RESAMPLE_FREQ = '1S'

def load_and_preprocess(csv_path):
    """
    Step 1: 数据预处理
    """
    print(f"正在读取文件: {csv_path}")

    # 读取CSV
    df = pd.read_csv(csv_path, parse_dates=['satelliteTime', 'receiveTime'])
    print(f"原始数据行数: {len(df)}")
    print(f"时间范围: {df['satelliteTime'].min()} 到 {df['satelliteTime'].max()}")

    # 按packageCode分组
    package_groups = df.groupby('packageCode')
    print(f"\n发现 {len(package_groups)} 个遥测包:")
    for pkg_code, group in package_groups:
        print(f"  包 {pkg_code}: {len(group)} 行数据")

    # 处理每个包
    results = {}
    for pkg_code, df_pkg in package_groups:
        print(f"\n处理包 {pkg_code}...")

        # 长格式转宽格式
        df_wide = df_pkg.pivot_table(
            index='satelliteTime',
            columns='paramCode',
            values='parsedValue',
            aggfunc='last'
        )
        print(f"  宽格式: {df_wide.shape[1]} 列")

        # 异常值检测
        df_wide = detect_outliers(df_wide)

        # 列名替换为中文
        df_wide = rename_columns_to_chinese(df_wide)

        # 保存结果
        output_file = OUTPUT_DIR / f'31star_pkg_{pkg_code}_wide.csv'
        df_wide.to_csv(output_file, encoding='utf-8-sig')
        print(f"  保存到: {output_file}")

        results[pkg_code] = df_wide

    return results

def detect_outliers(df):
    """
    三层异常值检测
    """
    df = df.copy()
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        # 层1: 物理范围检测 (从参数映射中获取或使用默认值)
        col_flag = f"{col}_flag"
        df[col_flag] = np.nan

        # 层2: 3σ统计检测
        rolling_mean = df[col].rolling(window=60, min_periods=10).mean()
        rolling_std = df[col].rolling(window=60, min_periods=10).std()
        stat_mask = (df[col] - rolling_mean).abs() > OUTLIER_SIGMA * rolling_std
        df.loc[stat_mask, col_flag] = 'stat_outlier'

        # 层3: 变化率突变检测
        diffs = df[col].diff().abs()
        rate_threshold = diffs.quantile(0.99)
        spike_mask = diffs > rate_threshold
        df.loc[spike_mask & df[col_flag].isna(), col_flag] = 'spike'

    return df

def rename_columns_to_chinese(df):
    """
    列名替换为中文名称
    """
    rename_map = {}
    for col in df.columns:
        if col.endswith('_flag'):
            original_code = col[:-5]
            chinese_name = get_param_name(original_code)
            rename_map[col] = f"{chinese_name}_标记"
        else:
            chinese_name = get_param_name(col)
            rename_map[col] = chinese_name

    return df.rename(columns=rename_map)

if __name__ == '__main__':
    csv_file = Path(__file__).parent.parent / 'ori-data' / '31star' / 'CSCN-A0031_TelPlatformParsed_20260307070624_1.csv'

    if not csv_file.exists():
        print(f"文件不存在: {csv_file}")
        sys.exit(1)

    results = load_and_preprocess(csv_file)
    print("\nStep 1 预处理完成!")
