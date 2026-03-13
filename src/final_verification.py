#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终验证脚本 - 使用已有数据完成完整流程
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

sys.path.insert(0, str(Path(__file__).parent.parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

def main():
    base_dir = Path(__file__).parent.parent / 'output'

    print("="*70)
    print("激光指向误差分析系统 - 验证报告")
    print("="*70)

    # Step 1: 检查已有数据
    step1_dir = base_dir / 'step1-preprocessing' / 'results'
    if not step1_dir.exists():
        print("Step 1 数据不存在，请先运行预处理")
        return

    csv_files = list(step1_dir.glob('*.csv'))
    print(f"\nStep 1 - 数据预处理:")
    print(f"  已生成 {len(csv_files)} 个宽格式文件")
    for f in sorted(csv_files):
        df = pd.read_csv(f, nrows=1)
        print(f"    - {f.name}: {len(df.columns)-1} 个参数")

    # Step 2 & 3: 处理每个终端
    print(f"\nStep 2 & 3 - 状态筛选与误差计算:")

    terminals = [
        ('B1', '136', 'B1慢-捕跟工作状态', {
            'A_t': 'B1慢-捕跟伺服理论方位角',
            'A_r': 'B1慢-捕跟伺服实时方位轴角',
            'E_t': 'B1慢-捕跟伺服理论俯仰角',
            'E_r': 'B1慢-捕跟伺服实时俯仰轴角',
        }),
        ('B2', '138', 'B2慢-捕跟工作状态', {
            'A_t': 'B2慢-捕跟伺服理论方位角',
            'A_r': 'B2慢-捕跟伺服实时方位轴角',
            'E_t': 'B2慢-捕跟伺服理论俯仰角',
            'E_r': 'B2慢-捕跟伺服实时俯仰轴角',
        }),
        ('A1-1', '134', 'A3慢-1-激光终端状态', {
            'A_t': 'A3慢-1-方位电机目标位置',
            'A_r': 'A3慢-1-方位电机当前位置',
            'E_t': 'A3慢-1-俯仰电机目标位置',
            'E_r': 'A3慢-1-俯仰电机当前位置',
        }),
        ('A1-2', '134', 'A3慢-2-激光终端状态', {
            'A_t': 'A3慢-2-方位电机目标位置',
            'A_r': 'A3慢-2-方位电机当前位置',
            'E_t': 'A3慢-2-俯仰电机目标位置',
            'E_r': 'A3慢-2-俯仰电机当前位置',
        }),
    ]

    all_results = {}

    for terminal_name, pkg_code, state_col, error_cols in terminals:
        # 从 Step 2 处理后文件读取完整数据（包含完整 1Hz 时间轴和插值好的参数）
        processed_file = base_dir / 'step2-state-filter' / 'results' / f'{terminal_name}_processed.csv'
        if not processed_file.exists():
            print(f"\n  {terminal_name}: 未找到处理后文件，跳过")
            continue

        df = pd.read_csv(processed_file, parse_dates=[0], index_col=0)

        # 计算误差（使用 Step 2 中已经插值好的参数值）
        A_t = df[error_cols['A_t']]
        A_r = df[error_cols['A_r']]
        E_t = df[error_cols['E_t']]
        E_r = df[error_cols['E_r']]

        # 在完整时间轴上计算误差（只要参数有值就计算，使用 Step 2 插值好的数据）
        delta_A = (A_t - A_r + 180) % 360 - 180  # 方位角环绕处理
        delta_E = E_t - E_r
        theta_error = np.sqrt((delta_A * np.cos(np.radians(E_r)))**2 + delta_E**2)

        df['delta_A'] = delta_A
        df['delta_E'] = delta_E
        df['theta_error'] = theta_error

        # 保存误差数据（包含完整 1Hz 时间轴，以及 session_id 列）
        step3_dir = base_dir / 'step3-error-calc' / 'results'
        step3_dir.mkdir(parents=True, exist_ok=True)
        out_file = step3_dir / f'error_{terminal_name}.csv'
        # 确保 session_id 列存在
        if 'session_id' in df.columns:
            df[['delta_A', 'delta_E', 'theta_error', 'session_id']].to_csv(out_file, encoding='utf-8-sig')
        else:
            df[['delta_A', 'delta_E', 'theta_error']].to_csv(out_file, encoding='utf-8-sig')

        # 统计指标（只使用有效 session 内的数据计算）
        valid_mask = df['session_id'].notna() if 'session_id' in df.columns else df.notna().all(axis=1)
        stats = {
            '数据点数': valid_mask.sum(),
            '方位误差_均值': delta_A[valid_mask].mean() if valid_mask.any() else np.nan,
            '方位误差_std': delta_A[valid_mask].std() if valid_mask.any() else np.nan,
            '俯仰误差_均值': delta_E[valid_mask].mean() if valid_mask.any() else np.nan,
            '俯仰误差_std': delta_E[valid_mask].std() if valid_mask.any() else np.nan,
            '综合误差_均值': theta_error[valid_mask].mean() if valid_mask.any() else np.nan,
            '综合误差_P95': theta_error[valid_mask].quantile(0.95) if valid_mask.any() else np.nan,
        }

        all_results[terminal_name] = {'data': df, 'stats': stats}

        print(f"\n  {terminal_name}:")
        print(f"    有效数据: {stats['数据点数']} 点")
        print(f"    平均综合误差: {stats['综合误差_均值']:.4f}°")
        print(f"    结果保存至: {out_file.name}")

    # 生成统计报告
    if all_results:
        report_file = base_dir / 'step3-error-calc' / 'error_statistics.md'

        # 使用与 verify_complete.py 相同的报告格式
        report = []
        report.append("# 指向误差统计报告\n")
        report.append("""| 终端   |   数据点数 |     方位误差_均值 |   方位误差_标准差 |   方位误差_RMS |   方位误差_P95 |   方位误差_P99 |     俯仰误差_均值 |   俯仰误差_标准差 |   俯仰误差_RMS |   俯仰误差_P95 |   俯仰误差_P99 |    综合误差_均值 |   综合误差_RMS |   综合误差_P95 |   综合误差_P99 |
|:-----|-------:|------------:|-----------:|-----------:|-----------:|-----------:|------------:|-----------:|-----------:|-----------:|-----------:|-----------:|-----------:|-----------:|-----------:|""")

        for term, result in sorted(all_results.items()):
            stats = result['stats']
            delta_A = result['data']['delta_A'][result['data']['session_id'].notna() if 'session_id' in result['data'].columns else result['data'].notna().all(axis=1)]
            delta_E = result['data']['delta_E'][result['data']['session_id'].notna() if 'session_id' in result['data'].columns else result['data'].notna().all(axis=1)]
            theta_error = result['data']['theta_error'][result['data']['session_id'].notna() if 'session_id' in result['data'].columns else result['data'].notna().all(axis=1)]

            # 计算完整统计指标
            row = [
                term,
                stats['数据点数'],
                delta_A.mean(),
                delta_A.std(),
                np.sqrt((delta_A ** 2).mean()),
                delta_A.quantile(0.95) if len(delta_A) > 0 else np.nan,
                delta_A.quantile(0.99) if len(delta_A) > 0 else np.nan,
                delta_E.mean(),
                delta_E.std(),
                np.sqrt((delta_E ** 2).mean()),
                delta_E.quantile(0.95) if len(delta_E) > 0 else np.nan,
                delta_E.quantile(0.99) if len(delta_E) > 0 else np.nan,
                theta_error.mean(),
                np.sqrt((theta_error ** 2).mean()),
                theta_error.quantile(0.95) if len(theta_error) > 0 else np.nan,
                theta_error.quantile(0.99) if len(theta_error) > 0 else np.nan,
            ]

            # 格式化输出
            report.append(f"| {row[0]} | {row[1]:5d} | {row[2]:10.6f} | {row[3]:9.6f} | {row[4]:9.6f} | {row[5]:9.6f} | {row[6]:9.6f} | {row[7]:10.6f} | {row[8]:9.6f} | {row[9]:9.6f} | {row[10]:9.6f} | {row[11]:9.6f} | {row[12]:10.6f} | {row[13]:9.6f} | {row[14]:9.6f} | {row[15]:9.6f} |")

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report) + '\n')

        print(f"\n统计报告已保存至: {report_file}")

    print("\n" + "="*70)
    print("验证完成！")
    print("="*70)

if __name__ == '__main__':
    main()
