#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
载荷开关机与指向误差关系分析模块
主要功能：
1. 通过温度变化识别载荷开关机时间段
2. 绘制指向误差时间序列图，用区域面积标注载荷开关机时间段
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import signal

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

sys.path.insert(0, str(Path(__file__).parent / 'config'))

from satellite_groups import get_group_by_star, TERMINALS
from temperature_params import get_temperature_params


class PayloadPowerAnalyzer:
    """载荷开关机分析器"""

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.output_dir = self.base_dir / 'payload_power_analysis'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir = self.output_dir / 'plots'
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir = self.output_dir / 'reports'
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = self.output_dir / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_terminal_data(self, star_name, terminal_name):
        """加载终端处理后的数据和误差数据"""
        terminal_file = self.base_dir / star_name / 'step2-state-filter' / 'results' / f'{terminal_name}_processed.csv'
        error_file = self.base_dir / star_name / 'step3-error-calc' / 'results' / f'error_{terminal_name}.csv'

        if not terminal_file.exists() or not error_file.exists():
            print(f"  未找到数据文件: {terminal_file} 或 {error_file}")
            return None, None

        terminal_data = pd.read_csv(terminal_file, parse_dates=[0], index_col=0)
        error_data = pd.read_csv(error_file, parse_dates=[0], index_col=0)

        return terminal_data, error_data

    def detect_payload_power_periods(self, terminal_data, star_name, terminal_name):
        """
        通过温度变化识别三个载荷（DBF、L、Ka）的开关机时间段

        方法：
        1. 直接使用您指定的三个具体遥测参数：
           - DBF载荷温度：RM16-DBF安装面1(+Z)
           - L载荷温度：RM83-L射频单元本体（-Y3-X1）
           - Ka载荷温度：RM99-Ka接收相控阵主散热面1(+X)
        2. 计算温度变化率
        3. 检测温度快速上升（开机）和快速下降（关机）的时间点
        4. 确定每个载荷的开关机时间段
        """
        group_name = get_group_by_star(star_name)
        temp_config = get_temperature_params(group_name, terminal_name)

        if temp_config is None:
            return None

        # 直接提取指定的三个温度参数，不需要取平均值
        payload_info = {}

        # 处理DBF载荷温度 - 直接使用RM16-DBF安装面1(+Z)
        dbf_param = 'RM16-DBF安装面1(+Z)'
        if dbf_param in terminal_data.columns:
            dbf_temp = terminal_data[dbf_param]
            dbf_periods = self._detect_single_payload_periods(dbf_temp, star_name, terminal_name, 'DBF')
            dbf_temp_rate = dbf_temp.diff()
            payload_info['DBF'] = {
                'temperature': dbf_temp,
                'power_periods': dbf_periods,
                'temp_params': [dbf_param],
                'temp_rate': dbf_temp_rate
            }
        else:
            print("  未找到DBF载荷温度参数: RM16-DBF安装面1(+Z)")

        # 处理L载荷温度 - 直接使用RM83-L射频单元本体（-Y3-X1）
        l_param = 'RM83-L射频单元本体（-Y3-X1）'
        if l_param in terminal_data.columns:
            l_temp = terminal_data[l_param]
            l_periods = self._detect_single_payload_periods(l_temp, star_name, terminal_name, 'L')
            l_temp_rate = l_temp.diff()
            payload_info['L'] = {
                'temperature': l_temp,
                'power_periods': l_periods,
                'temp_params': [l_param],
                'temp_rate': l_temp_rate
            }
        else:
            print("  未找到L载荷温度参数: RM83-L射频单元本体（-Y3-X1）")

        # 处理Ka载荷温度 - 直接使用RM99-Ka接收相控阵主散热面1(+X)
        ka_param = 'RM99-Ka接收相控阵主散热面1(+X)'
        if ka_param in terminal_data.columns:
            ka_temp = terminal_data[ka_param]
            ka_periods = self._detect_single_payload_periods(ka_temp, star_name, terminal_name, 'Ka')
            ka_temp_rate = ka_temp.diff()
            payload_info['Ka'] = {
                'temperature': ka_temp,
                'power_periods': ka_periods,
                'temp_params': [ka_param],
                'temp_rate': ka_temp_rate
            }
        else:
            print("  未找到Ka载荷温度参数: RM99-Ka接收相控阵主散热面1(+X)")

        # 收集所有使用的温度参数
        all_payload_cols = []
        for payload_name in ['DBF', 'L', 'Ka']:
            if payload_name in payload_info:
                all_payload_cols.extend(payload_info[payload_name]['temp_params'])

        # 绘制温度变化率图
        self.plot_temperature_rate(payload_info, star_name, terminal_name)

        return payload_info

    def plot_temperature_rate(self, payload_info, star_name, terminal_name):
        """
        绘制温度变化率（斜率）图
        """
        fig, axes = plt.subplots(3, 1, figsize=(18, 15), sharex=True)
        colors = {'DBF': 'orange', 'L': 'purple', 'Ka': 'cyan'}
        payload_names = ['DBF', 'L', 'Ka']

        for i, payload_name in enumerate(payload_names):
            if payload_name in payload_info:
                ax = axes[i]
                temp_rate = payload_info[payload_name]['temp_rate']
                temp = payload_info[payload_name]['temperature']

                # 绘制温度变化率
                ax.plot(temp_rate.index, temp_rate,
                        color=colors[payload_name], linewidth=0.5, alpha=0.7,
                        label=f'{payload_name}温度变化率')

                # 添加阈值线（标准差的1.5倍）
                threshold = temp_rate.std() * 1.5
                ax.axhline(y=threshold, color='red', linestyle='--', linewidth=1, label=f'正阈值 ({threshold:.3f})')
                ax.axhline(y=-threshold, color='red', linestyle='--', linewidth=1, label=f'负阈值 ({-threshold:.3f})')

                ax.set_ylabel('温度变化率 (°C/s)', fontsize=10)
                ax.set_title(f'{star_name} - {terminal_name} - {payload_name}载荷温度变化率', fontsize=12)
                ax.legend(loc='upper right')
                ax.grid(True, alpha=0.3)

                # 在温度变化率图上标注开关机时间段
                for period in payload_info[payload_name]['power_periods']:
                    ax.axvspan(period['start'], period['end'], color=colors[payload_name], alpha=0.2)

                # 添加温度曲线（右轴）
                ax2 = ax.twinx()
                ax2.plot(temp.index, temp, color='gray', linewidth=0.8, alpha=0.6, label='温度')
                ax2.set_ylabel('温度 (°C)', fontsize=10, color='gray')
                ax2.tick_params(axis='y', labelcolor='gray')
                ax2.legend(loc='upper left')

        axes[-1].set_xlabel('时间', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()

        plot_file = self.plots_dir / f'{star_name}_{terminal_name}_temperature_rate.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  温度变化率图已保存到: {plot_file.name}")

    def _detect_single_payload_periods(self, payload_temp, star_name, terminal_name, payload_name):
        """
        检测单个载荷的开关机时间段，使用时间窗口温变速率检测：
        状态机逻辑：检测温度上升（开机）→ 等待关机 → 检测温度下降（关机）→ 完整周期
        """
        power_periods = []

        # 去掉无效数据
        valid_temp = payload_temp.dropna()
        if len(valid_temp) < 60:  # 至少1分钟数据
            return power_periods

        # 使用时间窗口计算温度变化率（参数来自用户验证）
        time_window_sec = 20
        threshold_factor = 1.5
        min_duration = 10
        target_duration = 20

        window_size = time_window_sec
        step_size = time_window_sec

        # 计算每个窗口的温度变化率
        temp_rates = []
        rate_times = []

        for i in range(window_size, len(valid_temp), step_size):
            window_start = i - window_size
            window_end = i

            if window_start >= 0 and window_end < len(valid_temp):
                temp_change = valid_temp.iloc[window_end] - valid_temp.iloc[window_start]
                time_change_sec = (valid_temp.index[window_end] - valid_temp.index[window_start]).total_seconds()

                if time_change_sec > 0:
                    rate = temp_change / time_change_sec  # 温度变化率 (°C/s)
                    temp_rates.append(rate)
                    rate_times.append(valid_temp.index[window_end])

        if len(temp_rates) < 2:
            return power_periods

        # 转换为Series便于处理
        temp_rate_series = pd.Series(temp_rates, index=rate_times)

        # 使用中值滤波平滑
        temp_rate_smooth = pd.Series(
            signal.medfilt(temp_rate_series.fillna(0), kernel_size=min(5, len(temp_rate_series))),
            index=temp_rate_series.index
        )

        # 动态阈值
        std_val = temp_rate_smooth.std()
        threshold_pos = std_val * threshold_factor  # 正阈值（温度上升）
        threshold_neg = -std_val * threshold_factor  # 负阈值（温度下降）

        # 检测温度上升阶段（开机）和下降阶段（关机）
        temp_rising_mask = temp_rate_smooth > threshold_pos
        temp_falling_mask = temp_rate_smooth < threshold_neg

        # 状态机
        in_power_on = False      # 是否在开机上升阶段
        in_cooling_down = False  # 是否在关机下降阶段
        power_on_start = None    # 开机开始时间
        cooling_down_start = None # 关机开始时间

        for i in range(1, len(temp_rate_smooth)):
            is_rising = temp_rising_mask.iloc[i]
            is_falling = temp_falling_mask.iloc[i]
            is_normal = not is_rising and not is_falling  # 速率在正常范围内

            # ====== 第一阶段：检测开机（温度上升）======
            if is_rising and not in_power_on and not in_cooling_down:
                in_power_on = True
                # 开机开始时间：从当前窗口回溯到窗口开始
                power_on_start = temp_rate_smooth.index[i - window_size]

            # ====== 第二阶段：开机上升阶段结束，等待关机 ======
            elif not is_rising and in_power_on and not in_cooling_down:
                in_power_on = False
                # 进入"等待关机"状态

            # ====== 第三阶段：检测关机（温度下降）======
            elif is_falling and not in_power_on and not in_cooling_down:
                in_cooling_down = True
                # 关机开始时间：从当前窗口回溯到窗口开始
                cooling_down_start = temp_rate_smooth.index[i - window_size]

            # ====== 第四阶段：关机下降阶段结束，标记完整周期 ======
            elif is_normal and not in_power_on and in_cooling_down and cooling_down_start is not None:
                in_cooling_down = False

                # 完整时间段 = 开机开始 到 关机结束
                period_start = power_on_start
                period_end = temp_rate_smooth.index[i - 1]  # 前一个窗口的结束时间

                if period_start is not None:
                    # 计算持续时间
                    duration = (period_end - period_start).total_seconds() / 60

                    # 取target_duration分钟的时间段（如果足够长）
                    if duration >= min_duration:
                        # 从开机开始取target_duration分钟
                        actual_end = min(period_end, period_start + pd.Timedelta(minutes=target_duration))
                        power_periods.append({
                            'start': period_start,
                            'end': actual_end,
                            'type': 'powered',
                            'power_on_start': power_on_start,
                            'cooling_down_start': cooling_down_start
                        })

                # 重置状态
                power_on_start = None
                cooling_down_start = None

        # 如果最后还在关机下降状态，结束于最后一个数据点
        if in_cooling_down and cooling_down_start is not None and power_on_start is not None:
            period_start = power_on_start
            period_end = valid_temp.index[-1]

            duration = (period_end - period_start).total_seconds() / 60

            if duration >= min_duration:
                actual_end = min(period_end, period_start + pd.Timedelta(minutes=target_duration))
                power_periods.append({
                    'start': period_start,
                    'end': actual_end,
                    'type': 'powered',
                    'power_on_start': power_on_start,
                    'cooling_down_start': cooling_down_start
                })

        return power_periods

    def plot_error_with_payload_periods(self, terminal_data, error_data, power_info, star_name, terminal_name):
        """
        绘制指向误差时间序列图，用区域面积标注三个载荷（DBF、L、Ka）的开关机时间段
        """
        if error_data is None or power_info is None:
            return

        # 合并误差数据
        merged_data = pd.merge(
            terminal_data,
            error_data,
            left_index=True,
            right_index=True,
            how='inner'
        )

        if len(merged_data) < 100:
            print(f"  有效数据不足: {len(merged_data)}")
            return

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(18, 12), sharex=True)

        # 1. 方位误差
        ax1.plot(merged_data.index, merged_data['delta_A'],
                 color='blue', linewidth=0.5, label='方位误差', alpha=0.7)
        ax1.set_ylabel('方位误差 (°)', fontsize=12)
        ax1.set_title(f'{star_name} - {terminal_name} - 三个载荷开关机与指向误差关系', fontsize=14)
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)

        # 2. 俯仰误差
        ax2.plot(merged_data.index, merged_data['delta_E'],
                 color='green', linewidth=0.5, label='俯仰误差', alpha=0.7)
        ax2.set_ylabel('俯仰误差 (°)', fontsize=12)
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)

        # 3. 综合误差 + 载荷温度
        ax3.plot(merged_data.index, merged_data['theta_error'],
                 color='red', linewidth=0.5, label='综合误差', alpha=0.7)
        ax3.set_ylabel('综合误差 (°)', fontsize=12)
        ax3.set_xlabel('时间', fontsize=12)
        ax3.legend(loc='upper right')
        ax3.grid(True, alpha=0.3)

        # 绘制三个载荷的温度（右轴）
        ax4 = ax3.twinx()
        colors = {'DBF': 'orange', 'L': 'purple', 'Ka': 'cyan'}
        for payload_name in ['DBF', 'L', 'Ka']:
            if payload_name in power_info:
                ax4.plot(power_info[payload_name]['temperature'].index,
                         power_info[payload_name]['temperature'],
                         color=colors[payload_name], linewidth=1,
                         label=f'{payload_name}载荷温度', alpha=0.8)
        ax4.set_ylabel('载荷温度 (°C)', fontsize=12)
        ax4.legend(loc='upper left')

        # 标注三个载荷的开机时间段（区域面积）
        legend_elements = [
            Patch(facecolor='yellow', alpha=0.2, edgecolor='orange', label='DBF载荷开机'),
            Patch(facecolor='purple', alpha=0.2, edgecolor='purple', label='L载荷开机'),
            Patch(facecolor='cyan', alpha=0.2, edgecolor='cyan', label='Ka载荷开机'),
            Patch(facecolor='blue', alpha=0.5, label='方位误差'),
            Patch(facecolor='green', alpha=0.5, label='俯仰误差'),
            Patch(facecolor='red', alpha=0.5, label='综合误差'),
            Patch(facecolor='orange', alpha=0.5, label='DBF温度'),
            Patch(facecolor='purple', alpha=0.5, label='L温度'),
            Patch(facecolor='cyan', alpha=0.5, label='Ka温度')
        ]

        # 为每个载荷绘制开机时间段
        payload_colors = {'DBF': 'yellow', 'L': 'purple', 'Ka': 'cyan'}
        for payload_name, color in payload_colors.items():
            if payload_name in power_info:
                for period in power_info[payload_name]['power_periods']:
                    start_time = period['start']
                    end_time = period['end']

                    # 在所有子图上标注
                    for ax in [ax1, ax2, ax3]:
                        ax.axvspan(start_time, end_time, color=color, alpha=0.2)

        # 添加统一的图例
        fig.legend(handles=legend_elements, loc='lower center',
                   ncol=9, bbox_to_anchor=(0.5, 0.01), fontsize=9)

        plt.xticks(rotation=45)
        plt.tight_layout()

        plot_file = self.plots_dir / f'{star_name}_{terminal_name}_payload_power_error.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  载荷开关机分析图已保存到: {plot_file.name}")

        # 保存详细数据
        data_file = self.data_dir / f'{star_name}_{terminal_name}_payload_analysis.csv'
        output_df = pd.DataFrame({
            'delta_A': merged_data['delta_A'],
            'delta_E': merged_data['delta_E'],
            'theta_error': merged_data['theta_error']
        })

        # 添加三个载荷的温度数据
        for payload_name in ['DBF', 'L', 'Ka']:
            if payload_name in power_info:
                output_df[f'{payload_name}_temperature'] = power_info[payload_name]['temperature']

        output_df.to_csv(data_file)

        # 整理所有载荷的开机时间段
        all_periods = []
        for payload_name in ['DBF', 'L', 'Ka']:
            if payload_name in power_info:
                for period in power_info[payload_name]['power_periods']:
                    period['payload'] = payload_name
                    all_periods.append(period)

        return all_periods

    def analyze_single_terminal(self, star_name, terminal_name):
        """分析单个终端"""
        print(f"\n============================================================")
        print(f"载荷开关机分析终端: {star_name} - {terminal_name}")
        print(f"============================================================")

        terminal_data, error_data = self.load_terminal_data(star_name, terminal_name)
        if terminal_data is None or error_data is None:
            return None, None

        power_info = self.detect_payload_power_periods(terminal_data, star_name, terminal_name)
        if power_info is None:
            return None, None

        periods = self.plot_error_with_payload_periods(
            terminal_data, error_data, power_info, star_name, terminal_name
        )

        return periods, power_info

    def generate_report(self, all_periods, power_info_dict):
        """生成分析报告"""
        report_file = self.reports_dir / 'payload_power_analysis_report.md'

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 三个载荷（DBF、L、Ka）开关机与指向误差关系分析报告\n\n")
            f.write(f"**生成时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 分析的终端\n")
            for key in all_periods.keys():
                f.write(f"- {key}\n")

            f.write("\n## 载荷温度使用的遥测量说明\n")
            for star_terminal, power_info in power_info_dict.items():
                f.write(f"\n### {star_terminal}\n")
                for payload_name in ['DBF', 'L', 'Ka']:
                    if payload_name in power_info:
                        f.write(f"- **{payload_name}载荷温度**: 使用以下遥测量\n")
                        for param in power_info[payload_name]['temp_params']:
                            f.write(f"  - {param}\n")

            f.write("\n## 三个载荷开机时间段统计\n")
            for key, periods in all_periods.items():
                f.write(f"\n### {key}\n")

                # 按载荷类型分组统计
                dbf_periods = [p for p in periods if p['payload'] == 'DBF']
                l_periods = [p for p in periods if p['payload'] == 'L']
                ka_periods = [p for p in periods if p['payload'] == 'Ka']

                if dbf_periods:
                    f.write(f"- DBF载荷: 检测到 {len(dbf_periods)} 个开机时间段\n")
                    for i, period in enumerate(dbf_periods):
                        duration = (period['end'] - period['start']).total_seconds() / 60
                        f.write(f"  时间段 {i+1}: {period['start']} 至 {period['end']}, 持续 {duration:.1f} 分钟\n")

                if l_periods:
                    f.write(f"- L载荷: 检测到 {len(l_periods)} 个开机时间段\n")
                    for i, period in enumerate(l_periods):
                        duration = (period['end'] - period['start']).total_seconds() / 60
                        f.write(f"  时间段 {i+1}: {period['start']} 至 {period['end']}, 持续 {duration:.1f} 分钟\n")

                if ka_periods:
                    f.write(f"- Ka载荷: 检测到 {len(ka_periods)} 个开机时间段\n")
                    for i, period in enumerate(ka_periods):
                        duration = (period['end'] - period['start']).total_seconds() / 60
                        f.write(f"  时间段 {i+1}: {period['start']} 至 {period['end']}, 持续 {duration:.1f} 分钟\n")

                if not (dbf_periods or l_periods or ka_periods):
                    f.write("- 未检测到明显的载荷开机时间段\n")

            f.write("\n## 生成的文件\n")
            f.write("### 数据文件（output/payload_power_analysis/data/）\n")
            for data_file in sorted(self.data_dir.glob('*.csv')):
                f.write(f"- {data_file.name}\n")

            f.write("\n### 图表文件（output/payload_power_analysis/plots/）\n")
            for plot_file in sorted(self.plots_dir.glob('*.png')):
                f.write(f"- {plot_file.name}\n")

        print(f"\n载荷开关机分析报告已生成: {report_file}")


