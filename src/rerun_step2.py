#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
只重新运行 Step 2 - 用于更新甘特图
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

sys.path.insert(0, str(Path(__file__).parent.parent))
from param_mapping_jg01 import PARAM_MAPPING, get_param_name

OUTPUT_DIR = Path(__file__).parent.parent / 'output'
STEP1_OUTPUT = OUTPUT_DIR / 'step1-preprocessing' / 'results'
STEP2_OUTPUT = OUTPUT_DIR / 'step2-state-filter'

for subdir in ['reports', 'plots', 'results']:
    (STEP2_OUTPUT / subdir).mkdir(parents=True, exist_ok=True)

# 配置常量
VALID_STATE_VALUE = '6'
CONTINUITY_GAP_SEC = 10
SESSION_TRANSIENT_DROP = 10
RESAMPLE_FREQ = '1S'

# 终端配置
TERMINALS = {
    'B1': {
        'package': '136',
        'state_param': 'TMJB3031',
        'state_name': 'B1慢-捕跟工作状态',
        'error_params': {
            'A_t': 'TMJB3212', 'A_r': 'TMJB3079',
            'E_t': 'TMJB3213', 'E_r': 'TMJB3080',
        }
    },
    'B2': {
        'package': '138',
        'state_param': 'TMJB4031',
        'state_name': 'B2慢-捕跟工作状态',
        'error_params': {
            'A_t': 'TMJB4212', 'A_r': 'TMJB4079',
            'E_t': 'TMJB4213', 'E_r': 'TMJB4080',
        }
    },
    'A1-1': {
        'package': '134',
        'state_param': 'TMJA3115',
        'state_name': 'A3慢-1-激光终端状态',
        'error_params': {
            'A_t': 'TMJA3148', 'A_r': 'TMJA3147',
            'E_t': 'TMJA3150', 'E_r': 'TMJA3149',
        }
    },
    'A1-2': {
        'package': '134',
        'state_param': 'TMJA3239',
        'state_name': 'A3慢-2-激光终端状态',
        'error_params': {
            'A_t': 'TMJA3272', 'A_r': 'TMJA3271',
            'E_t': 'TMJA3274', 'E_r': 'TMJA3273',
        }
    },
}

def load_step1_data():
    """加载 Step 1 数据"""
    step1_data = {}
    for file in STEP1_OUTPUT.glob('*_wide.csv'):
        pkg_code = file.stem.split('_')[-2]
        df = pd.read_csv(file, parse_dates=['satelliteTime'], index_col='satelliteTime')
        step1_data[pkg_code] = df
    return step1_data

