#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单分析指向误差与热形变关系
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from temperature_analysis import TemperatureAnalyzer

def simple_analysis():
    """简单分析"""
    analyzer = TemperatureAnalyzer('output')
    data = analyzer.load_analysis_data('31star', 'A1-1')

    if data is None:
        print("Cannot load data")
        return

    window_size = int(120 * 60 / 2)

    print("="*60)
    print("CONCLUSIONS: Pointing Error vs Thermal Deformation")
    print("="*60)

    error_periodic = data['综合误差'].rolling(window=window_size, center=True, min_periods=1).mean()
    error_random = data['综合误差'] - error_periodic

    results = {
        'periodic': {},
        'random': {}
    }

    print("\n[1] PERIODIC THERMAL DEFORMATION (120-min orbit cycle):")
    for name, col in [('Front Optics Temp', '前光路温度'),
                      ('Rear Optics Temp', '后光路温度均值'),
                      ('Solar Irradiance', 'solar_irradiance')]:
        if col in data.columns:
            temp_periodic = data[col].rolling(window=window_size, center=True, min_periods=1).mean()
            valid = pd.DataFrame({'e': error_periodic, 't': temp_periodic}).dropna()
            if len(valid) > 100:
                corr, pval = stats.pearsonr(valid['e'], valid['t'])
                results['periodic'][name] = corr
                print(f"  {name}: correlation = {corr:.4f}, p-value={pval:.1e}")

    print("\n[2] RANDOM THERMAL DEFORMATION (payload temp change):")
    for name, col in [('DBF Payload', 'DBF载荷温度'),
                      ('L Payload', 'L载荷温度'),
                      ('Ka Payload', 'Ka载荷温度')]:
        if col in data.columns:
            temp_diff = data[col].diff()
            valid = pd.DataFrame({'e': error_random, 't': temp_diff}).dropna()
            if len(valid) > 100:
                corr, pval = stats.pearsonr(valid['e'], valid['t'])
                results['random'][name] = corr
                print(f"  {name} change: correlation = {corr:.4f}, p-value={pval:.1e}")

    print("\n" + "="*60)
    print("[3] CAN WE MODEL THIS?")
    print("="*60)
    print("\nKey Findings:")

    max_periodic = max(results['periodic'].values(), key=abs) if results['periodic'] else 0
    max_random = max(results['random'].values(), key=abs) if results['random'] else 0

    print(f"  - Strongest periodic correlation: {max_periodic:.4f}")
    print(f"  - Strongest random correlation: {max_random:.4f}")

    print("\nModeling Feasibility: YES, but with caveats:")
    print("  1. Periodic component (orbit cycle) can be modeled using:")
    print("     - Solar irradiance (120-min cycle)")
    print("     - Front/rear optics temperature")
    print("  2. Random component can be modeled using:")
    print("     - Payload temperature change rates")
    print("  3. Recommended approach:")
    print("     - Separate modeling for periodic and random components")
    print("     - Consider time delay effects (temperature -> deformation -> error)")
    print("     - Hybrid model: physics-based + data-driven")

    print("\n" + "="*60)

if __name__ == '__main__':
    simple_analysis()
