#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
卫星分组配置
"""

STAR_GROUP = {
    'jg01': ['A27', 'A28', 'A29', 'A30', 'A31', 'A32', 'A33', 'A34', 'A35', 'A36'],
    'jg02': ['A57', 'A58', 'A59', 'A60', 'A61', 'A62', 'A63', 'A64', 'A65', 'A66'],
}

PARAM_MAPPING_FILE = {
    'jg01': 'param_mapping_jg01.py',
    'jg02': 'param_mapping_jg02.py',
}

# 终端编号规则
TERMINAL_MAP = {
    'jg01': {'01': 'B1', '02': 'A1-2', '03': 'B2', '04': 'A1-1'},
    'jg02': {'01': 'A1-1', '02': 'A2-1', '03': 'A2-2', '04': 'A1-2'},
}

# 终端配置
# 终端配置 - 支持按星号动态调整包代码
TERMINALS = {
    'jg01': {
        # 通用终端配置（适用于大多数jg01组卫星）
        'common': {
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
        },
        # 星号特定配置（覆盖通用配置）
        '32star': {
            'A1-1': {
                'package': '13B',  # 32star激光A使用13B包
                'state_param': 'TMJA3115',
                'state_name': 'A3慢-1-激光终端状态',
                'error_params': {
                    'A_t': 'TMJA3148', 'A_r': 'TMJA3147',
                    'E_t': 'TMJA3150', 'E_r': 'TMJA3149',
                }
            },
            'A1-2': {
                'package': '13B',  # 32star激光A使用13B包
                'state_param': 'TMJA3239',
                'state_name': 'A3慢-2-激光终端状态',
                'error_params': {
                    'A_t': 'TMJA3272', 'A_r': 'TMJA3271',
                    'E_t': 'TMJA3274', 'E_r': 'TMJA3273',
                }
            },
        },
    },
    'jg02': {
        'A1-1': {
            'package': '13B',
            'state_param': 'TMJA3115',
            'state_name': 'A1慢3-1-激光终端状态',
            'error_params': {
                'A_t': 'TMJA3148', 'A_r': 'TMJA3147',
                'E_t': 'TMJA3150', 'E_r': 'TMJA3149',
            }
        },
        'A2-1': {
            'package': '13F',
            'state_param': 'TMJA8115',
            'state_name': 'A2慢3-1-激光终端状态',
            'error_params': {
                'A_t': 'TMJA8148', 'A_r': 'TMJA8147',
                'E_t': 'TMJA8150', 'E_r': 'TMJA8149',
            }
        },
        'A2-2': {
            'package': '13F',
            'state_param': 'TMJA8239',
            'state_name': 'A2慢3-2-激光终端状态',
            'error_params': {
                'A_t': 'TMJA8272', 'A_r': 'TMJA8271',
                'E_t': 'TMJA8274', 'E_r': 'TMJA8273',
            }
        },
        'A1-2': {
            'package': '13B',
            'state_param': 'TMJA3239',
            'state_name': 'A1慢3-2-激光终端状态',
            'error_params': {
                'A_t': 'TMJA3272', 'A_r': 'TMJA3271',
                'E_t': 'TMJA3274', 'E_r': 'TMJA3273',
            }
        },
    },
}

def get_group_by_star(star_name):
    """根据卫星编号获取分组"""
    # 处理 '61star' 这样的格式
    if star_name.endswith('star'):
        try:
            star_num = int(star_name[:2])
            if 27 <= star_num <= 36:
                return 'jg01'
            elif 57 <= star_num <= 66:
                return 'jg02'
        except ValueError:
            pass

    # 处理 'A61' 这样的格式
    if star_name.startswith('A') and len(star_name) >= 3:
        try:
            star_num = int(star_name[1:3])
            if 27 <= star_num <= 36:
                return 'jg01'
            elif 57 <= star_num <= 66:
                return 'jg02'
        except ValueError:
            pass
    return 'jg01'  # 默认返回 jg01