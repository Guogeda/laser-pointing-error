#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
卫星链路拓扑配置
"""

# 卫星实际在轨的链路拓扑
LINK_TOPOLOGY = [
    ('A2701', 'A2803'),
    ('A3401', 'A3503'),
    ('A3601', 'A2703'),
    ('A2804', 'A2902'),
    ('A2904', 'A3004'),
    ('A3002', 'A3102'),
    ('A3104', 'A3204'),
    ('A3304', 'A3402'),
    ('A3504', 'A3602'),
    ('A3302', 'A3201'),
    ('A2702', 'A0703'),
    ('A2802', 'A0803'),
    ('A3502', 'A1503'),
    ('A5802', 'A5704'),
    ('A5902', 'A5804'),
    ('A6002', 'A5904'),
    ('A6102', 'A6004'),
    ('A5803', 'A2801'),
    ('A5903', 'A2901'),
    ('A6003', 'A3001'),
    ('A6103', 'A3101'),
    ('A5703', 'A2704'),
]

# 简化分析：重点分析的链路
FOCUSED_LINKS = [
    ('A32', 'A31'),  # 32-31 链路
    ('A31', 'A61'),  # 31-61 链路
]

# 卫星对的名称映射（用于数据处理）
STAR_PAIR_MAP = {
    'A32-A31': ('32star', '31star'),
    'A31-A61': ('31star', '61star'),
}

def get_star_pair(link_name):
    """获取链路对应的卫星数据文件夹名"""
    return STAR_PAIR_MAP.get(link_name)

def is_focused_link(star1, star2):
    """判断是否是重点分析的链路"""
    return (star1, star2) in FOCUSED_LINKS or (star2, star1) in FOCUSED_LINKS