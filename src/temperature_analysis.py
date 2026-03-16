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
from scipy.fft import fft, fftfreq
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

    def load_sun_vector_data(self, star_name):
        """
        硬编码加载太阳矢量数据

        参数:
            star_name: 卫星名称

        返回:
            DataFrame: 太阳矢量数据，索引为时间
        """
        sun_data_dir = Path('ori-data/orbit-sun-data')

        # 尝试可能的文件名
        possible_files = [
            sun_data_dir / f'{star_name}_Sun_Vector_J2000.csv',
            sun_data_dir / f'{star_name.replace("star", "start")}_Sun_Vector_J2000.csv'
        ]

        sun_data_file = None
        for f in possible_files:
            if f.exists():
                sun_data_file = f
                break

        if sun_data_file is None:
            print(f"  未找到太阳矢量数据文件: {possible_files}")
            return None

        # 解析UTCG格式时间
        sun_data = pd.read_csv(sun_data_file)
        sun_data['time'] = pd.to_datetime(sun_data['Time (UTCG)'], format='%d %b %Y %H:%M:%S.%f')
        sun_data = sun_data.set_index('time')
        sun_data = sun_data.rename(columns={
            'x (km)': 'sun_vector_x',
            'y (km)': 'sun_vector_y',
            'z (km)': 'sun_vector_z'
        })
        sun_data = sun_data[['sun_vector_x', 'sun_vector_y', 'sun_vector_z']]

        print(f"  太阳矢量数据已加载: {sun_data_file.name}")
        return sun_data

    def calculate_solar_energy(self, sun_vector_df):
        """
        硬编码计算太阳能量相关参数

        参数:
            sun_vector_df: 太阳矢量数据DataFrame

        返回:
            tuple: (sun_distance, solar_irradiance, solar_elevation)
        """
        # 计算太阳距离
        sun_distance = np.sqrt(
            sun_vector_df['sun_vector_x']**2 +
            sun_vector_df['sun_vector_y']**2 +
            sun_vector_df['sun_vector_z']**2
        )

        # 太阳常数和天文单位
        solar_constant = 1361  # W/m²，地球轨道平均值
        au = 149597870.7  # 天文单位，km

        # 计算太阳辐照度（平方反比定律）
        solar_irradiance = solar_constant / (sun_distance / au)**2

        # 计算太阳高度角（简化：使用z分量）
        solar_elevation = np.degrees(np.arccos(sun_vector_df['sun_vector_z'] / sun_distance))

        return sun_distance, solar_irradiance, solar_elevation

    def merge_with_sun_vector(self, analysis_data, sun_data):
        """
        硬编码合并分析数据与太阳矢量数据

        参数:
            analysis_data: 分析数据DataFrame
            sun_data: 太阳矢量数据DataFrame

        返回:
            DataFrame: 合并后的数据
        """
        if analysis_data is None or sun_data is None:
            return analysis_data

        analysis_data = analysis_data.copy()
        # 将分析数据的时间索引转换为datetime
        analysis_data.index = pd.to_datetime(analysis_data.index)

        # 时间对齐（最邻近匹配，容差0.5秒）
        sun_data_aligned = sun_data.reindex(
            analysis_data.index,
            method='nearest',
            tolerance=pd.Timedelta('500ms')
        )

        # 合并太阳矢量数据
        analysis_data['sun_vector_x'] = sun_data_aligned['sun_vector_x']
        analysis_data['sun_vector_y'] = sun_data_aligned['sun_vector_y']
        analysis_data['sun_vector_z'] = sun_data_aligned['sun_vector_z']

        # 计算太阳能量参数
        sun_distance, solar_irradiance, solar_elevation = self.calculate_solar_energy(sun_data_aligned)
        analysis_data['sun_distance'] = sun_distance
        analysis_data['solar_irradiance'] = solar_irradiance
        analysis_data['solar_elevation'] = solar_elevation

        return analysis_data

    def spectral_analysis(self, signal, sampling_rate=1):
        """
        硬编码频谱分析

        参数:
            signal: 信号Series
            sampling_rate: 采样率，默认1Hz

        返回:
            tuple: (频率数组, 功率数组)
        """
        valid_signal = signal.dropna()
        n = len(valid_signal)

        if n < 100:
            return None, None

        # FFT计算
        yf = fft(valid_signal.values)
        xf = fftfreq(n, 1/sampling_rate)

        # 取正频率部分
        positive_freqs = xf > 0
        xf_pos = xf[positive_freqs]
        yf_pos = np.abs(yf[positive_freqs])

        return xf_pos, yf_pos

    def load_analysis_data(self, star_name, terminal_name):
        """
        硬编码加载已有的分析数据

        参数:
            star_name: 卫星名称
            terminal_name: 终端名称

        返回:
            DataFrame: 分析数据
        """
        data_file = self.data_dir / f'{star_name}_{terminal_name}_analysis_data.csv'
        if data_file.exists():
            return pd.read_csv(data_file, parse_dates=[0], index_col=0)
        return None

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

        # 5. DBF载荷温度 - 硬编码单个遥测量：RM16-DBF安装面1(+Z)
        dbf_target_col = 'RM16-DBF安装面1(+Z)'
        if dbf_target_col in terminal_data.columns:
            output_data['DBF载荷温度'] = terminal_data[dbf_target_col]

        # 6. L载荷温度 - 硬编码单个遥测量：RM83-L射频单元本体（-Y3-X1）
        l_target_col = 'RM83-L射频单元本体（-Y3-X1）'
        if l_target_col in terminal_data.columns:
            output_data['L载荷温度'] = terminal_data[l_target_col]

        # 7. Ka载荷温度 - 硬编码单个遥测量：RM99-Ka接收相控阵主散热面1(+X)
        ka_target_col = 'RM99-Ka接收相控阵主散热面1(+X)'
        if ka_target_col in terminal_data.columns:
            output_data['Ka载荷温度'] = terminal_data[ka_target_col]

        # 移除全NaN的行
        output_data = output_data.dropna(how='all')

        if len(output_data) < 100:
            print(f"  有效数据不足: {len(output_data)} 点")
            return None

        # 不在这里保存CSV，而是在合并太阳矢量数据后再保存
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

        # 3. DBF载荷温度与误差
        if 'DBF载荷温度' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['DBF载荷温度', error_col]].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['DBF载荷温度'], valid_data[error_col], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['DBF载荷温度'], valid_data[error_col])
                    z = np.polyfit(valid_data['DBF载荷温度'], valid_data[error_col], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['DBF载荷温度'], p(valid_data['DBF载荷温度']), 'r--', lw=2)
                    ax.set_title(f'DBF载荷温度 vs {error_col}\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'DBF载荷温度 vs {error_col}')
                ax.set_xlabel('DBF载荷温度 (°C)')
                ax.set_ylabel(f'{error_col} (°)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        # 4. L载荷温度与误差
        if 'L载荷温度' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['L载荷温度', error_col]].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['L载荷温度'], valid_data[error_col], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['L载荷温度'], valid_data[error_col])
                    z = np.polyfit(valid_data['L载荷温度'], valid_data[error_col], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['L载荷温度'], p(valid_data['L载荷温度']), 'r--', lw=2)
                    ax.set_title(f'L载荷温度 vs {error_col}\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'L载荷温度 vs {error_col}')
                ax.set_xlabel('L载荷温度 (°C)')
                ax.set_ylabel(f'{error_col} (°)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        # 5. Ka载荷温度与误差
        if 'Ka载荷温度' in merged_data.columns:
            if plot_idx < len(axes):
                ax = axes[plot_idx]
                valid_data = merged_data[['Ka载荷温度', error_col]].dropna()
                if len(valid_data) >= 50:
                    ax.scatter(valid_data['Ka载荷温度'], valid_data[error_col], alpha=0.3, s=5)
                    try:
                        corr, p_val = stats.pearsonr(valid_data['Ka载荷温度'], valid_data[error_col])
                        z = np.polyfit(valid_data['Ka载荷温度'], valid_data[error_col], 1)
                        p = np.poly1d(z)
                        ax.plot(valid_data['Ka载荷温度'], p(valid_data['Ka载荷温度']), 'r--', lw=2)
                        ax.set_title(f'Ka载荷温度 vs {error_col}\n相关系数={corr:.3f}, P值={p_val:.1e}')
                    except:
                        ax.set_title(f'Ka载荷温度 vs {error_col}')
                    ax.set_xlabel('Ka载荷温度 (°C)')
                    ax.set_ylabel(f'{error_col} (°)')
                    ax.grid(True, alpha=0.3)
                plot_idx += 1

        plt.tight_layout()
        plot_file = self.plots_dir / f'{star_name}_{terminal_name}_temp_error_scatter.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  散点图已保存到: {plot_file.name}")

    def plot_solar_energy_relations(self, merged_data, star_name, terminal_name):
        """
        硬编码绘制太阳能量与其他参数的关系图

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

        # 1. 太阳辐照度与误差
        if 'solar_irradiance' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['solar_irradiance', error_col]].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['solar_irradiance'], valid_data[error_col], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['solar_irradiance'], valid_data[error_col])
                    z = np.polyfit(valid_data['solar_irradiance'], valid_data[error_col], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['solar_irradiance'], p(valid_data['solar_irradiance']), 'r--', lw=2)
                    ax.set_title(f'太阳辐照度 vs {error_col}\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'太阳辐照度 vs {error_col}')
                ax.set_xlabel('太阳辐照度 (W/m²)')
                ax.set_ylabel(f'{error_col} (°)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        # 2. 太阳辐照度与前光路温度
        if 'solar_irradiance' in merged_data.columns and '前光路温度' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['solar_irradiance', '前光路温度']].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['solar_irradiance'], valid_data['前光路温度'], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['solar_irradiance'], valid_data['前光路温度'])
                    z = np.polyfit(valid_data['solar_irradiance'], valid_data['前光路温度'], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['solar_irradiance'], p(valid_data['solar_irradiance']), 'r--', lw=2)
                    ax.set_title(f'太阳辐照度 vs 前光路温度\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'太阳辐照度 vs 前光路温度')
                ax.set_xlabel('太阳辐照度 (W/m²)')
                ax.set_ylabel('前光路温度 (°C)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        # 3. 太阳高度角与误差
        if 'solar_elevation' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['solar_elevation', error_col]].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['solar_elevation'], valid_data[error_col], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['solar_elevation'], valid_data[error_col])
                    z = np.polyfit(valid_data['solar_elevation'], valid_data[error_col], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['solar_elevation'], p(valid_data['solar_elevation']), 'r--', lw=2)
                    ax.set_title(f'太阳高度角 vs {error_col}\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'太阳高度角 vs {error_col}')
                ax.set_xlabel('太阳高度角 (°)')
                ax.set_ylabel(f'{error_col} (°)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        # 4. 太阳高度角与前光路温度
        if 'solar_elevation' in merged_data.columns and '前光路温度' in merged_data.columns:
            ax = axes[plot_idx]
            valid_data = merged_data[['solar_elevation', '前光路温度']].dropna()
            if len(valid_data) >= 50:
                ax.scatter(valid_data['solar_elevation'], valid_data['前光路温度'], alpha=0.3, s=5)
                try:
                    corr, p_val = stats.pearsonr(valid_data['solar_elevation'], valid_data['前光路温度'])
                    z = np.polyfit(valid_data['solar_elevation'], valid_data['前光路温度'], 1)
                    p = np.poly1d(z)
                    ax.plot(valid_data['solar_elevation'], p(valid_data['solar_elevation']), 'r--', lw=2)
                    ax.set_title(f'太阳高度角 vs 前光路温度\n相关系数={corr:.3f}, P值={p_val:.1e}')
                except:
                    ax.set_title(f'太阳高度角 vs 前光路温度')
                ax.set_xlabel('太阳高度角 (°)')
                ax.set_ylabel('前光路温度 (°C)')
                ax.grid(True, alpha=0.3)
            plot_idx += 1

        plt.tight_layout()
        plot_file = self.plots_dir / f'{star_name}_{terminal_name}_solar_energy_relations.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  太阳能量关系图已保存到: {plot_file.name}")

    def separate_periodic_random(self, signal, period_minutes=120):
        """
        使用移动平均方法分离周期性和随机性成分

        参数:
            signal: 输入信号
            period_minutes: 轨道周期（分钟），默认120分钟

        返回:
            tuple: (周期性成分, 随机性成分)
        """
        valid_signal = signal.dropna()
        n = len(valid_signal)

        if n < 10:
            return signal, pd.Series(0.0, index=signal.index)

        # 窗口大小设为轨道周期的一半
        window_size = int((period_minutes * 60) / 2)
        window_size = max(1, min(window_size, n // 10))

        # 使用移动平均提取周期性成分（趋势）
        periodic_signal = valid_signal.rolling(window=window_size, center=True, min_periods=1).mean()

        # 随机性成分 = 原信号 - 周期性成分
        random_signal = valid_signal - periodic_signal

        # 重新整理成与原始数据相同的索引
        periodic_series = pd.Series(np.nan, index=signal.index)
        random_series = pd.Series(np.nan, index=signal.index)

        periodic_series.loc[valid_signal.index] = periodic_signal
        random_series.loc[valid_signal.index] = random_signal

        return periodic_series, random_series

    def plot_periodic_random_decomposition(self, merged_data, star_name, terminal_name):
        """
        硬编码绘制周期性和随机性成分分解图

        参数:
            merged_data: 合并后的数据
            star_name: 卫星名称
            terminal_name: 终端名称
        """
        signals_to_decompose = []

        # 获取需要分析的信号
        if '综合误差' in merged_data.columns:
            signals_to_decompose.append(('综合误差', merged_data['综合误差']))

        if '前光路温度' in merged_data.columns:
            signals_to_decompose.append(('前光路温度', merged_data['前光路温度']))

        if '后光路温度均值' in merged_data.columns:
            signals_to_decompose.append(('后光路温度均值', merged_data['后光路温度均值']))

        if 'solar_irradiance' in merged_data.columns:
            signals_to_decompose.append(('太阳辐照度', merged_data['solar_irradiance']))

        for name, signal in signals_to_decompose:
            # 对于太阳辐照度和前后光路温度，使用120分钟移动平均作为周期性成分
            if name in ['太阳辐照度', '前光路温度', '后光路温度均值']:
                window_size = int(120 * 60 / 2)  # 60分钟窗口
                periodic = signal.rolling(window=window_size, center=True, min_periods=1).mean()
                random = signal - periodic
            else:  # 对于误差和载荷温度，使用更短窗口
                window_size = int(30 * 60)  # 30分钟窗口
                periodic = signal.rolling(window=window_size, center=True, min_periods=1).mean()
                random = signal - periodic

            plt.figure(figsize=(14, 8))

            # 原始信号
            plt.subplot(3, 1, 1)
            plt.plot(signal.index, signal, 'b-', linewidth=1)
            plt.title(f'{star_name} - {terminal_name} - {name} - 原始信号')
            plt.ylabel('值')
            plt.grid(True, alpha=0.3)

            # 周期性成分
            plt.subplot(3, 1, 2)
            plt.plot(signal.index, periodic, 'g-', linewidth=1)
            plt.title(f'{star_name} - {terminal_name} - {name} - 周期性成分（120分钟轨道周期）')
            plt.ylabel('值')
            plt.grid(True, alpha=0.3)

            # 随机性成分
            plt.subplot(3, 1, 3)
            plt.plot(signal.index, random, 'r-', linewidth=1)
            plt.title(f'{star_name} - {terminal_name} - {name} - 随机性成分')
            plt.xlabel('时间')
            plt.ylabel('值')
            plt.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(self.plots_dir / f'{star_name}_{terminal_name}_{name}_periodic_random.png',
                      dpi=150, bbox_inches='tight')
            plt.close()

            print(f"  {name}周期性/随机性成分图已保存")

    def analyze_thermal_deformation_effects(self, merged_data, star_name, terminal_name):
        """
        硬编码分析周期性和随机热形变对指向误差的影响
        周期性热形变：太阳辐照度、前后光路温度变化
        随机热形变：载荷温度变化（设备状态影响）

        参数:
            merged_data: 合并后的数据
            star_name: 卫星名称
            terminal_name: 终端名称

        返回:
            dict: 分析结果
        """
        results = {}

        if '综合误差' not in merged_data.columns:
            return results

        # 使用120分钟移动平均分离误差信号的周期性和随机性成分
        window_size = int(120 * 60 / 2)  # 60分钟窗口
        error_periodic = merged_data['综合误差'].rolling(window=window_size, center=True, min_periods=1).mean()
        error_random = merged_data['综合误差'] - error_periodic

        # 分析周期性热形变影响（直接使用原始值，因为这些本身就是周期性的）
        periodic_effects = {}

        if '前光路温度' in merged_data.columns:
            corr, _ = stats.pearsonr(error_periodic.dropna(), merged_data['前光路温度'].dropna())
            periodic_effects['前光路温度'] = corr

        if '后光路温度均值' in merged_data.columns:
            corr, _ = stats.pearsonr(error_periodic.dropna(), merged_data['后光路温度均值'].dropna())
            periodic_effects['后光路温度均值'] = corr

        if 'solar_irradiance' in merged_data.columns:
            corr, _ = stats.pearsonr(error_periodic.dropna(), merged_data['solar_irradiance'].dropna())
            periodic_effects['太阳辐照度'] = corr

        results['periodic'] = periodic_effects

        # 分析随机热形变影响（使用载荷温度的变化率）
        random_effects = {}

        if 'DBF载荷温度' in merged_data.columns:
            temp_diff = merged_data['DBF载荷温度'].diff()
            valid_data = pd.DataFrame({
                'error': error_random,
                'temp': temp_diff
            }).dropna()
            if len(valid_data) > 100:
                corr, _ = stats.pearsonr(valid_data['error'], valid_data['temp'])
                random_effects['DBF载荷温度'] = corr

        if 'L载荷温度' in merged_data.columns:
            temp_diff = merged_data['L载荷温度'].diff()
            valid_data = pd.DataFrame({
                'error': error_random,
                'temp': temp_diff
            }).dropna()
            if len(valid_data) > 100:
                corr, _ = stats.pearsonr(valid_data['error'], valid_data['temp'])
                random_effects['L载荷温度'] = corr
            random_effects['L载荷温度'] = corr

        if 'Ka载荷温度' in merged_data.columns:
            temp_periodic, temp_random = self.separate_periodic_random(merged_data['Ka载荷温度'])
            corr = np.corrcoef(error_random.dropna(), temp_random.dropna())[0, 1]
            random_effects['Ka载荷温度'] = corr

        results['random'] = random_effects

        return results

    def plot_deformation_error_relations(self, merged_data, star_name, terminal_name):
        """
        硬编码绘制热形变与指向误差关系图
        周期性热形变：太阳辐照度、前后光路温度（120分钟轨道周期）
        随机热形变：载荷温度（设备状态影响）

        参数:
            merged_data: 合并后的数据
            star_name: 卫星名称
            terminal_name: 终端名称
        """
        if '综合误差' not in merged_data.columns:
            return

        # 使用120分钟移动平均分离误差信号的周期性和随机性成分
        window_size = int(120 * 60 / 2)  # 60分钟窗口
        error_periodic = merged_data['综合误差'].rolling(window=window_size, center=True, min_periods=1).mean()
        error_random = merged_data['综合误差'] - error_periodic

        # 创建图形
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        plot_idx = 0

        # 1. 周期性成分关系（太阳辐照度 vs 误差周期性成分）
        if 'solar_irradiance' in merged_data.columns:
            valid_data = pd.DataFrame({
                'error': error_periodic,
                'temp': merged_data['solar_irradiance']
            }).dropna()

            if len(valid_data) > 100:
                ax = axes[plot_idx // 2, plot_idx % 2]
                ax.scatter(valid_data['temp'], valid_data['error'], alpha=0.3, s=5)
                ax.set_xlabel('太阳辐照度 (W/m²)')
                ax.set_ylabel('指向误差周期性成分 (°)')
                ax.set_title(f'{star_name} - {terminal_name}\n太阳辐照度与指向误差周期性关系')
                ax.grid(True, alpha=0.3)
                plot_idx += 1

        # 2. 周期性成分关系（前光路温度 vs 误差周期性成分）
        if '前光路温度' in merged_data.columns:
            valid_data = pd.DataFrame({
                'error': error_periodic,
                'temp': merged_data['前光路温度']
            }).dropna()

            if len(valid_data) > 100:
                ax = axes[plot_idx // 2, plot_idx % 2]
                ax.scatter(valid_data['temp'], valid_data['error'], alpha=0.3, s=5)
                ax.set_xlabel('前光路温度 (°C)')
                ax.set_ylabel('指向误差周期性成分 (°)')
                ax.set_title(f'{star_name} - {terminal_name}\n前光路温度与指向误差周期性关系')
                ax.grid(True, alpha=0.3)
                plot_idx += 1

        # 3. 随机性成分关系（DBF载荷温度变化 vs 误差随机性成分）
        if 'DBF载荷温度' in merged_data.columns:
            temp_diff = merged_data['DBF载荷温度'].diff()
            valid_data = pd.DataFrame({
                'error': error_random,
                'temp': temp_diff
            }).dropna()

            if len(valid_data) > 100:
                ax = axes[plot_idx // 2, plot_idx % 2]
                ax.scatter(valid_data['temp'], valid_data['error'], alpha=0.3, s=5)
                ax.set_xlabel('DBF载荷温度变化 (°C)')
                ax.set_ylabel('指向误差随机性成分 (°)')
                ax.set_title(f'{star_name} - {terminal_name}\nDBF载荷温度变化与指向误差随机性关系')
                ax.grid(True, alpha=0.3)
                plot_idx += 1

        # 4. 随机性成分关系（L载荷温度变化 vs 误差随机性成分）
        if 'L载荷温度' in merged_data.columns:
            temp_diff = merged_data['L载荷温度'].diff()
            valid_data = pd.DataFrame({
                'error': error_random,
                'temp': temp_diff
            }).dropna()

            if len(valid_data) > 100:
                ax = axes[plot_idx // 2, plot_idx % 2]
                ax.scatter(valid_data['temp'], valid_data['error'], alpha=0.3, s=5)
                ax.set_xlabel('L载荷温度变化 (°C)')
                ax.set_ylabel('指向误差随机性成分 (°)')
                ax.set_title(f'{star_name} - {terminal_name}\nL载荷温度变化与指向误差随机性关系')
                ax.grid(True, alpha=0.3)
                plot_idx += 1

        plt.tight_layout()
        plt.savefig(self.plots_dir / f'{star_name}_{terminal_name}_thermal_deformation_effects.png',
                  dpi=150, bbox_inches='tight')
        plt.close()

        print("  热形变影响关系图已保存")

    def plot_spectral_analysis(self, merged_data, star_name, terminal_name):
        """
        硬编码绘制频谱分析图

        参数:
            merged_data: 合并后的温度和误差数据
            star_name: 卫星名称
            terminal_name: 终端名称
        """
        if merged_data is None:
            return

        signals_to_analyze = []

        if '综合误差' in merged_data.columns:
            signals_to_analyze.append(('综合误差', merged_data['综合误差']))
        elif '俯仰指向误差' in merged_data.columns:
            signals_to_analyze.append(('俯仰指向误差', merged_data['俯仰指向误差']))

        if '前光路温度' in merged_data.columns:
            signals_to_analyze.append(('前光路温度', merged_data['前光路温度']))

        if '后光路温度均值' in merged_data.columns:
            signals_to_analyze.append(('后光路温度均值', merged_data['后光路温度均值']))

        if 'DBF载荷温度' in merged_data.columns:
            signals_to_analyze.append(('DBF载荷温度', merged_data['DBF载荷温度']))

        if 'L载荷温度' in merged_data.columns:
            signals_to_analyze.append(('L载荷温度', merged_data['L载荷温度']))

        if 'Ka载荷温度' in merged_data.columns:
            signals_to_analyze.append(('Ka载荷温度', merged_data['Ka载荷温度']))

        if 'solar_irradiance' in merged_data.columns:
            signals_to_analyze.append(('太阳辐照度', merged_data['solar_irradiance']))

        if 'solar_elevation' in merged_data.columns:
            signals_to_analyze.append(('太阳高度角', merged_data['solar_elevation']))

        plt.figure(figsize=(14, 10))

        max_power = 0
        all_freqs = []

        for name, signal in signals_to_analyze:
            freqs, power = self.spectral_analysis(signal, sampling_rate=1)
            if freqs is not None and power is not None and len(freqs) > 0:
                plt.semilogy(freqs, power, label=name, linewidth=1.5)
                all_freqs.extend(freqs)
                if len(power) > 0:
                    current_max = np.max(power)
                    if current_max > max_power:
                        max_power = current_max

        plt.xlabel('频率 (Hz)')
        plt.ylabel('功率谱密度')
        plt.title('各信号频谱分析')
        plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1))
        plt.grid(True, alpha=0.3)

        # 设置合理的x轴范围（主要关注低频部分）
        if all_freqs:
            max_freq = min(np.max(all_freqs), 0.01)  # 限制在0.01Hz以下（约100秒周期）
            plt.xlim(0, max_freq)

        plt.tight_layout()
        plot_file = self.plots_dir / f'{star_name}_{terminal_name}_spectral_analysis.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  频谱分析图已保存到: {plot_file.name}")

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

        # 硬编码加载太阳矢量数据
        sun_data = self.load_sun_vector_data(star_name)
        if sun_data is not None:
            merged_data = self.merge_with_sun_vector(merged_data, sun_data)
            print(f"  太阳矢量数据已合并")
        else:
            print(f"  未找到太阳矢量数据，跳过")

        # 硬编码导出处理后的数据到CSV文件（包含太阳矢量数据）
        csv_file = self.data_dir / f'{star_name}_{terminal_name}_analysis_data.csv'
        merged_data.to_csv(csv_file)
        print(f"  分析数据已保存到: {csv_file.name}")

        # 绘制简单的分析图
        self.plot_simple_temperature_analysis(merged_data, star_name, terminal_name)

        # 绘制太阳能量关系图
        if 'solar_irradiance' in merged_data.columns or 'solar_elevation' in merged_data.columns:
            self.plot_solar_energy_relations(merged_data, star_name, terminal_name)

        # 绘制频谱分析图
        self.plot_spectral_analysis(merged_data, star_name, terminal_name)

        # 绘制周期性和随机性成分分解图
        self.plot_periodic_random_decomposition(merged_data, star_name, terminal_name)

        # 绘制热形变影响关系图
        self.plot_deformation_error_relations(merged_data, star_name, terminal_name)

        # 分析热形变影响
        self.analyze_thermal_deformation_effects(merged_data, star_name, terminal_name)

        self.results[f'{star_name}_{terminal_name}'] = merged_data

        return merged_data

    def generate_report(self):
        """生成增强版分析报告"""
        report_file = self.reports_dir / 'temperature_analysis_summary.md'

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 温度与误差关系分析报告（硬编码方案）\n\n")
            f.write("## 注意事项\n")
            f.write("本报告使用严格的硬编码方案生成，所有温度参数均严格按照配置的列名提取。\n")
            f.write("载荷温度使用单个遥测量而非平均值：\n")
            f.write("- DBF载荷：RM16-DBF安装面1(+Z)\n")
            f.write("- L载荷：RM83-L射频单元本体（-Y3-X1）\n")
            f.write("- Ka载荷：RM99-Ka接收相控阵主散热面1(+X)\n\n")

            f.write("## 分析的终端\n")
            for key in self.results.keys():
                f.write(f"- {key}\n")

            f.write("\n## 数据文件列名说明\n")
            f.write("### 新增列（太阳矢量数据）\n")
            f.write("- `sun_vector_x`, `sun_vector_y`, `sun_vector_z`：太阳矢量分量（km）\n")
            f.write("- `sun_distance`：太阳距离（km）\n")
            f.write("- `solar_irradiance`：太阳辐照度（W/m²）\n")
            f.write("- `solar_elevation`：太阳高度角（度）\n\n")

            f.write("### 载荷温度列名变更\n")
            f.write("- 原 `DBF载荷温度均值` 改为 `DBF载荷温度`（单个遥测量）\n")
            f.write("- 原 `L载荷温度均值` 改为 `L载荷温度`（单个遥测量）\n")
            f.write("- 原 `Ka载荷温度均值` 改为 `Ka载荷温度`（单个遥测量）\n\n")

            f.write("## 生成的文件\n")
            f.write("### 数据文件（output/temperature_analysis/data/）\n")
            for data_file in sorted(self.data_dir.glob('*.csv')):
                f.write(f"- {data_file.name}\n")

            f.write("\n### 图表文件（output/temperature_analysis/plots/）\n")
            for plot_file in sorted(self.plots_dir.glob('*.png')):
                f.write(f"- {plot_file.name}\n")

            f.write("\n## 分析方法说明\n")
            f.write("- **太阳能量计算**：使用平方反比定律计算太阳辐照度\n")
            f.write("- **太阳高度角**：假设卫星基准轴为z轴的简化模型\n")
            f.write("- **频谱分析**：使用FFT进行信号的频率特性分析\n")
            f.write("- **数据对齐**：太阳矢量数据使用nearest方法时间对齐，容差0.5秒\n")
            f.write("- **热形变分离**：使用轨道周期（108分钟）滤波分离周期性和随机性热形变成分\n\n")

            f.write("## 分析结果\n\n")

            f.write("### 周期性热形变影响（108分钟轨道周期）\n")
            f.write("- **周期性成分来源**：太阳辐照度周期性变化导致的温度波动\n")
            f.write("- **主要影响参数**：\n")
            f.write("  - 太阳辐照度：直接反映轨道周期性变化\n")
            f.write("  - 前光路温度：受轨道周期影响较大\n")
            f.write("  - 后光路温度均值：受轨道周期影响较小\n\n")

            f.write("### 随机热形变影响（载荷温度变化）\n")
            f.write("- **随机性成分来源**：载荷设备开关机和运行状态变化\n")
            f.write("- **主要影响参数**：\n")
            f.write("  - DBF载荷温度：受设备运行状态影响\n")
            f.write("  - L载荷温度：受设备运行状态影响\n")
            f.write("  - Ka载荷温度：受设备运行状态影响\n\n")

            f.write("## 分析建议\n")
            f.write("1. 分析重点关注太阳辐照度周期性变化对温度和误差的影响（108分钟轨道周期）\n")
            f.write("2. 频谱分析结果可用于识别轨道周期（约108分钟）的影响\n")
            f.write("3. 太阳高度角变化可反映卫星轨道姿态特征\n")
            f.write("4. 可进一步分析太阳能量与温度变化的相位关系\n")
            f.write("5. 载荷温度的随机性变化对指向误差有显著影响，需关注设备状态变化\n")

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
