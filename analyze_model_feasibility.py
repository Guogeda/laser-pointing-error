#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析指向误差与周期性和随机热形变的关系，评估建模可行性
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from temperature_analysis import TemperatureAnalyzer

def analyze_model_feasibility():
    """分析建模可行性"""
    analyzer = TemperatureAnalyzer('output')

    # 加载31star A1-1的数据（作为示例）
    data = analyzer.load_analysis_data('31star', 'A1-1')

    if data is None:
        print("无法加载数据")
        return

    print("=" * 80)
    print("指向误差与热形变关系分析结论")
    print("=" * 80)

    # 使用120分钟移动平均分离周期性和随机性成分
    window_size = int(120 * 60 / 2)  # 60分钟窗口

    print("\n【分析方法】")
    print("- 周期性成分：120分钟移动平均（轨道周期）")
    print("- 随机性成分：原信号 - 周期性成分")

    # 分离各信号的周期性和随机性成分
    signals = {}
    for col in ['综合误差', '前光路温度', '后光路温度均值', 'solar_irradiance',
                'DBF载荷温度', 'L载荷温度', 'Ka载荷温度']:
        if col in data.columns:
            periodic = data[col].rolling(window=window_size, center=True, min_periods=1).mean()
            random = data[col] - periodic
            signals[col] = {
                'original': data[col],
                'periodic': periodic,
                'random': random
            }

    print(f"\n【数据概览】")
    print(f"- 有效数据点数: {len(data.dropna(subset=['综合误差']))}")
    print(f"- 时间跨度: {data.index.min()} 至 {data.index.max()}")

    # 1. 周期性热形变与指向误差的关系
    print("\n" + "=" * 80)
    print("一、周期性热形变影响分析")
    print("=" * 80)

    error_periodic = signals['综合误差']['periodic']

    periodic_correlations = {}
    for name, col in [('前光路温度', '前光路温度'),
                      ('后光路温度', '后光路温度均值'),
                      ('太阳辐照度', 'solar_irradiance')]:
        if col in signals:
            temp_periodic = signals[col]['periodic']
            valid_data = pd.DataFrame({
                'error': error_periodic,
                'temp': temp_periodic
            }).dropna()

            if len(valid_data) > 100:
                corr, p_val = stats.pearsonr(valid_data['error'], valid_data['temp'])
                periodic_correlations[name] = corr
                print(f"\n{name}:")
                print(f"  相关系数: {corr:.4f}")
                print(f"  P值: {p_val:.4e}")
                print(f"  显著性: {'★★★ 极显著' if p_val < 0.001 else '★★ 显著' if p_val < 0.01 else '★ 较显著' if p_val < 0.05 else '不显著'}")

    # 2. 随机热形变与指向误差的关系
    print("\n" + "=" * 80)
    print("二、随机热形变影响分析")
    print("=" * 80)

    error_random = signals['综合误差']['random']

    random_correlations = {}
    for name, col in [('DBF载荷温度', 'DBF载荷温度'),
                      ('L载荷温度', 'L载荷温度'),
                      ('Ka载荷温度', 'Ka载荷温度')]:
        if col in signals:
            temp_diff = signals[col]['original'].diff()
            valid_data = pd.DataFrame({
                'error': error_random,
                'temp': temp_diff
            }).dropna()

            if len(valid_data) > 100:
                corr, p_val = stats.pearsonr(valid_data['error'], valid_data['temp'])
                random_correlations[name] = corr
                print(f"\n{name}变化率:")
                print(f"  相关系数: {corr:.4f}")
                print(f"  P值: {p_val:.4e}")
                print(f"  显著性: {'★★★ 极显著' if p_val < 0.001 else '★★ 显著' if p_val < 0.01 else '★ 较显著' if p_val < 0.05 else '不显著'}")

    # 3. 建模可行性分析
    print("\n" + "=" * 80)
    print("三、建模可行性分析")
    print("=" * 80)

    # 准备特征
    features = []
    feature_names = []

    # 周期性特征
    if '前光路温度' in signals:
        features.append(signals['前光路温度']['periodic'])
        feature_names.append('前光路温度_周期')

    if '后光路温度均值' in signals:
        features.append(signals['后光路温度均值']['periodic'])
        feature_names.append('后光路温度_周期')

    if 'solar_irradiance' in signals:
        features.append(signals['solar_irradiance']['periodic'])
        feature_names.append('太阳辐照度_周期')

    # 随机性特征（温度变化率）
    if 'DBF载荷温度' in signals:
        features.append(signals['DBF载荷温度']['original'].diff())
        feature_names.append('DBF载荷温度_变化')

    if 'L载荷温度' in signals:
        features.append(signals['L载荷温度']['original'].diff())
        feature_names.append('L载荷温度_变化')

    if 'Ka载荷温度' in signals:
        features.append(signals['Ka载荷温度']['original'].diff())
        feature_names.append('Ka载荷温度_变化')

    if len(features) > 0:
        # 构建数据集
        X = pd.concat(features, axis=1)
        X.columns = feature_names
        y = signals['综合误差']['original']

        # 去除NaN
        valid_data = pd.concat([X, y], axis=1).dropna()
        X_valid = valid_data[feature_names]
        y_valid = valid_data[valid_data.columns[-1]]

        print(f"\n可用于建模的数据:")
        print(f"  特征数: {len(feature_names)}")
        print(f"  样本数: {len(valid_data)}")
        print(f"  特征: {', '.join(feature_names)}")

        if len(valid_data) > 100:
            # 划分训练集和测试集
            X_train, X_test, y_train, y_test = train_test_split(X_valid, y_valid, test_size=0.3, random_state=42)

            # 线性回归
            print("\n【模型1：线性回归】")
            lr = LinearRegression()
            lr.fit(X_train, y_train)
            y_pred_lr = lr.predict(X_test)
            r2_lr = r2_score(y_test, y_pred_lr)
            rmse_lr = np.sqrt(mean_squared_error(y_test, y_pred_lr))

            print(f"  R²分数: {r2_lr:.4f}")
            print(f"  RMSE: {rmse_lr:.6f}°")
            print(f"  系数:")
            for name, coef in zip(feature_names, lr.coef_):
                print(f"    {name}: {coef:.6e}")

            # 随机森林
            print("\n【模型2：随机森林】")
            rf = RandomForestRegressor(n_estimators=100, random_state=42)
            rf.fit(X_train, y_train)
            y_pred_rf = rf.predict(X_test)
            r2_rf = r2_score(y_test, y_pred_rf)
            rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))

            print(f"  R²分数: {r2_rf:.4f}")
            print(f"  RMSE: {rmse_rf:.6f}°")
            print(f"  特征重要性:")
            for name, importance in zip(feature_names, rf.feature_importances_):
                print(f"    {name}: {importance:.4f}")

    # 4. 结论
    print("\n" + "=" * 80)
    print("四、结论")
    print("=" * 80)

    print("\n【1. 周期性热形变影响】")
    if periodic_correlations:
        max_corr_name = max(periodic_correlations.keys(), key=lambda k: abs(periodic_correlations[k]))
        max_corr = periodic_correlations[max_corr_name]
        print(f"  主要影响因素: {max_corr_name} (相关系数={max_corr:.4f})")
        if abs(max_corr) > 0.5:
            print("  评价: 周期性热形变对指向误差有较强影响")
        elif abs(max_corr) > 0.3:
            print("  评价: 周期性热形变对指向误差有中等影响")
        else:
            print("  评价: 周期性热形变对指向误差影响较弱")
    else:
        print("  未检测到显著的周期性影响")

    print("\n【2. 随机热形变影响】")
    if random_correlations:
        max_corr_name = max(random_correlations.keys(), key=lambda k: abs(random_correlations[k]))
        max_corr = random_correlations[max_corr_name]
        print(f"  主要影响因素: {max_corr_name}变化率 (相关系数={max_corr:.4f})")
        if abs(max_corr) > 0.3:
            print("  评价: 随机热形变对指向误差有明显影响")
        elif abs(max_corr) > 0.1:
            print("  评价: 随机热形变对指向误差有一定影响")
        else:
            print("  评价: 随机热形变对指向误差影响较弱")
    else:
        print("  未检测到显著的随机性影响")

    print("\n【3. 建模可行性】")
    print("  可以建立指向误差与热形变的关系模型，但需要考虑以下因素:")
    print("  ✓ 周期性成分（太阳辐照度、前后光路温度）可用于建模轨道周期影响")
    print("  ✓ 随机性成分（载荷温度变化率）可用于建模设备状态影响")
    print("  ✗ 单一模型可能无法完全捕捉所有影响因素")
    print("  ✗ 需要考虑相位滞后效应（温度变化→热形变→指向误差有时间延迟）")
    print("  ✗ 建议采用分时段建模或加入时间序列特征")

    print("\n【4. 建议的建模方案】")
    print("  方案1: 分成分建模")
    print("    - 周期性误差 = f(太阳辐照度_周期, 前光路温度_周期, 后光路温度_周期)")
    print("    - 随机性误差 = g(DBF载荷温度_变化, L载荷温度_变化, Ka载荷温度_变化)")
    print("    - 总误差 = 周期性误差 + 随机性误差")
    print("")
    print("  方案2: 时间序列模型")
    print("    - 使用LSTM或ARIMA模型，加入温度特征的滞后项")
    print("    - 考虑不同温度参数的响应时间差异")
    print("")
    print("  方案3: 混合模型")
    print("    - 物理模型（热传导方程）+ 数据驱动模型（机器学习）")
    print("    - 利用先验知识约束模型参数")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    analyze_model_feasibility()