def generate_valid_distribution_plots(step1_data, terminal_data):
    """生成 Step 2 有效数据分布图表（甘特图效果）"""
    print("\n生成有效数据分布甘特图...")

    for terminal, config in TERMINALS.items():
        pkg_code = config['package']
        state_name = config['state_name']

        plot_file = STEP2_OUTPUT / 'plots' / f'{terminal}_valid_distribution.png'

        # 加载原始数据和处理后的数据
        step1_file = STEP1_OUTPUT / f'31star_pkg_{pkg_code}_wide.csv'
        step2_raw_file = STEP2_OUTPUT / 'results' / f'{terminal}_raw.csv'
        step2_processed_file = STEP2_OUTPUT / 'results' / f'{terminal}_processed.csv'

        if not step1_file.exists() or not step2_processed_file.exists():
            continue

        raw_df = pd.read_csv(step1_file, parse_dates=['satelliteTime'], index_col='satelliteTime')
        processed_df = pd.read_csv(step2_processed_file, parse_dates=[0], index_col=0)

        # 构建完整的时间轴
        if len(raw_df) > 0 and len(processed_df) > 0:
            t_min = min(raw_df.index.min(), processed_df.index.min())
            t_max = max(raw_df.index.max(), processed_df.index.max())
        elif len(raw_df) > 0:
            t_min, t_max = raw_df.index.min(), raw_df.index.max()
        else:
            t_min, t_max = processed_df.index.min(), processed_df.index.max()

        # 创建统一1Hz时间轴（整秒）
        full_index = pd.date_range(start=t_min.floor('S'), end=t_max.ceil('S'), freq=RESAMPLE_FREQ)

        # 标记每个时间点的状态
        # 0: 无效数据（白色）
        # 1: 有效数据（原始值，浅色）
        # 2: 插值数据（深色）
        status = pd.Series([0]*len(full_index), index=full_index)

        # 第一步：标记原始数据中存在的点（未筛选前）
        if len(raw_df) > 0:
            # 先将所有原始数据时间点标记为有效（临时）
            for t in raw_df.index:
                # 找到最近的统一时间轴点（500ms容差）
                dt = full_index - t
                abs_dt = np.abs(dt.total_seconds())
                min_dt_idx = abs_dt.argmin()
                if abs_dt[min_dt_idx] <= 0.5:  # 500ms
                    status.iloc[min_dt_idx] = 1  # 临时标记为有原始数据

        # 第二步：标记处理后的有效数据
        if len(processed_df) > 0:
            # 找到一个有_interp标记的列（数值列）
            interp_col = None
            for col in processed_df.columns:
                if col.endswith('_interp'):
                    interp_col = col
                    break

            for t in processed_df.index:
                dt = full_index - t
                abs_dt = np.abs(dt.total_seconds())
                min_dt_idx = abs_dt.argmin()
                if abs_dt[min_dt_idx] <= 0.5:  # 500ms
                    # 检查是否在有效session内
                    session_id = processed_df.loc[t, 'session_id'] if 'session_id' in processed_df.columns else None
                    if pd.notna(session_id):
                        if interp_col and interp_col in processed_df.columns:
                            # 检查是否是插值数据
                            if processed_df.loc[t, interp_col]:
                                status.iloc[min_dt_idx] = 2  # 插值数据（红色）
                            else:
                                status.iloc[min_dt_idx] = 1  # 原始有效数据（浅蓝）
                        else:
                            status.iloc[min_dt_idx] = 1  # 默认标记为有效数据

        # 找到连续相同状态的区间
        intervals = []
        if len(status) > 0:
            current_status = status.iloc[0]
            start_time = status.index[0]

            for i in range(1, len(status)):
                if status.iloc[i] != current_status:
                    intervals.append((start_time, status.index[i-1], current_status))
                    current_status = status.iloc[i]
                    start_time = status.index[i]

            # 添加最后一个区间
            intervals.append((start_time, status.index[-1], current_status))

        # 绘图
        fig, ax = plt.subplots(figsize=(16, 5))

        # 定义颜色：0-白色，1-浅蓝，2-红色（对比度更高）
        colors = {
            0: 'white',
            1: '#87CEEB',  # 浅蓝
            2: '#FF6B6B'   # 红色
        }
        labels = {
            0: '无效数据',
            1: '有效数据（原始）',
            2: '有效数据（插值）'
        }

        # 绘制每个区间
        for start, end, s in intervals:
            ax.axvspan(start, end, color=colors[s], alpha=0.8)

        # 创建图例
        legend_elements = [
            Patch(facecolor=colors[0], edgecolor='black', label=labels[0]),
            Patch(facecolor=colors[1], edgecolor='black', label=labels[1]),
            Patch(facecolor=colors[2], edgecolor='black', label=labels[2])
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        ax.set_yticks([])  # 隐藏y轴刻度
        ax.set_xlabel('时间', fontsize=12)
        ax.set_title(f'{terminal} - 有效数据分布（甘特图）', fontsize=14)
        ax.grid(True, alpha=0.3, axis='x')

        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  {terminal}_valid_distribution.png")

def main():
    print("="*60)
    print("重新运行 Step 2 - 甘特图更新")
    print("="*60)

    # 加载 Step 1 数据
    step1_data = load_step1_data()
    print(f"已加载 {len(step1_data)} 个 Step 1 数据包")

    # 加载已有的 Step 2 处理结果
    terminal_data = {}
    for terminal in TERMINALS.keys():
        processed_file = STEP2_OUTPUT / 'results' / f'{terminal}_processed.csv'
        if processed_file.exists():
            df = pd.read_csv(processed_file, parse_dates=[0], index_col=0)
            # 只保留有效session数据
            if 'session_id' in df.columns:
                terminal_data[terminal] = df[df['session_id'].notna()].copy()
                print(f"{terminal}: 已加载 {len(terminal_data[terminal])} 条有效数据")

    # 重新生成甘特图
    generate_valid_distribution_plots(step1_data, terminal_data)

    print("\n" + "="*60)
    print("完成！")
    print("="*60)

if __name__ == '__main__':
    main()
