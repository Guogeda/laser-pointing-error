#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
硬编码温度与误差关系分析模块
注意：本模块必须使用硬编码方案，禁止使用智能方法！

主要功能：
1. 每个终端单独分析：前光路/后光路/载荷温度与误差关系
2. 严格按照硬编码的列名提取温度参数
3. 生成符合要求结构的CSV文件
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 添加配置路径
sys.path.insert(0, str(Path(__file__).parent / 'config'))

from satellite_groups import get_group_by_star, TERMINALS
from temperature_params import get_temperature_params


class TemperatureAnalyzer:
    """硬编码温度与误差关系分析器"""

    def __init__(self, base_dir):
        """
        初始化分析器

        参数:
            base_dir: 输出目录路径
        """
        self.base_dir = Path(base_dir)
        self.results = {}

        # 创建输出目录
        self.output_dir = self.base_dir / 'temperature_analysis'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir = self.output_dir / 'plots'
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir = self.output_dir / 'reports'
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = self.output_dir / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_terminal_data(self, star_name, terminal_name):
        """
        硬编码加载终端处理后的数据

        参数:
            star_name: 卫星名称
            terminal_name: 终端名称

        返回:
            tuple: (terminal_data, error_data)
        """
        # 硬编码加载路径
        terminal_file = self.base_dir / star_name / 'step2-state-filter' / 'results' / f'{terminal_name}_processed.csv'
        error_file = self.base_dir / star_name / 'step3-error-calc' / 'results' / f'error_{terminal_name}.csv'

        if not terminal_file.exists() or not error_file.exists():
            print(f"  未找到数据文件: {terminal_file} 或 {error_file}")
            return None, None

        terminal_data = pd.read_csv(terminal_file, parse_dates=[0], index_col=0)
        error_data = pd.read_csv(error_file, parse_dates=[0], index_col=0)

        return terminal_data, error_data

    def merge_temperature_and_error(self, terminal_data, error_data, star_name, terminal_name):
        """
        硬编码合并温度数据和误差数据，严格按照要求的结构

        参数:
            terminal_data: 终端数据
            error_data: 误差数据
            star_name: 卫星名称
            terminal_name: 终端名称

        返回:
            DataFrame: 合并后的数据
        """
        if terminal_data is None or error_data is None:
            return None

        # 对齐时间轴
        merged_data = pd.merge(terminal_data, error_data, left_index=True, right_index=True, how='inner')

        # 创建新的DataFrame，严格按照用户要求的结构组织
        output_data = pd.DataFrame(index=merged_data.index)

        # 1. 误差参数 - 严格硬编码列名
        if 'delta_A' in merged_data.columns:
            output_data['方位指向误差'] = merged_data['delta_A']
        if 'delta_E' in merged_data.columns:
            output_data['俯仰指向误差'] = merged_data['delta_E']
        if 'theta_error' in merged_data.columns:
            output_data['综合误差'] = merged_data['theta_error']

        # 2. 硬编码获取温度参数配置
        group_name = get_group_by_star(star_name)
        temp_config = get_temperature_params(group_name, terminal_name)

        if temp_config is None:
            print(f"  未找到{star_name} {terminal_name}的硬编码温度配置")
            return None

        # 3. 前光路温度 - 严格硬编码
        if temp_config['front_path'] in terminal_data.columns:
            output_data['前光路温度'] = terminal_data[temp_config['front_path']]

        # 4. 后光路温度 - 严格硬编码每一列，然后计算均值
        rear_path_cols = temp_config['rear_path']
        for i, col in enumerate(rear_path_cols):
            if col in terminal_data.columns:
                output_data[f'后光路温度{i+1}'] = terminal_data[col]

        # 计算后光路温度均值
        rear_temp_cols = [f'后光路温度{i+1}' for i in range(len(rear_path_cols)) if f'后光路温度{i+1}' in output_data.columns]
        if rear_temp_cols:
            output_data['后光路温度均值'] = output_data[rear_temp_cols].mean(axis=1)

        # 5. DBF载荷温度（3个）- 严格硬编码
        dbf_cols = []
        for col in temp_config['payload']:
            if 'RM15' in col or 'RM16' in col or 'RM17' in col:
                dbf_cols.append(col)

        for i, col in enumerate(dbf_cols):
            if col in terminal_data.columns:
                output_data[f'DBF载荷温度{i+1}'] = terminal_data[col]

        dbf_temp_cols = [f'DBF载荷温度{i+1}' for i in range(len(dbf_cols)) if f'DBF载荷温度{i+1}' in output_data.columns]
        if dbf_temp_cols:
            output_data['DBF载荷温度均值'] = output_data[dbf_temp_cols].mean(axis=1)

        # 6. L载荷温度（4个）- 严格硬编码
        l_cols = []
        for col in temp_config['payload']:
            if 'RM83' in col or 'RM89' in col or 'RM90' in col or 'RM91' in col:
                l_cols.append(col)

        for i, col in enumerate(l_cols):
            if col in terminal_data.columns:
                output_data[f'L载荷温度{i+1}'] = terminal_data[col]

        l_temp_cols = [f'L载荷温度{i+1}' for i in range(len(l_cols)) if f'L载荷温度{i+1}' in output_data.columns]
        if l_temp_cols:
            output_data['L载荷温度均值'] = output_data[l_temp_cols].mean(axis=1)

        # 7. Ka载荷温度（2个）- 严格硬编码
        ka_cols = []
        for col in temp_config['payload']:
            if 'RM99' in col or 'RM100' in col:
                ka_cols.append(col)

        for i, col in enumerate(ka_cols):
            if col in terminal_data.columns:
                output_data[f'Ka载荷温度{i+1}'] = terminal_data[col]

        ka_temp_cols = [f'Ka载荷温度{i+1}' for i in range(len(ka_cols)) if f'Ka载荷温度{i+1}' in output_data.columns]
        if ka_temp_cols:
            output_data['Ka载荷温度均值'] = output_data[ka_temp_cols].mean(axis=1)

        # 移除全NaN的行
        output_data = output_data.dropna(how='all')

        if len(output_data) < 100:
            print(f"  有效数据不足: {len(output_data)} 点")
            return None

        # 硬编码导出处理后的数据到CSV文件
        csv_file = self.data_dir / f'{star_name}_{terminal_name}_analysis_data.csv'
        output_data.to_csv(csv_file)
        print(f"  分析数据已保存到: {csv_file.name}")

        return output_data

    def plot_simple_temperature_analysis(self, merged_data, star_name, terminal_name):
        """
        绘制简单清晰的温度与误差关系图

        参数:
            merged_data: 合并后的温度和误差数据
            star_name: 卫星名称
            terminal_name: 终端名称
        """
        if merged_data is None:
            return

        error_col = '综合误差' if '综合误差' in merged_data.columns else '俯仰指向误差'
        if error_col not in merged_data.columns:
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()

        plot_idx = 0

        # 1. 前光路温度与误差
        if '前光路温度' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['前光路温度', error_col]].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['前光路温度'], valid_data[error_col], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['前光路温度'], valid_data[error_col])
                    z = np.polyfit(valid_data['前光路温度'], valid_data[error_col], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['前光路温度'], p(valid_data['前光路温度']), 'r--', lw=2)
                    ax.set_title(f'前光路温度 vs {error_col}\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'前光路温度 vs {error_col}')
                ax.set_xlabel('前光路温度 (°C)')
                ax.set_ylabel(f'{error_col} (°)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        # 2. 后光路温度均值与误差
        if '后光路温度均值' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['后光路温度均值', error_col]].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['后光路温度均值'], valid_data[error_col], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['后光路温度均值'], valid_data[error_col])
                    z = np.polyfit(valid_data['后光路温度均值'], valid_data[error_col], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['后光路温度均值'], p(valid_data['后光路温度均值']), 'r--', lw=2)
                    ax.set_title(f'后光路温度均值 vs {error_col}\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'后光路温度均值 vs {error_col}')
                ax.set_xlabel('后光路温度均值 (°C)')
                ax.set_ylabel(f'{error_col} (°)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        # 3. DBF载荷温度均值与误差
        if 'DBF载荷温度均值' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['DBF载荷温度均值', error_col]].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['DBF载荷温度均值'], valid_data[error_col], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['DBF载荷温度均值'], valid_data[error_col])
                    z = np.polyfit(valid_data['DBF载荷温度均值'], valid_data[error_col], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['DBF载荷温度均值'], p(valid_data['DBF载荷温度均值']), 'r--', lw=2)
                    ax.set_title(f'DBF载荷温度均值 vs {error_col}\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'DBF载荷温度均值 vs {error_col}')
                ax.set_xlabel('DBF载荷温度均值 (°C)')
                ax.set_ylabel(f'{error_col} (°)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        # 4. L载荷温度均值与误差
        if 'L载荷温度均值' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['L载荷温度均值', error_col]].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['L载荷温度均值'], valid_data[error_col], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['L载荷温度均值'], valid_data[error_col])
                    z = np.polyfit(valid_data['L载荷温度均值'], valid_data[error_col], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['L载荷温度均值'], p(valid_data['L载荷温度均值']), 'r--', lw=2)
                    ax.set_title(f'L载荷温度均值 vs {error_col}\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'L载荷温度均值 vs {error_col}')
                ax.set_xlabel('L载荷温度均值 (°C)')
                ax.set_ylabel(f'{error_col} (°)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        plt.tight_layout()
        plot_file = self.plots_dir / f'{star_name}_{terminal_name}_temp_error_scatter.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  散点图已保存到: {plot_file.name}")

    def analyze_single_terminal(self, star_name, terminal_name):
        """
        硬编码分析单个终端

        参数:
            star_name: 卫星名称
            terminal_name: 终端名称
        """
        print(f"\n============================================================")
        print(f"处理终端: {star_name} - {terminal_name}")
        print(f"============================================================")

        # 硬编码加载数据
        terminal_data, error_data = self.load_terminal_data(star_name, terminal_name)
        if terminal_data is None or error_data is None:
            print("  数据加载失败")
            return None

        # 硬编码合并数据
        merged_data = self.merge_temperature_and_error(terminal_data, error_data, star_name, terminal_name)
        if merged_data is None:
            print("  数据合并失败")
            return None

        # 绘制简单的分析图
        self.plot_simple_temperature_analysis(merged_data, star_name, terminal_name)

        self.results[f'{star_name}_{terminal_name}'] = merged_data

        return merged_data

    def generate_report(self):
        """生成简单的分析报告"""
        report_file = self.reports_dir / 'temperature_analysis_summary.md'

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 温度与误差关系分析报告（硬编码方案）\n\n")
            f.write("## 注意事项\n")
            f.write("本报告使用严格的硬编码方案生成，所有温度参数均严格按照配置的列名提取。\n\n")

            f.write("## 分析的终端\n")
            for key in self.results.keys():
                f.write(f"- {key}\n")

            f.write("\n## 生成的文件\n")
            f.write("### 数据文件（output/temperature_analysis/data/）\n")
            for data_file in sorted(self.data_dir.glob('*.csv')):
                f.write(f"- {data_file.name}\n")

            f.write("\n### 图表文件（output/temperature_analysis/plots/）\n")
            for plot_file in sorted(self.plots_dir.glob('*.png')):
                f.write(f"- {plot_file.name}\n")

        print(f"\n综合分析报告已生成: {report_file}")


def main():
    """主函数 - 硬编码分析所有可用终端"""
    base_dir = Path('output')
    analyzer = TemperatureAnalyzer(base_dir)

    # 硬编码分析已有的卫星
    available_stars = []
    for star_dir in base_dir.iterdir():
        if star_dir.is_dir() and star_dir.name.endswith('star'):
            available_stars.append(star_dir.name)

    print(f"找到卫星: {available_stars}")

    for star_name in available_stars:
        # 直接查找已有的processed文件，不依赖配置
        step2_results = base_dir / star_name / 'step2-state-filter' / 'results'
        step3_results = base_dir / star_name / 'step3-error-calc' / 'results'

        if not step2_results.exists() or not step3_results.exists():
            continue

        # 查找所有processed.csv文件
        terminals = []
        for proc_file in step2_results.glob('*_processed.csv'):
            terminal_name = proc_file.stem.replace('_processed', '')
            # 检查对应的error文件是否存在
            error_file = step3_results / f'error_{terminal_name}.csv'
            if error_file.exists():
                terminals.append(terminal_name)

        print(f"\n{star_name} 可用终端: {terminals}")

        for terminal_name in terminals:
            analyzer.analyze_single_terminal(star_name, terminal_name)

    analyzer.generate_report()


if __name__ == '__main__':
    main()
