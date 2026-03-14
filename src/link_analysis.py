#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
链路分析模块
分析：
1. 32-31 和 31-61 两条链路的关系
2. 温度与指向误差的关系
3. 预留太阳夹角分析接口
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 链路配对配置 - (卫星1, 终端1, 卫星2, 终端2)
LINK_PAIRS = [
    ('32star', 'B1', '31star', 'A1-1'),
    ('31star', 'A1-1', '61star', 'A2-1'),
]

# 卫星默认终端配置
STAR_DEFAULT_TERMINALS = {
    '31star': ['A1-1', 'A1-2'],
    '32star': ['B1', 'B2'],
    '61star': ['A2-1', 'A2-2'],
}

# 温度参数关键词（用于自动识别）
TEMP_KEYWORDS = [
    'RM',
    '温度',
    '热控',
    '反馈'
]

class LinkAnalyzer:
    """链路分析器"""

    def __init__(self, base_dir):
        """
        初始化链路分析器

        参数:
            base_dir: 输出目录路径
        """
        self.base_dir = Path(base_dir)
        self.results = {}

    def load_terminal_data(self, star_name, terminal_name):
        """
        加载终端处理后的数据

        参数:
            star_name: 卫星名称，如 '31star'
            terminal_name: 终端名称，如 'A1-1'

        返回:
            DataFrame: 终端处理后的数据
        """
        processed_file = self.base_dir / star_name / 'step2-state-filter' / 'results' / f'{terminal_name}_processed.csv'
        if not processed_file.exists():
            print(f"未找到文件: {processed_file}")
            return None
        return pd.read_csv(processed_file, parse_dates=[0], index_col=0)

    def load_error_data(self, star_name, terminal_name):
        """
        加载误差计算结果

        参数:
            star_name: 卫星名称，如 '31star'
            terminal_name: 终端名称，如 'A1-1'

        返回:
            DataFrame: 误差计算结果
        """
        error_file = self.base_dir / star_name / 'step3-error-calc' / 'results' / f'error_{terminal_name}.csv'
        if not error_file.exists():
            print(f"未找到文件: {error_file}")
            return None
        return pd.read_csv(error_file, parse_dates=[0], index_col=0)

    def merge_temperature_and_error(self, terminal_data, error_data):
        """
        合并温度数据和误差数据

        参数:
            terminal_data: 终端处理后的数据（包含温度）
            error_data: 误差计算结果

        返回:
            DataFrame: 合并后的数据
        """
        if terminal_data is None or error_data is None:
            return None

        # 找到可用的温度参数（通过关键词自动识别）
        available_temp_params = []
        for col in terminal_data.columns:
            # 跳过标记列和插值标记列
            if col.endswith('_标记') or col.endswith('_interp'):
                continue
            # 检查是否包含温度相关关键词
            if any(keyword in col for keyword in TEMP_KEYWORDS):
                available_temp_params.append(col)

        if not available_temp_params:
            print("未找到可用的温度参数")
            return None

        # 合并数据
        merged_data = pd.DataFrame(index=terminal_data.index)

        # 添加温度数据
        for temp_param in available_temp_params:
            merged_data[temp_param] = terminal_data[temp_param]

        # 添加误差数据
        if 'theta_error' in error_data.columns:
            merged_data['theta_error'] = error_data['theta_error']
        if 'delta_A' in error_data.columns:
            merged_data['delta_A'] = error_data['delta_A']
        if 'delta_E' in error_data.columns:
            merged_data['delta_E'] = error_data['delta_E']

        return merged_data

    def analyze_temperature_error_correlation(self, merged_data, star_name, terminal_name):
        """
        分析温度与误差的相关性

        参数:
            merged_data: 合并后的温度和误差数据
            star_name: 卫星名称
            terminal_name: 终端名称

        返回:
            dict: 相关性分析结果
        """
        if merged_data is None or len(merged_data) < 100:
            return None

        results = {
            'star_name': star_name,
            'terminal_name': terminal_name,
            'correlations': {},
            'p_values': {}
        }

        # 找到误差列
        error_cols = [col for col in merged_data.columns if col in ['theta_error', 'delta_A', 'delta_E']]
        if not error_cols:
            return None

        # 找到温度列（通过关键词自动识别）
        temp_cols = []
        for col in merged_data.columns:
            if any(keyword in col for keyword in TEMP_KEYWORDS):
                temp_cols.append(col)
        if not temp_cols:
            return None

        for error_col in error_cols:
            for temp_col in temp_cols:
                # 移除 NaN 值
                valid_data = merged_data[[error_col, temp_col]].dropna()
                if len(valid_data) < 50:
                    continue

                # 计算皮尔逊相关系数，添加异常处理
                try:
                    # 检查数据是否有足够的变化
                    if valid_data[temp_col].std() < 1e-10 or valid_data[error_col].std() < 1e-10:
                        continue

                    corr, p_value = stats.pearsonr(valid_data[temp_col], valid_data[error_col])

                    key = f"{temp_col} vs {error_col}"
                    results['correlations'][key] = corr
                    results['p_values'][key] = p_value
                except Exception as e:
                    print(f"  跳过相关性计算: {temp_col} vs {error_col}, 错误: {e}")
                    continue

        return results

    def plot_temperature_error_correlation(self, merged_data, star_name, terminal_name):
        """
        绘制温度与误差的关系图

        参数:
            merged_data: 合并后的温度和误差数据
            star_name: 卫星名称
            terminal_name: 终端名称
        """
        if merged_data is None or len(merged_data) < 100:
            return

        # 找到误差列和温度列
        error_cols = [col for col in merged_data.columns if col in ['theta_error', 'delta_A', 'delta_E']]
        temp_cols = []
        for col in merged_data.columns:
            if any(keyword in col for keyword in TEMP_KEYWORDS):
                temp_cols.append(col)

        if not error_cols or not temp_cols:
            return

        # 限制温度列数量，避免图表过多
        temp_cols = temp_cols[:4]

        for error_col in error_cols:
            n_cols = min(2, len(temp_cols))
            n_rows = (len(temp_cols) + n_cols - 1) // n_cols

            fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 4 * n_rows))
            if n_rows == 1 and n_cols == 1:
                axes = np.array([axes])
            axes = axes.flatten()

            for i, temp_col in enumerate(temp_cols):
                ax = axes[i]

                # 移除 NaN 值
                valid_data = merged_data[[error_col, temp_col]].dropna()
                if len(valid_data) < 50:
                    continue

                # 散点图
                ax.scatter(valid_data[temp_col], valid_data[error_col], alpha=0.5, s=10)

                # 添加趋势线和计算相关系数，添加异常处理
                try:
                    if valid_data[temp_col].std() < 1e-10 or valid_data[error_col].std() < 1e-10:
                        continue

                    # 添加趋势线
                    z = np.polyfit(valid_data[temp_col], valid_data[error_col], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data[temp_col], p(valid_data[temp_col]), 'r--', lw=2)

                    corr, p_value = stats.pearsonr(valid_data[temp_col], valid_data[error_col])
                except Exception as e:
                    print(f"  跳过绘图: {temp_col} vs {error_col}, 错误: {e}")
                    continue

                ax.set_xlabel(temp_col)
                ax.set_ylabel(error_col)
                ax.set_title(f'{temp_col} vs {error_col} (corr={corr:.3f}, p={p_value:.3e})')
                ax.grid(True, alpha=0.3)

            # 移除空的子图
            for i in range(len(temp_cols), len(axes)):
                axes[i].axis('off')

            plt.tight_layout()

            # 保存图像
            plot_dir = self.base_dir / 'step3-error-calc' / 'plots'
            plot_dir.mkdir(parents=True, exist_ok=True)
            plot_file = plot_dir / f'{star_name}_{terminal_name}_temp_vs_{error_col}.png'
            plt.savefig(plot_file, dpi=150, bbox_inches='tight')
            plt.close()

            print(f"温度-误差关系图 → {plot_file.name}")

    def plot_time_series_comparison(self, terminal_data, error_data, star_name, terminal_name):
        """
        绘制时间序列对比图（温度和误差）

        参数:
            terminal_data: 终端处理后的数据
            error_data: 误差计算结果
            star_name: 卫星名称
            terminal_name: 终端名称
        """
        if terminal_data is None or error_data is None:
            return

        # 找到温度列（通过关键词自动识别）
        temp_cols = []
        for col in terminal_data.columns:
            if any(keyword in col for keyword in TEMP_KEYWORDS) and not col.endswith('_标记') and not col.endswith('_interp'):
                temp_cols.append(col)
        if not temp_cols:
            return

        # 限制温度列数量
        temp_cols = temp_cols[:3]

        fig, axes = plt.subplots(len(temp_cols) + 1, 1, figsize=(16, 4 * (len(temp_cols) + 1)), sharex=True)

        # 绘制综合误差
        if 'theta_error' in error_data.columns:
            axes[0].plot(error_data.index, error_data['theta_error'], color='red', linewidth=0.5, label='综合误差')
            axes[0].set_ylabel('综合误差 (°)')
            axes[0].set_title(f'{star_name} - {terminal_name}: 综合误差与温度时间序列')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)

        # 绘制温度
        for i, temp_col in enumerate(temp_cols):
            if i + 1 < len(axes):
                axes[i + 1].plot(terminal_data.index, terminal_data[temp_col], label=temp_col, color='blue', linewidth=0.5)
                axes[i + 1].set_ylabel('温度 (°C)')
                axes[i + 1].legend()
                axes[i + 1].grid(True, alpha=0.3)

        axes[-1].set_xlabel('时间')
        plt.xticks(rotation=45)
        plt.tight_layout()

        # 保存图像
        plot_dir = self.base_dir / 'step3-error-calc' / 'plots'
        plot_dir.mkdir(parents=True, exist_ok=True)
        plot_file = plot_dir / f'{star_name}_{terminal_name}_temp_error_timeseries.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"温度-误差时间序列图 → {plot_file.name}")

    def analyze_single_star(self, star_name, terminal_name='A1-1'):
        """
        分析单颗卫星的温度-误差关系

        参数:
            star_name: 卫星名称，如 '31star'
            terminal_name: 终端名称，如 'A1-1'

        返回:
            dict: 分析结果
        """
        print(f"\n{'='*60}")
        print(f"分析 {star_name} - {terminal_name}")
        print(f"{'='*60}")

        # 加载数据
        terminal_data = self.load_terminal_data(star_name, terminal_name)
        error_data = self.load_error_data(star_name, terminal_name)

        if terminal_data is None or error_data is None:
            print(f"数据加载失败: {star_name} - {terminal_name}")
            return None

        # 合并数据
        merged_data = self.merge_temperature_and_error(terminal_data, error_data)

        # 分析相关性
        corr_result = self.analyze_temperature_error_correlation(merged_data, star_name, terminal_name)

        # 绘制关系图
        self.plot_temperature_error_correlation(merged_data, star_name, terminal_name)

        # 绘制时间序列对比图
        self.plot_time_series_comparison(terminal_data, error_data, star_name, terminal_name)

        if corr_result:
            print(f"  成功分析相关性，找到 {len(corr_result['correlations'])} 组关系")
        else:
            print(f"  相关性分析失败")

        return corr_result

    def find_available_terminal(self, star_name):
        """
        找到卫星可用的终端

        参数:
            star_name: 卫星名称

        返回:
            str: 可用的终端名称，如果没有则返回None
        """
        terminal_names = STAR_DEFAULT_TERMINALS.get(star_name, ['A1-1', 'A1-2', 'B1', 'B2', 'A2-1', 'A2-2'])

        for terminal_name in terminal_names:
            processed_file = self.base_dir / star_name / 'step2-state-filter' / 'results' / f'{terminal_name}_processed.csv'
            error_file = self.base_dir / star_name / 'step3-error-calc' / 'results' / f'error_{terminal_name}.csv'
            if processed_file.exists() and error_file.exists():
                return terminal_name

        return None

    def analyze_link_pair(self, star1_name, star2_name, terminal1_name=None, terminal2_name=None):
        """
        分析链路配对的关系

        参数:
            star1_name: 卫星1名称，如 '32star'
            star2_name: 卫星2名称，如 '31star'
            terminal1_name: 卫星1终端名称（可选，自动查找）
            terminal2_name: 卫星2终端名称（可选，自动查找）
        """
        print(f"\n{'='*60}")
        print(f"分析链路: {star1_name} <-> {star2_name}")
        print(f"{'='*60}")

        # 自动查找可用终端
        if terminal1_name is None:
            terminal1_name = self.find_available_terminal(star1_name)
            if terminal1_name:
                print(f"{star1_name} 使用终端: {terminal1_name}")

        if terminal2_name is None:
            terminal2_name = self.find_available_terminal(star2_name)
            if terminal2_name:
                print(f"{star2_name} 使用终端: {terminal2_name}")

        if terminal1_name is None or terminal2_name is None:
            print("找不到可用的终端数据")
            return

        # 加载两颗卫星的数据
        star1_terminal = self.load_terminal_data(star1_name, terminal1_name)
        star1_error = self.load_error_data(star1_name, terminal1_name)
        star2_terminal = self.load_terminal_data(star2_name, terminal2_name)
        star2_error = self.load_error_data(star2_name, terminal2_name)

        if star1_error is None or star2_error is None:
            print("数据加载失败")
            return

        # 时间对齐
        if 'theta_error' in star1_error.columns and 'theta_error' in star2_error.columns:
            # 合并误差数据
            merged_errors = pd.DataFrame({
                f'{star1_name}_error': star1_error['theta_error'],
                f'{star2_name}_error': star2_error['theta_error'],
            }).dropna()

            if len(merged_errors) < 100:
                print("有效数据不足")
                return

            # 检查数据是否有足够的变化
            star1_std = merged_errors[f'{star1_name}_error'].std()
            star2_std = merged_errors[f'{star2_name}_error'].std()

            if star1_std < 1e-10 or star2_std < 1e-10:
                print(f"数据方差不足: {star1_name} std={star1_std:.4e}, {star2_name} std={star2_std:.4e}")
                # 只生成时间序列图，不生成散点图和相关系数
                fig, ax = plt.subplots(figsize=(16, 6))
                ax.plot(merged_errors.index, merged_errors[f'{star1_name}_error'], label=star1_name, color='blue', linewidth=0.5, alpha=0.7)
                ax.plot(merged_errors.index, merged_errors[f'{star2_name}_error'], label=star2_name, color='red', linewidth=0.5, alpha=0.7)

                ax.set_xlabel('时间')
                ax.set_ylabel('综合误差 (°)')
                ax.set_title(f'链路误差时间序列: {star1_name} <-> {star2_name} (数据方差不足)')
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()

                plot_dir = self.base_dir / 'step3-error-calc' / 'plots'
                plot_dir.mkdir(parents=True, exist_ok=True)
                plot_file = plot_dir / f'link_{star1_name}_{star2_name}_error_timeseries.png'
                plt.savefig(plot_file, dpi=150, bbox_inches='tight')
                plt.close()

                print(f"链路误差时间序列图 → {plot_file.name}")

                return {
                    'correlation': np.nan,
                    'p_value': np.nan,
                    'valid_samples': len(merged_errors),
                    'note': '数据方差不足'
                }

            # 计算相关系数
            corr, p_value = stats.pearsonr(merged_errors[f'{star1_name}_error'], merged_errors[f'{star2_name}_error'])

            print(f"链路误差相关系数: {corr:.4f} (p={p_value:.4e})")

            # 绘制散点图
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.scatter(merged_errors[f'{star1_name}_error'], merged_errors[f'{star2_name}_error'], alpha=0.5, s=10)

            # 添加趋势线
            z = np.polyfit(merged_errors[f'{star1_name}_error'], merged_errors[f'{star2_name}_error'], 1)
            p = np.poly1d(z)
            ax.plot(merged_errors[f'{star1_name}_error'], p(merged_errors[f'{star1_name}_error']), 'r--', lw=2)

            ax.set_xlabel(f'{star1_name} 综合误差 (°)')
            ax.set_ylabel(f'{star2_name} 综合误差 (°)')
            ax.set_title(f'链路误差关系: {star1_name} <-> {star2_name} (corr={corr:.3f})')
            ax.grid(True, alpha=0.3)

            # 保存图像
            plot_dir = self.base_dir / 'step3-error-calc' / 'plots'
            plot_dir.mkdir(parents=True, exist_ok=True)
            plot_file = plot_dir / f'link_{star1_name}_{star2_name}_error_correlation.png'
            plt.savefig(plot_file, dpi=150, bbox_inches='tight')
            plt.close()

            print(f"链路误差关系图 → {plot_file.name}")

            # 绘制时间序列对比
            fig, ax = plt.subplots(figsize=(16, 6))
            ax.plot(merged_errors.index, merged_errors[f'{star1_name}_error'], label=star1_name, color='blue', linewidth=0.5, alpha=0.7)
            ax.plot(merged_errors.index, merged_errors[f'{star2_name}_error'], label=star2_name, color='red', linewidth=0.5, alpha=0.7)

            ax.set_xlabel('时间')
            ax.set_ylabel('综合误差 (°)')
            ax.set_title(f'链路误差时间序列: {star1_name} <-> {star2_name}')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()

            plot_file = plot_dir / f'link_{star1_name}_{star2_name}_error_timeseries.png'
            plt.savefig(plot_file, dpi=150, bbox_inches='tight')
            plt.close()

            print(f"链路误差时间序列图 → {plot_file.name}")

            return {
                'correlation': corr,
                'p_value': p_value,
                'valid_samples': len(merged_errors)
            }

        return None

    def generate_report(self, results):
        """
        生成分析报告

        参数:
            results: 分析结果

        返回:
            str: 报告内容
        """
        report = []
        report.append("# 链路分析报告\n\n")

        # 单星分析结果
        report.append("## 单星温度-误差相关性分析\n\n")
        report.append("| 卫星 | 终端 | 温度参数 | 误差类型 | 相关系数 | P值 |\n")
        report.append("|------|------|----------|----------|----------|-----|\n")

        for star_result in results.get('single_star', []):
            if not star_result:
                continue
            star_name = star_result['star_name']
            terminal_name = star_result['terminal_name']

            for key, corr in star_result['correlations'].items():
                temp_col, error_col = key.split(' vs ')
                p_value = star_result['p_values'][key]
                report.append(f"| {star_name} | {terminal_name} | {temp_col} | {error_col} | {corr:.4f} | {p_value:.4e} |\n")

        report.append("\n")

        # 链路分析结果
        if 'link_pairs' in results:
            report.append("## 链路误差相关性分析\n\n")
            report.append("| 卫星1 | 终端1 | 卫星2 | 终端2 | 相关系数 | P值 | 有效样本数 |\n")
            report.append("|-------|-------|-------|-------|----------|-----|-----------|\n")

            for link_result in results['link_pairs']:
                if link_result:
                    report.append(f"| {link_result['star1']} | {link_result.get('terminal1', 'A1-1')} | {link_result['star2']} | {link_result.get('terminal2', 'A1-1')} | {link_result['correlation']:.4f} | {link_result['p_value']:.4e} | {link_result['valid_samples']} |\n")

        return '\n'.join(report)

    def run_full_analysis(self):
        """
        运行完整的分析流程
        """
        all_results = {
            'single_star': [],
            'link_pairs': []
        }

        # 分析单颗卫星
        for star_name in ['31star', '32star', '61star']:
            # 尝试所有可能的终端
            terminal_names = STAR_DEFAULT_TERMINALS.get(star_name, ['A1-1', 'A1-2', 'B1', 'B2', 'A2-1', 'A2-2'])
            for terminal_name in terminal_names:
                result = self.analyze_single_star(star_name, terminal_name)
                if result:
                    all_results['single_star'].append(result)

        # 分析链路配对
        for star1, terminal1, star2, terminal2 in LINK_PAIRS:
            result = self.analyze_link_pair(star1, star2, terminal1, terminal2)
            if result:
                result['star1'] = star1
                result['star2'] = star2
                result['terminal1'] = terminal1
                result['terminal2'] = terminal2
                all_results['link_pairs'].append(result)

        # 生成报告
        report_content = self.generate_report(all_results)
        report_file = self.base_dir / 'step3-error-calc' / 'reports' / 'link_analysis_report.md'
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"\n链路分析报告 → {report_file.name}")

        return all_results


def main():
    """主函数"""
    base_dir = Path(__file__).parent.parent / 'output'
    analyzer = LinkAnalyzer(base_dir)
    analyzer.run_full_analysis()


if __name__ == '__main__':
    main()