def main():
    """主函数"""
    base_dir = Path('output')
    analyzer = PayloadPowerAnalyzer(base_dir)

    all_periods = {}
    power_info_dict = {}

    # 分析已有的卫星
    available_stars = []
    for star_dir in base_dir.iterdir():
        if star_dir.is_dir() and star_dir.name.endswith('star'):
            available_stars.append(star_dir.name)

    print(f"找到卫星: {available_stars}")

    for star_name in available_stars:
        step2_results = base_dir / star_name / 'step2-state-filter' / 'results'
        step3_results = base_dir / star_name / 'step3-error-calc' / 'results'

        if not step2_results.exists() or not step3_results.exists():
            continue

        # 查找所有processed.csv文件
        terminals = []
        for proc_file in step2_results.glob('*_processed.csv'):
            terminal_name = proc_file.stem.replace('_processed', '')
            error_file = step3_results / f'error_{terminal_name}.csv'
            if error_file.exists():
                terminals.append(terminal_name)

        print(f"\n{star_name} 可用终端: {terminals}")

        for terminal_name in terminals:
            periods, power_info = analyzer.analyze_single_terminal(star_name, terminal_name)
            if periods is not None and power_info is not None:
                star_terminal_key = f'{star_name}_{terminal_name}'
                all_periods[star_terminal_key] = periods
                power_info_dict[star_terminal_key] = power_info

    analyzer.generate_report(all_periods, power_info_dict)


if __name__ == '__main__':
    main()
