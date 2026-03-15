#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
温度参数硬编码配置
注意：本项目必须使用硬编码方案，禁止使用智能方法！
所有温度参数必须严格对应实际列名，不允许自动识别或模糊匹配

温度来源分为两部分：
1. 与轨道周期有关：来源于太阳的热量，影响激光终端前后光路的温度
2. 与载荷温度有关：取 DBF、L、ka载荷温度遥测的平均值
"""

# 温度参数配置
TEMPERATURE_PARAMS = {
    'jg01': {
        'B1': {
            'front_path': 'B1慢-热控通道02反馈温度值_望远镜筒',  # 前光路温度（望远镜筒温度）
            'rear_path': ['B1慢-热控通道10反馈温度值_后光路1A', 'B1慢-热控通道11反馈温度值_后光路1B',
                         'B1慢-热控通道12反馈温度值_后光路2A', 'B1慢-热控通道13反馈温度值_后光路2B'],  # 后光路温度（多个参数取平均）
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']  # 载荷温度（多个参数取平均）
        },
        'B2': {
            'front_path': 'B2慢-热控通道02反馈温度值_望远镜筒',
            'rear_path': ['B2慢-热控通道10反馈温度值_后光路1A', 'B2慢-热控通道11反馈温度值_后光路1B',
                         'B2慢-热控通道12反馈温度值_后光路2A', 'B2慢-热控通道13反馈温度值_后光路2B'],
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']
        },
        'A1-1': {
            'front_path': 'A3慢-1-主镜筒温度(主)',  # 激光A前光路温度：主镜筒温度(主)
            'rear_path': ['A3慢-1-后光学基板温度(主)'],  # 激光A后光路温度：后光学基板温度(主)，只有1个
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']
        },
        'A1-2': {
            'front_path': 'A3慢-2-主镜筒温度(主)',  # 激光A前光路温度：主镜筒温度(主)
            'rear_path': ['A3慢-2-后光学基板温度(主)'],  # 激光A后光路温度：后光学基板温度(主)，只有1个
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']
        }
    },
    'jg02': {
        'A1-1': {
            'front_path': 'A1慢3-1-主镜筒温度(主)',  # 激光A前光路温度：主镜筒温度(主)
            'rear_path': ['A1慢3-1-后光学基板温度(主)'],  # 激光A后光路温度：后光学基板温度(主)，只有1个
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']
        },
        'A2-1': {
            'front_path': 'A2慢3-1-主镜筒温度(主)',  # 激光A前光路温度：主镜筒温度(主)
            'rear_path': ['A2慢3-1-后光学基板温度(主)'],  # 激光A后光路温度：后光学基板温度(主)，只有1个
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']
        },
        'A2-2': {
            'front_path': 'A2慢3-2-主镜筒温度(主)',  # 激光A前光路温度：主镜筒温度(主)
            'rear_path': ['A2慢3-2-后光学基板温度(主)'],  # 激光A后光路温度：后光学基板温度(主)，只有1个
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']
        },
        'A1-2': {
            'front_path': 'A1慢3-2-主镜筒温度(主)',  # 激光A前光路温度：主镜筒温度(主)
            'rear_path': ['A1慢3-2-后光学基板温度(主)'],  # 激光A后光路温度：后光学基板温度(主)，只有1个
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']
        },
        'B1': {
            'front_path': 'B1慢-热控通道02反馈温度值_望远镜筒',  # 前光路温度（望远镜筒）
            'rear_path': ['B1慢-热控通道10反馈温度值_后光路1A', 'B1慢-热控通道11反馈温度值_后光路1B',
                         'B1慢-热控通道12反馈温度值_后光路2A', 'B1慢-热控通道13反馈温度值_后光路2B'],  # 后光路温度（4个）
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']  # 载荷温度（9个）
        },
        'B2': {
            'front_path': 'B2慢-热控通道02反馈温度值_望远镜筒',
            'rear_path': ['B2慢-热控通道10反馈温度值_后光路1A', 'B2慢-热控通道11反馈温度值_后光路1B',
                         'B2慢-热控通道12反馈温度值_后光路2A', 'B2慢-热控通道13反馈温度值_后光路2B'],
            'payload': ['RM15-DBF本体', 'RM16-DBF安装面1(+Z)', 'RM17-DBF安装面2(-Z)',
                       'RM83-L射频单元本体（-Y3-X1）', 'RM89-L射频单元本体（-Y1+X3）',
                       'RM90-L射频单元本体（-Y3+X4）', 'RM91-L射频单元（-Y1）',
                       'RM99-Ka接收相控阵主散热面1(+X)', 'RM100-Ka接收相控阵主散热面2(-X)']
        }
    }
}

def get_temperature_params(group_name, terminal_name):
    """
    获取指定卫星组和终端的温度参数配置

    参数:
        group_name: 卫星组名称，如 'jg01' 或 'jg02'
        terminal_name: 终端名称，如 'A1-1'

    返回:
        dict: 温度参数配置，包含前光路、后光路和载荷温度参数
    """
    if group_name not in TEMPERATURE_PARAMS:
        print(f"警告: 未找到卫星组 {group_name} 的温度参数配置，使用默认配置")
        group_name = 'jg01'  # 默认使用jg01组配置

    if terminal_name not in TEMPERATURE_PARAMS[group_name]:
        print(f"警告: 未找到终端 {terminal_name} 的温度参数配置，返回None")
        return None

    return TEMPERATURE_PARAMS[group_name][terminal_name]

def calculate_payload_temperature(df, payload_params):
    """
    计算载荷温度平均值

    参数:
        df: DataFrame，包含所有参数数据
        payload_params: 载荷温度参数列表

    返回:
        Series: 载荷温度平均值
    """
    valid_params = []
    for param in payload_params:
        if param in df.columns:
            valid_params.append(param)

    if not valid_params:
        return None

    # 计算有效参数的平均值（忽略NaN值）
    payload_temp = df[valid_params].mean(axis=1)
    return payload_temp

def calculate_rear_path_temperature(df, rear_params):
    """
    计算后光路温度平均值

    参数:
        df: DataFrame，包含所有参数数据
        rear_params: 后光路温度参数列表

    返回:
        Series: 后光路温度平均值
    """
    valid_params = []
    for param in rear_params:
        if param in df.columns:
            valid_params.append(param)

    if not valid_params:
        return None

    # 计算有效参数的平均值（忽略NaN值）
    rear_temp = df[valid_params].mean(axis=1)
    return rear_temp

def extract_temperature_data(df, temperature_config):
    """
    从DataFrame中提取温度数据

    参数:
        df: DataFrame，包含所有参数数据
        temperature_config: 温度参数配置

    返回:
        dict: 包含前光路温度、后光路温度和载荷温度的字典
    """
    temp_data = {}

    # 提取前光路温度
    if 'front_path' in temperature_config and temperature_config['front_path'] in df.columns:
        temp_data['front_path'] = df[temperature_config['front_path']]

    # 计算后光路温度平均值
    if 'rear_path' in temperature_config:
        rear_temp = calculate_rear_path_temperature(df, temperature_config['rear_path'])
        if rear_temp is not None:
            temp_data['rear_path'] = rear_temp

    # 计算载荷温度平均值
    if 'payload' in temperature_config:
        payload_temp = calculate_payload_temperature(df, temperature_config['payload'])
        if payload_temp is not None:
            temp_data['payload'] = payload_temp

    return temp_data
