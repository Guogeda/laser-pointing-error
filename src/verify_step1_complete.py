#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证脚本 - Step 1: 数据预处理 (完整版本)
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import shutil
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，避免显示窗口
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 导入参数映射
sys.path.insert(0, str(Path(__file__).parent.parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

# 可配置参数
OUTPUT_DIR = Path(__file__).parent.parent / 'output' / 'step1-preprocessing'

# 清理并重新创建目录
if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORTS_DIR = OUTPUT_DIR / 'reports'
REPORTS_DIR.mkdir(exist_ok=True)
PLOTS_DIR = OUTPUT_DIR / 'plots'
PLOTS_DIR.mkdir(exist_ok=True)
RESULTS_DIR = OUTPUT_DIR / 'results'
RESULTS_DIR.mkdir(exist_ok=True)

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
    package_stats = []
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

        # 保存结果到 results 目录
        output_file = RESULTS_DIR / f'31star_pkg_{pkg_code}_wide.csv'
        df_wide.to_csv(output_file, encoding='utf-8-sig')
        print(f"  保存到: {output_file}")

        # 计算包的统计信息
        stats = calculate_package_statistics(df_wide, pkg_code)
        package_stats.append(stats)

        # 生成时间线图表
        plot_timeline(df_wide, pkg_code)

        results[pkg_code] = df_wide

    # 生成预处理报告
    generate_preprocessing_report(package_stats)

    return results

def calculate_package_statistics(df, pkg_code):
    """计算包的统计信息"""
    total_rows = len(df)
    valid_rows = len(df.dropna(subset=[col for col in df.columns if not col.endswith('_标记')]))
    valid_rate = valid_rows / total_rows if total_rows > 0 else 0

    # 计算异常点数量
    outlier_total = 0
    for col in df.columns:
        if col.endswith('_标记'):
            outlier_total += df[col].notna().sum()

    return {
        'package_code': pkg_code,
        'total_rows': total_rows,
        'valid_rows': valid_rows,
        'valid_rate': valid_rate,
        'time_range': (df.index.min(), df.index.max()) if len(df) > 0 else (None, None),
        'outlier_total': outlier_total,
        'columns': [col for col in df.columns if not col.endswith('_标记')],
    }

def generate_preprocessing_report(package_stats):
    """生成预处理报告"""
    report_file = REPORTS_DIR / 'preprocessing_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 数据预处理报告\n\n")

        for stats in package_stats:
            f.write(f"## 包 {stats['package_code']}\n")
            f.write(f"- 行数: {stats['total_rows']}\n")
            f.write(f"- 有效行数: {stats['valid_rows']}\n")
            f.write(f"- 有效率: {stats['valid_rate']:.2%}\n")
            if stats['time_range'][0] is not None:
                f.write(f"- 时间范围: {stats['time_range'][0]} 到 {stats['time_range'][1]}\n")
            f.write(f"- 参数数量: {len(stats['columns'])}\n")
            f.write(f"- 异常值总数: {stats['outlier_total']}\n")
            f.write("\n")

    print(f"  报告保存到: {report_file}")

def plot_timeline(df, pkg_code):
    """绘制时间线图"""
    # 选择第一个参数作为代表性参数
    param_col = None
    for col in df.columns:
        if not col.endswith('_标记'):
            param_col = col
            break
    if param_col is None:
        return

    fig, ax = plt.subplots(figsize=(16, 8))
    ax.plot(df.index, df[param_col], label=param_col, color='blue', linewidth=0.5)

    # 绘制有效/无效区间
    flag_col = f"{param_col}_标记"
    if flag_col in df.columns:
        invalid_mask = df[flag_col].notna()
        # 找到连续的无效区间
        if len(invalid_mask) > 0:
            # 标记区间
            in_invalid = False
            start = None
            for time, is_invalid in invalid_mask.items():
                if is_invalid and not in_invalid:
                    start = time
                    in_invalid = True
                elif not is_invalid and in_invalid:
                    ax.axvspan(start, time, color='red', alpha=0.2)
                    in_invalid = False
            if in_invalid and start is not None:
                ax.axvspan(start, df.index[-1], color='red', alpha=0.2)

    ax.set_title(f'包 {pkg_code} - {param_col} 时间线')
    ax.set_xlabel('时间')
    ax.set_ylabel('值')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)

    # 保存图表
    plot_file = PLOTS_DIR / f'31star_pkg_{pkg_code}_timeline.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"  图表保存到: {plot_file}")

def detect_outliers(df):
    """
    三层异常值检测
    """
    df = df.copy()
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        col_flag = f"{col}_标记"
        df[col_flag] = np.nan

        # 层2: 3σ统计检测
        rolling_mean = df[col].rolling(window=60, min_periods=10).mean()
        rolling_std = df[col].rolling(window=60, min_periods=10).std()
        stat_mask = (df[col] - rolling_mean).abs() > OUTLIER_SIGMA * rolling_std
        df.loc[stat_mask, col_flag] = 'stat_outlier'

        # 层3: 变化率突变检测
        diffs = df[col].diff().abs()
        if len(diffs.dropna()) > 0:
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
        if col.endswith('_标记'):
            original_code = col[:-3]  # 去掉 '_标记'
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
